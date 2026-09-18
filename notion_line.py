import os
import time
import threading
import requests
from flask import Flask

# =========================
# 設定
# =========================

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LINE_TOKEN = os.environ["LINE_TOKEN"]

DATABASE_ID = "3dd984275b318016b87ac407900eb39a"

# 1分ごとにNotionを確認
CHECK_INTERVAL = 60

app = Flask(__name__)


# =========================
# Webサーバー
# =========================

@app.route("/")
def home():
    return "Notion LINE Bot is running!"


# =========================
# Notionを確認する処理
# =========================

def check_notion():

    notion_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    notion_headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    print("Notion APIへ接続します...")

    try:

        response = requests.post(
    notion_url,
    headers=notion_headers,
    timeout=10
)

        print("Notion APIから返事が来ました！")
        print("Notion Status:", response.status_code)

    except requests.exceptions.ConnectTimeout:

        print("Notion APIへの接続がタイムアウトしました")
        return

    except requests.exceptions.ReadTimeout:

        print("Notion APIからの返事がタイムアウトしました")
        return

    except requests.exceptions.RequestException as e:

        print("Notion API通信エラー:", e)
        return

    if response.status_code != 200:

        print("Notion Response:", response.text)
        return

    data = response.json()

    # =========================
    # お知らせを確認
    # =========================

    for page in data.get("results", []):

        properties = page["properties"]

        line_check = properties["LINEに通知を入れるか"]["checkbox"]
        notified = properties["通知済み"]["checkbox"]

        # LINE通知しない
        if not line_check:
            continue

        # すでに通知済み
        if notified:
            continue

        # =========================
        # タイトル取得
        # =========================

        title_data = properties["タイトル"]["title"]

        title = ""

        if title_data:

            title = "".join(
                item["plain_text"]
                for item in title_data
            )

        # =========================
        # 本文取得
        # =========================

        body_data = properties["本文"]["rich_text"]

        body = ""

        for item in body_data:

            body += item["plain_text"]

        # =========================
        # リンク・ファイル取得
        # =========================

        file_data = properties["リンク、ファイル"]["files"]

        detail_url = None

        if file_data:

            first_file = file_data[0]

            # 外部URL
            if first_file.get("type") == "external":

                detail_url = first_file["external"]["url"]

            # Notionにアップロードしたファイル
            elif first_file.get("type") == "file":

                detail_url = first_file["file"]["url"]

        print("新しいお知らせを発見！")
        print("タイトル:", title)
        print("本文:", body)
        print("詳細URL:", detail_url)

        # =========================
        # LINEへ一斉送信
        # =========================

        line_url = "https://api.line.me/v2/bot/message/broadcast"

        line_headers = {
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json"
        }

        # =========================
        # Flexメッセージ
        # =========================

        contents = [

            # 見出し
            {
                "type": "box",
                "layout": "horizontal",
                "alignItems": "center",
                "contents": [

                    {
                        "type": "text",
                        "text": "📢",
                        "size": "xxl",
                        "flex": 0
                    },

                    {
                        "type": "text",
                        "text": "新着お知らせ",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#333333",
                        "margin": "md"
                    }

                ]
            },

            # 区切り線
            {
                "type": "separator",
                "margin": "xl"
            },

            # タイトル
            {
                "type": "text",
                "text": title,
                "weight": "bold",
                "size": "xl",
                "color": "#333333",
                "margin": "xl",
                "wrap": True
            },

            # 本文
            {
                "type": "text",
                "text": body,
                "size": "md",
                "color": "#555555",
                "margin": "lg",
                "wrap": True
            }

        ]

        # =========================
        # 詳細を見るボタン
        # =========================

        if detail_url:

            contents.append(
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#06C755",
                    "margin": "xl",
                    "action": {
                        "type": "uri",
                        "label": "詳細を見る",
                        "uri": detail_url
                    }
                }
            )

        else:

            print("リンク、ファイルが設定されていません。")

        # =========================
        # LINEメッセージ
        # =========================

        line_data = {

            "messages": [

                {
                    "type": "flex",

                    "altText": f"📢 新着お知らせ：{title}",

                    "contents": {

                        "type": "bubble",

                        "size": "mega",

                        "body": {

                            "type": "box",
                            "layout": "vertical",
                            "spacing": "lg",
                            "paddingAll": "lg",

                            "contents": contents

                        }

                    }

                }

            ]

        }

        # =========================
        # LINE送信
        # =========================

        line_response = requests.post(
            line_url,
            headers=line_headers,
            json=line_data,
            timeout=30
        )

        print("LINE Status:", line_response.status_code)
        print("LINE Response:", line_response.text)

        # =========================
        # LINE送信成功なら通知済みにする
        # =========================

        if line_response.status_code == 200:

            page_id = page["id"]

            update_url = f"https://api.notion.com/v1/pages/{page_id}"

            update_data = {

                "properties": {

                    "通知済み": {
                        "checkbox": True
                    }

                }

            }

            update_response = requests.patch(
                update_url,
                headers=notion_headers,
                json=update_data,
                timeout=30
            )

            print(
                "Notion通知済み更新:",
                update_response.status_code
            )

            if update_response.status_code == 200:

                print("通知完了！")

            else:

                print(
                    "Notion更新エラー:",
                    update_response.text
                )


# =========================
# 常時監視
# =========================

def monitoring():

    print("Notion監視を開始しました！")

    while True:

        print("Notionを確認しています...")

        check_notion()

        print(
            f"{CHECK_INTERVAL}秒後に再確認します。"
        )

        time.sleep(CHECK_INTERVAL)


# =========================
# Render起動時にNotion監視開始
# =========================

thread = threading.Thread(
    target=monitoring,
    daemon=True
)

thread.start()
