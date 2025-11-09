import json
import os
from linebot import LineBotApi, WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

# 取得正確的檔案路徑
def get_correct_path(filename):
    # 方案 1: 回到上一層目錄後找檔案
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(parent_dir, filename)

# 地址與照片 URL 對應表
ADDRESS_IMAGES = {
    "鷁欣緻境": "https://img2.591.com.tw/house/2023/10/18/169760391235376409.jpg!900x.water3.jpg",
    "鷁崎緻鄰": "https://scontent.ftpe3-2.fna.fbcdn.net/v/t39.30808-6/489739408_1223168263150410_3463683946423401988_n.jpg?_nc_cat=107&ccb=1-7&_nc_sid=127cfc&_nc_ohc=EleX0EMME9oQ7kNvwGsUvn6&_nc_oc=AdlseOoh3hljH7T8kgd--v5r8_OiiRT1C_ckGmfTKDMd-YMmTE4fMno-w8lug24BdbCDGZQXYLIOC5IY1ChaLTMv&_nc_zt=23&_nc_ht=scontent.ftpe3-2.fna&_nc_gid=XEQoFMlopq6CRJqxFHGH0w&oh=00_Afjr0nM1MfAMODU4TlKAFaXN_DI-u4tZWPAF6pwPmb_UBQ&oe=69151CCB",

    # 預設圖片，當找不到對應地址時使用
    "default": "https://img2.591.com.tw/house/2023/10/18/169760391235376409.jpg!900x.water3.jpg"
}

def create_addresses_select_columns():
    try:
        # 使用正確路徑開啟檔案
        with open(get_correct_path('addresses.json'), 'r', encoding='utf-8') as f:
            addresses = json.load(f)

        # 檢查地址列表是否為空
        if not addresses:
            return []  # 返回空列表，由呼叫者處理

        # 1. 準備 CarouselTemplate 的 Columns 列表
        columns = []

        # 2. 遍歷地址列表，為每個地址建立一個 CarouselColumn
        for addr in addresses:
            # 從對應表取得圖片 URL，如果沒有則使用預設圖片
            image_url = ADDRESS_IMAGES.get(addr, ADDRESS_IMAGES["default"])
            
            # 每個地址 (addr) 成為一個 Column
            column = CarouselColumn(
                thumbnail_image_url = image_url,
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
            if len(columns) >= 10:
                break # 達到上限，停止添加

        return columns
    except Exception as e:
        print(f"讀取地址檔案時發生錯誤: {e}")
        return []  # 發生錯誤時返回空列表