import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LINE_TOKEN = os.environ["LINE_TOKEN"]

DATABASE_ID = "3dd984275b318016b87ac407900eb39a"

# =========================
# Notionからお知らせを取得
# =========================

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

data = response.json()

# =========================
# お知らせを確認
# =========================

for page in data["results"]:

    properties = page["properties"]

    line_check = properties["LINEに通知を入れるか"]["checkbox"]
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
        title = title_data[0]["text"]["content"]

    # =========================
    # 本文取得
    # =========================

    body_data = properties["本文"]["rich_text"]

    body = ""

    for item in body_data:
        body += item["text"]["content"]

    print("新しいお知らせを発見！")
    print("タイトル:", title)
    print("本文:", body)

    # =========================
    # LINEへ一斉送信
    # =========================

    line_url = "https://api.line.me/v2/bot/message/broadcast"

    line_headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

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

                        "contents": [

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
                            },

                            # 詳細を見るボタン
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#06C755",
                                "margin": "xl",
                                "action": {
                                    "type": "uri",
                                    "label": "詳細を見る",
                                    "uri": "https://kikusui-net.com/news/"
                                }
                            }
                        ]
                    }
                }
            }
        ]
    }

    line_response = requests.post(
        line_url,
        headers=line_headers,
        json=line_data
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
            json=update_data
        )

        print("Notion通知済み更新:", update_response.status_code)

        if update_response.status_code == 200:
            print("通知完了！")