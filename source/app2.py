from itertools import count
import json
from api_key import key
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import re
import youtube_dl
import subprocess
import string

os.chdir(r'S:\out of context\source')
DB = 'store2.json'

youtube = build('youtube', 'v3', developerKey=key)


def put_search_in_db(response, db):
    with open(db, 'r') as db_read:
        data = json.load(db_read)

    alreadyExists = 0

    for item in response["items"]:
        vId = item["id"]["videoId"]
        vTitle = item["snippet"]["title"]

        if vId in data:
            alreadyExists += 1
        else:
            data[vId] = {
                "vTitle": vTitle,
                "cScanned": False,
                "cMatched": {

                }
            }

    with open(db, 'w') as db_write:
        json.dump(data, db_write)

    print(
        f"{alreadyExists} / {len(response['items'])} already exists. Added {len(response['items']) - alreadyExists} new data.")


def get_search(toSearch, db, howMany=50):
    request = youtube.search().list(
        part='snippet',
        maxResults=howMany,
        order='viewCount',
        q=toSearch,
        type='video',
    )

    response = request.execute()
    put_search_in_db(response, db)


def get_comments(vId, nextPage=None):
    request = youtube.commentThreads().list(
        part='snippet,replies',
        maxResults=100,
        order='relevance',
        videoId=vId,
        pageToken=nextPage
    )

    try:
        response = request.execute()
    except HttpError as e:
        print(f'#ERROR# {e}')
        return None
    return response


def get_all_comments(vId, db, nextPage=None):

    regex = r'^<a href=\".+\">(\d{1,2}:\d{2})</a>'
    with open(db, 'r') as db_read:
        data = json.load(db_read)

    while True:
        response = get_comments(vId, nextPage)
        if response:
            for item in response['items']:
                cText = item['snippet']['topLevelComment']['snippet']['textDisplay']
                research = re.search(regex, cText)
                if research:
                    data[vId]["cMatched"][item['snippet']['topLevelComment']['id']] = {
                        "cTimestamp": research.group(1),
                        "cText": cText,
                        "cLikeCount": item['snippet']['topLevelComment']['snippet']['likeCount']
                    }

            if 'nextPageToken' not in response:
                break
            else:
                nextPage = response['nextPageToken']
        else:
            print("No response")
            break

    data[vId]["cScanned"] = True
    print(f"Comments scanned for {vId}")

    with open(db, 'w') as db_write:
        json.dump(data, db_write)


def populate_comments():
    with open(DB, 'r') as db_read:
        data = json.load(db_read)

    track = 0
    for k, v in data.items():
        if v["cScanned"] == False:
            get_all_comments(k, DB)
            track += 1
        else:
            pass
        print(f'Added comments: {track} / {len(data)}')


def download_video(vId):
    ydl_opts = {'outtmpl': f'vids/{vId}/{vId}'}

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(f'https://www.youtube.com/watch?v={vId}')

    with open(DB, 'r') as db_read:
        data = json.load(db_read)

    for file in os.listdir(rf"vids\{vId}"):
        if re.search(vId, file):
            data[vId]["vFile"] = file

    data[vId]["vDownloaded"] = True
    print(f'Downloaded {vId}')

    with open(DB, 'w') as db_write:
        json.dump(data, db_write)


def download_multiple(limit: int = 5):
    with open(DB, 'r') as db_read:
        data = json.load(db_read)
    count = 0
    for k, v in data.items():
        if "vDownloaded" not in v:
            download_video(k)
            limit -= 1
            count += 1
        else:
            pass

        if limit == 0:
            break
    print(f'Downloaded {count} videos')


def review(vId, cCount: int = 10):
    with open(DB, 'r') as db_read:
        data = json.load(db_read)

    likeCount = []

    for k, v in data[vId]["cMatched"].items():
        likeCount.append((k, v["cLikeCount"]))

    likeCount.sort(key=lambda i: i[1], reverse=True)

    if len(likeCount) < cCount:
        cCount = len(likeCount)
    for cId in likeCount[:cCount]:
        qAssurance = "no"
        if "vCreated" not in data[vId]["cMatched"][cId[0]]:
            print(rf'mkdir vids\{vId}\{cId[0]}')
            subprocess.run(rf'mkdir vids\{vId}\{cId[0]}', shell=True)
            subprocess.run(
                rf'ffmpeg -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -i vids\{vId}\{data[vId]["vFile"]} -ss {data[vId]["cMatched"][cId[0]]["cTimestamp"]} -copyts -t 0:01:00 -c:a copy -c:v h264_nvenc -avoid_negative_ts make_zero vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv')
            print(f'{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv created.')
            afterTimestamp = re.search(
                r'^.{60,80}</a>(.+)', data[vId]["cMatched"][cId[0]]["cText"])
            afterAfterTimestamp = re.sub(r'[^a-zA-Z\d]+', afterTimestamp)
            print(
                f'{data[vId]["cMatched"][cId[0]]["cTimestamp"]} || {afterAfterTimestamp} || {data[vId]["cMatched"][cId[0]]["cLikeCount"]}')
            while (qAssurance == "no"):

                subprocess.run(
                    rf'vlc vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv --meta-title={afterAfterTimestamp} --video-title-timeout=60000')
                toCut = input(
                    'Select duration? 0 if irrelevant, 60 if full video: ')
                if toCut == '0':
                    os.remove(
                        rf'vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv')
                    print("Irrelevant")
                    break
                if toCut == '60':
                    print("Full")
                    break
                subprocess.run(
                    rf'ffmpeg -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -i vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv -ss 0:00:00 -copyts -t 0:00:{toCut} -c:a copy -c:v h264_nvenc -avoid_negative_ts make_zero vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}_edited.mkv')
                subprocess.run(
                    rf'vlc vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}_edited.mkv --meta-title={afterAfterTimestamp} --video-title-timeout=60000')
                qAssurance = input("Are you satisfied? ")
                if qAssurance == '':
                    os.remove(
                        rf'vids\{vId}\{cId[0]}\{data[vId]["vFile"][:-4]}_____{cId[0]}.mkv')

            x = {
                "title": afterTimestamp.group(1),
                "description": f"Watch the original video: https://youtu.be/{vId}\nIf you would like to remove the video, email me.\n#outofcontextproject #Shorts"
            }

            with open(rf'vids\{vId}\{cId[0]}\info.json', 'w') as json_write:
                json.dump(x, json_write)

            data[vId]["cMatched"][cId[0]]["vCreated"] = True

        else:
            print(f'{cId[0]} clip already exists. Continuing...')
            continue

    with open(DB, 'w') as db_write:
        json.dump(data, db_write)


def multiple_review(vCount, cCount):
    with open(DB, 'r') as db_read:
        data = json.load(db_read)

    for k, v in data.items():
        if "vDownloaded" in v:
            if "vReviewed" not in v:
                print(k)
                review(k, cCount)
                vCount -= 1
            else:
                print(f'{k} Already reviewed. Continuing')
                continue
        else:
            print(f'{k} Not downloaded. Continuing')
            continue

        if vCount == 0:
            break


def main():
    searchThis = input("Search what? ")
    if searchThis != '':
        get_search(searchThis, DB, 2)  # 100pts
    else:
        pass

    searchThis = input("Get all the unfetched comments in DB? ")
    if searchThis == "yes":
        populate_comments()   # n*track*1pts
    else:
        pass

    searchThis = input("Download how many? ")
    if searchThis != '':
        download_multiple(int(searchThis))
    else:
        pass

    multiple_review(2, 2)


if __name__ == '__main__':
    main()
