import sqlite3
import json
from app import connect_to_db
from app import end_db



def main():
    conn, cursor = connect_to_db()


    with open('store.json', 'r') as rf:
        pdata = json.load(rf)

    sql = f'SELECT name FROM sqlite_master WHERE type="table"'
    cursor.execute(sql)
    for i in cursor:
        print(i)

    
    i=''

    # ydl_opts = {}
    # with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    #     result = ydl.extract_info(f'https://www.youtube.com/watch?v={i}')

    



    end_db(conn)


if __name__ == '__main__':
    main()