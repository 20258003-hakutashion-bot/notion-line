import os
import time
import threading
import requests
from flask import Flask

# =========================
# 環境変数
# =========================

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LINE_TOKEN = os.environ["LINE_TOKEN"]

# Notion データベースID
DATABASE_ID = "3dd984275b318016b87a-c407900eb39a"

# 60秒ごとにNotionを確認
CHECK_INTERVAL = 60


# =========================
# Flask
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "Notion LINE Bot is running!"


# =========================
# Notionを確認
# =========================

def check_notion():

    notion_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    notion_headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    response = requests.post(
        notion_url,
        headers=notion_headers
    )

    print("Notion Status:", response.status_code)

    if response.status_code != 200:
        print("Notion Response:", response.text)
        return

    data = response.json()

    for page in data.get("results", []):

        properties = page["properties"]

        # LINEに通知するか
        line_check = properties["LINEに通知を入れるか"]["checkbox"]

        # すでに通知済みか
        notified = properties["通知済み"]["checkbox"]

        if not line_check:
            continue

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

            if first_file.get("type") == "external":

                detail_url = first_file["external"]["url"]

            elif first_file.get("type") == "file":

                detail_url = first_file["file"]["url"]

        print("新しいお知らせを発見！")
        print("タイトル:", title)
        print("本文:", body)
        print("詳細URL:", detail_url)

        # =========================
        # LINE送信
        # =========================

        line_url = "https://api.line.me/v2/bot/message/broadcast"

        line_headers = {
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json"
        }

        contents = [

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

            {
                "type": "separator",
                "margin": "xl"
            },

            {
                "type": "text",
                "text": title,
                "weight": "bold",
                "size": "xl",
                "color": "#333333",
                "margin": "xl",
                "wrap": True
            },

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

            contents.append({

                "type": "button",
                "style": "primary",
                "color": "#06C755",
                "margin": "xl",

                "action": {
                    "type": "uri",
                    "label": "詳細を見る",
                    "uri": detail_url
                }

            })

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

        # LINEへ送信

        line_response = requests.post(
            line_url,
            headers=line_headers,
            json=line_data
        )

        print("LINE Status:", line_response.status_code)
        print("LINE Response:", line_response.text)

        # =========================
        # 通知成功ならNotionを更新
        # =========================

        if line_response.status_code == 200:

            page_id = page["id"]

            update_url = (
                f"https://api.notion.com/v1/pages/{page_id}"
            )

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
                json=update_data
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
# 監視開始
# =========================

thread = threading.Thread(
    target=monitoring,
    daemon=True
)

thread.start()
