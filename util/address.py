import json
from linebot import LineBotApi, WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import *


def create_addresses_select_columns():
    with open('addresses.json', 'r', encoding='utf-8') as f:
        addresses = json.load(f)

    # 檢查地址列表是否為空
    if not addresses:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，目前沒有可供選擇的地址資訊。")
        )
        return

    # 1. 準備 CarouselTemplate 的 Columns 列表
    columns = []

    # 2. 遍歷地址列表，為每個地址建立一個 CarouselColumn
    for addr in addresses:
        
        # 每個地址 (addr) 成為一個 Column
        column = CarouselColumn(
            thumbnail_image_url = 'https://cdn.discordapp.com/attachments/873571198498377799/1426414059758157935/skirk.png?ex=68eb231d&is=68e9d19d&hm=a750d3cd305fc92a47553e45c7d686bfe9cad32a102fced385da41c0924f8115&',
            title=addr, 
            text='請確認並選擇此地址',
            actions=[
                MessageAction(
                    label='選擇此地址', 
                    text=addr 
                )
            ]
        )
        columns.append(column)

        # *** LINE CarouselTemplate 限制: 最多只能有 10 個 Columns ***
        # 如果地址數量超過 10 個，需要分頁或提供其他選擇方式
        if len(columns) >= 10:
            break # 達到上限，停止添加

    return columns