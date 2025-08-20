from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

from dotenv import load_dotenv
import os
from db import *
from imagemap import create_identity_imagemap

load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

rich_menu_to_create = RichMenu(
    size={"width": 2500, "height": 843},
    selected=True,
    name="Main Menu",
    chat_bar_text="點我開啟選單",
    areas=[
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=MessageAction(label="修改個人資訊", text="修改個人資訊")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=MessageAction(label="我要報修", text="我要報修")
        )
    ]
)


rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
with open("richmenu.jpg", 'rb') as f:
    line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)

line_bot_api.set_default_rich_menu(rich_menu_id)