from .api_key import key

# base_uri = "https://www.googleapis/com/v3/"

# 3_months_hot = "https://trends.google.com/trends/explore?date=today%203-m&gprop=youtube"
# 3_months_hot_english = "https://trends.google.com/trends/explore?date=today%203-m&geo=US&gprop=youtube"

from googleapiclient.discovery import build
from googleapiclient import errors

#import sqlite3

import json
import sqlite3
import os
import re
import youtube_dl
import zlib

os.chdir(r'S:\out of context\source')


def connect_to_db():
    conn = sqlite3.connect('ooc.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS quota (count INTEGER)")

    return (conn, c)


def end_db(conn):
    conn.commit()
    conn.close()


query = "epic gamers"

youtube = build('youtube', 'v3', developerKey=key)

comment_storage = []


def get_comments(vID, c=None, pt=None):

    request = youtube.commentThreads().list(
        part='snippet,replies',
        maxResults=100,
        order='relevance',
        videoId=vID,
        pageToken=pt
    )
    response = request.execute()  # quota - 1 unit
    c.execute("INSERT INTO quota VALUES (1)")

    for i in response['items']:
        comment_storage.append(i)

    if 'nextPageToken' in response:
        get_comments(vID, c, pt=response['nextPageToken'])
    return comment_storage


def get_search(toSearch=query, c=None):
    request = youtube.search().list(
        part='snippet',
        maxResults=50,
        order='viewCount',
        q=toSearch,
        type='video',
    )

    response = request.execute()  # quota - 100 unit
    c.execute("INSERT INTO quota VALUES (100)")
    return response


def main():
    conn, c = connect_to_db()

# ----------------------------------------------------------
    search_results = get_search("anime funny", c)

    with open('store.json', 'r') as rf:
        pdata = json.load(rf)

    pdata['data'].append(search_results)

    with open('store.json', 'w') as rf:
        json.dump(pdata, rf)

    vID_list = []

    for i in search_results['items']:
        vID_list.append(i['id']['videoId'])
        print(i['id']['videoId'])
# ----------------------------------------------------------

# ----------------------------------------------------------
    # with open('store.json', 'r') as rf:
    #     data = json.load(rf)

    # vID_list = []

    # for i in data['data'][0]['items']:
    #     vID_list.append(i['id']['videoId'])
# ----------------------------------------------------------

    regex = r'^<a href=\"(.+)\">(\d{1,2}:\d{2})</a>'

    for i in vID_list:
        ibyte = i.encode('utf-8')
        ihash = zlib.adler32(ibyte)
        c.execute(
            "SELECT count(name) FROM sqlite_master WHERE type='table' AND name=?", (ihash, ))
        if c.fetchone()[0] == 1:
            print("Table exists")
            continue
        createnewtable = f'CREATE TABLE IF NOT EXISTS "{ihash}" (cid BLOB PRIMARY KEY, vid BLOB, mlink BLOB, ts BLOB, txt BLOB, lcount INTEGER)'
        c.execute(createnewtable)
        comment_storage.clear()
        try:
            comments = get_comments(i, c)
        except errors.HttpError as e:
            print(f'ERROR\t{e}')
            continue
        for j in comments:
            txt = j['snippet']['topLevelComment']['snippet']['textDisplay']
            cid = j['snippet']['topLevelComment']['id']
            lcount = j['snippet']['topLevelComment']['snippet']['likeCount']
            print(lcount)
            research = re.search(regex, txt)
            if research:
                sql = f"INSERT INTO \"{ihash}\" (cid, vid, mlink, ts, txt, lcount) VALUES (?, ?, ?, ?, ?, ?)"
                c.execute(
                    sql, (cid, i, research.group(1), research.group(2), txt, lcount, ))
                print('\tHIT', '\t', research.group(
                    1), '\t', research.group(2))
                print('\t---EOC---')
        conn.commit()

    end_db(conn)


if __name__ == '__main__':
    main()
