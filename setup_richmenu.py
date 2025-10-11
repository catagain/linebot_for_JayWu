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

def create_general_rich_menu():
    """創建【通用功能選單】的 Rich Menu 骨架。"""
    
    # 尺寸定義: 2500x1200 (頂部頁籤 200px, 功能區 1000px)
    menu_object = RichMenu(
        size=RichMenu.Size(width=2500, height=1200),
        selected=True, 
        name="通用功能選單 (分頁一)",
        chat_bar_text="選單",
        areas=[
            # A. 頁籤區域 (所有頁面都一樣)
            
            # A1: 通用功能頁籤 (當前頁籤)
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=200),
                action=PostbackAction(label='通用功能', data='action=switch_menu&target=general')
            ),
            # A2: 住戶功能頁籤
            RichMenuArea(
                bounds=RichMenuBounds(x=834, y=0, width=833, height=200),
                action=PostbackAction(label='住戶功能', data='action=switch_menu&target=resident')
            ),
            # A3: 預售屋專區頁籤
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=0, width=833, height=200),
                action=PostbackAction(label='預售屋專區', data='action=switch_menu&target=presell')
            ),
            
            # B. 功能區 (y=201, height=500)
            
            # B1: 重設個人資訊
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=201, width=833, height=500),
                action=MessageAction(text='重設個人資訊')
            ),
            # B2: 我的資料
            RichMenuArea(
                bounds=RichMenuBounds(x=834, y=201, width=833, height=500),
                action=MessageAction(text='我的資料')
            ),
            # B3: 私訊客服
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=201, width=833, height=500),
                action=MessageAction(text='私訊客服')
            )
        ]
    )
    
    # 執行 API 呼叫，創建骨架並返回 ID
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=menu_object)
    global RICH_MENU_GENERAL_ID
    RICH_MENU_GENERAL_ID = rich_menu_id
    return rich_menu_id

def create_resident_rich_menu():
    """創建【住戶功能選單】的 Rich Menu 骨架。"""
    
    menu_object = RichMenu(
        size=RichMenu.Size(width=2500, height=1200),
        selected=True, 
        name="住戶功能選單 (分頁二)",
        chat_bar_text="選單",
        areas=[
            # A. 頁籤區域 (保持一致，確保切換邏輯不變)
            RichMenuArea(bounds=RichMenuBounds(x=0, y=0, width=833, height=200), action=PostbackAction(label='通用功能', data='action=switch_menu&target=general')),
            RichMenuArea(bounds=RichMenuBounds(x=834, y=0, width=833, height=200), action=PostbackAction(label='住戶功能', data='action=switch_menu&target=resident')),
            RichMenuArea(bounds=RichMenuBounds(x=1667, y=0, width=833, height=200), action=PostbackAction(label='預售屋專區', data='action=switch_menu&target=presell')),
            
            # B. 功能區 (單一按鈕：我要報修)
            
            # B1: 我要報修 (佔滿整個功能區)
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=201, width=2500, height=500),
                action=MessageAction(text='我要報修')
            )
        ]
    )
    
    # 🚨 執行 API 呼叫，創建骨架並返回 ID
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=menu_object)
    global RICH_MENU_RESIDENT_ID
    RICH_MENU_RESIDENT_ID = rich_menu_id
    return rich_menu_id

def create_presell_rich_menu():
    """創建【預售屋專區選單】的 Rich Menu 骨架。"""
    
    menu_object = RichMenu(
        size=RichMenu.Size(width=2500, height=1200),
        selected=True, 
        name="預售屋專區選單 (分頁三)",
        chat_bar_text="選單",
        areas=[
            # A. 頁籤區域 (保持一致)
            RichMenuArea(bounds=RichMenuBounds(x=0, y=0, width=833, height=200), action=PostbackAction(label='通用功能', data='action=switch_menu&target=general')),
            RichMenuArea(bounds=RichMenuBounds(x=834, y=0, width=833, height=200), action=PostbackAction(label='住戶功能', data='action=switch_menu&target=resident')),
            RichMenuArea(bounds=RichMenuBounds(x=1667, y=0, width=833, height=200), action=PostbackAction(label='預售屋專區', data='action=switch_menu&target=presell')),
            
            # B. 功能區 (兩個按鈕)
            
            # B1: 預約客變時間 (左半邊)
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=201, width=1250, height=500),
                action=MessageAction(text='預約客變時間')
            ),
            # B2: 各階段款項上傳 (右半邊)
            RichMenuArea(
                bounds=RichMenuBounds(x=1251, y=201, width=1249, height=500), # 寬度可以稍微調整以湊滿 2500
                action=MessageAction(text='各階段款項上傳')
            )
        ]
    )
    
    # 🚨 執行 API 呼叫，創建骨架並返回 ID
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=menu_object)
    global RICH_MENU_PRESELL_ID
    RICH_MENU_PRESELL_ID = rich_menu_id
    return rich_menu_id

"""
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
"""