from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import json
import random
import string

from dotenv import load_dotenv
import os
from db import *
from imagemap import create_identity_imagemap

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# TBD 
# address 選擇清單的函式化
# 預售屋的房子特別標示
# 檢查保固
# 報修時的地址選擇

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id

    # 如果第一次加好友，就新增到資料庫（避免重複）
    if not user_exists(user_id):
        add_user(user_id)

    # 傳送 imagemap 訊息詢問身分
    imagemap_msg = create_identity_imagemap()
    line_bot_api.reply_message(event.reply_token, imagemap_msg)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id

    # 第一次來的使用者
    if not user_exists(user_id):
        add_user(user_id)
        imagemap_msg = create_identity_imagemap()
        line_bot_api.reply_message(event.reply_token, imagemap_msg)
        return

    # 其他訊息處理（身份選擇後）
    msg = event.message.text
    user = get_user(user_id)

    if not user['identity']:
        if msg in ['我是訪客', '我是住戶']:

            update_identity(user_id, msg)

            if msg == '我是住戶':

                # step 紀錄目前詢問的個人資訊；mode 紀錄是否是第一次填寫，若否代表是在更改個人訊息，不使用預設的填寫流程。
                update_user_step(user_id, 'ask_id_number')
                update_user_mode(user_id, 'initial_fill')
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"你選擇的身分是：{msg}\n請輸入您的身分字號：")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"你選擇的身分是：{msg}\n感謝您的回覆！")
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請先選擇身分喔！")
            )

    # 如果是住戶，進行多輪提問，取得對方資訊
    if user['identity'] == '我是住戶':
        step = user['step']
        mode = user['mode']

        if msg == '我是住戶':
            update_user_step(user_id, 'ask_id_number')
            update_user_mode(user_id, 'initial_fill')
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"你選擇的身分是：{msg}\n請輸入您的身分字號：")
            )

        if msg == '我的個人資料':
            # 取得使用者所有資訊
            user_info = get_user(user_id)
            if user_info and user_info['identity'] == '我是住戶':
                # 格式化並回覆使用者資訊
                addresses_text = '\n'.join(user_info.get('addresses', [])) if user_info.get('addresses') else "未設定"
                profile_text = (
                    f"✅ 你的個人資料：\n"
                    f"身分：{user_info.get('identity', '未設定')}\n"
                    f"身分證字號：{user_info.get('id_number', '未設定')}\n"
                    f"名字：{user_info.get('name', '未設定')}\n"
                    f"生日：{user_info.get('birthday', '未設定')}\n"
                    f"電話：{user_info.get('phone', '未設定')}\n"
                    f"Email：{user_info.get('email', '未設定')}\n"
                    f"戶名或門牌：\n{addresses_text}"
                )
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=profile_text)
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請先完成住戶身份認證才能查看個人資料喔！")
                )
            return # 處理完畢後直接結束

        # 讓使用者修改個人資訊
        elif msg == "修改個人資訊":

            # 將 mode 更改，讓修改資訊過程不是預設的線性流程回答，而只更改單一欄位。
            update_user_mode(user_id, 'modify_data')
            
            message = TemplateSendMessage(
                alt_text="修改個人資訊",
                template=CarouselTemplate(
                    columns=[
                        CarouselColumn(
                            title="基本資訊",
                            text="請選擇要修改的欄位：",
                            actions=[
                                MessageAction(label="身分證字號", text="修改_身分證字號"),
                                MessageAction(label="名字", text="修改_名字"),
                                MessageAction(label="生日", text="修改_生日"),
                            ]
                        ),
                        CarouselColumn(
                            title="聯絡資訊",
                            text="請選擇要修改的欄位：",
                            actions=[
                                MessageAction(label="電話", text="修改_電話"),
                                MessageAction(label="Email", text="修改_Email"),
                                MessageAction(label="戶名或門牌", text="修改_戶名或門牌"),
                            ]
                        ),
                        CarouselColumn(
                            title="新增資訊",
                            text="請選擇要修改的欄位：",
                            actions=[
                                MessageAction(label="新增戶名聯絡人", text="新增戶名聯絡人"),
                                MessageAction(label="Email", text="修改_Email"),
                                MessageAction(label="戶名或門牌", text="修改_戶名或門牌"),
                            ]
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, message)
            return

        elif msg == '我的地址密碼':
            # 取得使用者綁定的所有地址，這部分是從你的資料庫讀取
            
            if not user['address']:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="你目前沒有綁定的地址。"))
                return
            
            # 將地址字串轉換為列表，以便生成選單
            addresses = user['addresses']
            
            # 檢查地址列表是否為空，理論上在上面已經處理過
            if not addresses:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="你目前沒有綁定的地址。"))
                return
            
            # 檢查地址數量是否超過限制
            if len(addresses) > 10:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="你綁定的地址數量過多，請聯繫管理員。"))
                return

            carousel_columns = []
            for addr in addresses:
                # 建立每個地址的 actions
                actions = [
                    MessageAction(
                        label="查詢密碼",
                        text=f"查詢密碼：{addr}"
                    ),
                    MessageAction(
                        label="重新生成密碼",
                        text=f"重新生成密碼：{addr}"
                    ),
                    MessageAction(
                        label="取消",
                        text="取消"
                    )
                ]

                # 建立一個新的 CarouselColumn，將地址作為 title
                carousel_columns.append(
                    CarouselColumn(
                        title=addr,
                        text="請選擇操作：",
                        actions=actions
                    )
                )
                
            message = TemplateSendMessage(
                alt_text="請選擇地址",
                template=CarouselTemplate(columns=carousel_columns)
            )
            line_bot_api.reply_message(event.reply_token, message)
            return

        # 處理查詢密碼
        elif msg.startswith('查詢密碼：'):
            # 從訊息中提取出完整的地址
            selected_address = msg.replace('查詢密碼：', '')
            
            # 檢查該使用者是否確實綁定了這個地址
            if selected_address not in user['addresses']:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="你沒有綁定這個地址，無法查詢密碼。")
                )
                return

            # 從 JSON 檔案中查詢密碼
            address_info = get_address_info(selected_address)
            if address_info:
                reply_text = f"你的地址【{selected_address}】的密碼是：{address_info['password']}"
            else:
                reply_text = "該地址無密碼資訊，請聯繫管理員。"
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return

        # 處理重新生成密碼
        elif msg.startswith('重新生成密碼：'):
            # 從訊息中提取出完整的地址
            selected_address = msg.replace('重新生成密碼：', '')
            
            # 檢查該使用者是否確實綁定了這個地址
            addresses_str = user.get('addresses', '')
            if selected_address not in user['addresses']:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="你沒有綁定這個地址，無法重新生成密碼。")
                )
                return

            # 生成新的隨機密碼並更新 JSON 檔案
            new_password = generate_new_password()
            update_address_info(selected_address, new_password)
            
            reply_text = f"你的地址【{selected_address}】的新密碼是：{new_password}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            return

        # 提供複數帳號想擁有相同戶名的方式
        elif msg == "新增戶名聯絡人":

            return
        
        elif msg.startswith("修改_"):

            # 戶名門牌用選擇的，故另外處理
            if msg == '修改_戶名或門牌':
                update_user_mode(user_id, 'modify_data')
                update_user_step(user_id, 'ask_address_1')

                # 讀取本地的 addresses.json 檔案
                with open('addresses.json', 'r', encoding='utf-8') as f:
                    addresses = json.load(f)

                # 將地址轉換為 ButtonTemplate 的 actions
                actions = [
                    MessageAction(
                        label=addr,
                        text=addr
                    ) for addr in addresses
                ]

                # 建立選單訊息
                address_selection_msg = TemplateSendMessage(
                    alt_text='請選擇你的戶名或門牌',
                    template=ButtonsTemplate(
                        title='請選擇你的戶名或門牌',
                        text='請從以下選項中選擇你的地址：',
                        actions=actions
                    )
                )

                line_bot_api.reply_message(event.reply_token, address_selection_msg)               
                return

            update_user_mode(user_id, 'modify_data')
            field_map = {
                "修改_身分證字號": ("ask_id_number", "請輸入新的身分證字號："),
                "修改_名字": ("ask_name", "請輸入新的名字："),
                "修改_生日": ("ask_birthday", "請輸入新的生日（yyyy-mm-dd）："),
                "修改_電話": ("ask_phone", "請輸入新的電話號碼："),
                "修改_Email": ("ask_email", "請輸入新的 Email：")
            }
            step, question = field_map[msg]
            update_user_step(user_id, step)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=question))
            return

        elif msg == '我要報修':
            base_url = "https://docs.google.com/forms/d/e/1FAIpQLSe_eMdAWSUVn7Ze6ZgF5F5aL3Dt2c4pEQGzZBzqFmuOp40EvQ/viewform"
            entry_field_name = 'entry.1742058975'
            entry_field_address = 'entry.1219801190'
            entry_field_phone = 'entry.1168269233'

            user_name = user['name']
            user_address = user['address']
            user_phone = user['phone']
            prefill_url = f'{base_url}?usp=pp_url&{entry_field_name}={user_name}&{entry_field_address}={user_address}&{entry_field_phone}={user_phone}'
            message = TextSendMessage(
                text=f"請填寫以下報修表單 👇\n{prefill_url}"
            )

            line_bot_api.reply_message(event.reply_token, message)
        
        elif msg == '確認':

            # 如果使用者是修改資料，mode 會是 modify_data，則不繼續進行提問
            if mode == 'modify_data':
                # 將地址額外詢問
                if step == 'ask_address':
                    full_address = user['temp_value']
                    try:
                        with open('available_addresses.json', 'r+', encoding='utf-8') as f:
                            available_addresses = json.load(f)

                            # 檢查完整的地址是否存在於列表中
                            address_exists = any(item["address"] == full_address for item in available_addresses)

                            if address_exists:
                                # 如果地址存在，將完整地址暫存，並進入下一步驟詢問密碼
                                update_temp_value(user_id, full_address)
                                update_user_step(user_id, 'ask_password')
                                
                                line_bot_api.reply_message(
                                    event.reply_token,
                                    TextSendMessage(text="此地址存在，請輸入該地址的綁定密碼：")
                                )
                            else:
                                # 如果地址不存在，給予錯誤提示，並讓使用者重填
                                line_bot_api.reply_message(
                                    event.reply_token,
                                    TextSendMessage(text="此地址不存在於可新增列表中，請確認後重新輸入門牌號碼")
                                )
                                clear_temp_value(user_id)
                                update_user_step(user_id, None)

                            """ 舊 address 系統
                            if full_address in available_addresses:
                                # **只有在確認時才從檔案中刪除地址**
                                available_addresses.remove(full_address)
                                f.seek(0)
                                json.dump(available_addresses, f, ensure_ascii=False, indent=2)
                                f.truncate()

                                # 將地址寫入使用者資料
                                append_address(user_id, full_address)
                                clear_temp_value(user_id)
                                update_user_step(user_id, None)
                                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 新地址已成功新增！"))
                            else:
                                # 如果地址已經被其他使用者新增了，給出提示
                                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此地址已被其他使用者新增，請聯繫管理員。"))
                                clear_temp_value(user_id)
                                update_user_step(user_id, None)
                            """

                    except FileNotFoundError:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="地址清單檔案不存在，請聯繫管理員。"))
                        clear_temp_value(user_id)
                        update_user_step(user_id, None)
                    return

                else:
                    update_user_field(user_id, step[4:], user['temp_value'])
                    update_user_step(user_id, None)
                    clear_user_mode(user_id)
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 資料修改完畢，謝謝你的配合！"))
                    return

            if step == 'ask_id_number':
                update_user_field(user_id, 'id_number', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, 'ask_name')
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入你的名字"))
                return

            elif step == 'ask_name':
                update_user_field(user_id, 'name', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, 'ask_birthday')
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入你的生日（格式 yyyy-mm-dd）："))
                return

            elif step == 'ask_birthday':
                update_user_field(user_id, 'birthday', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, 'ask_phone')
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入你的電話號碼："))
                return

            elif step == 'ask_phone':
                update_user_field(user_id, 'phone', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, 'ask_email')
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入你的 Email："))
                return

            elif step == 'ask_email':
                update_user_field(user_id, 'email', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, 'ask_address_1')
               
                # 讀取本地的 addresses.json 檔案
                with open('addresses.json', 'r', encoding='utf-8') as f:
                    addresses = json.load(f)

                # 將地址轉換為 ButtonTemplate 的 actions
                actions = [
                    MessageAction(
                        label=addr,
                        text=addr
                    ) for addr in addresses
                ]

                # 建立選單訊息
                address_selection_msg = TemplateSendMessage(
                    alt_text='請選擇你的戶名或門牌',
                    template=ButtonsTemplate(
                        title='請選擇你的戶名或門牌',
                        text='請從以下選項中選擇你的地址：',
                        actions=actions
                    )
                )

                line_bot_api.reply_message(event.reply_token, address_selection_msg)
                return

            elif step == 'ask_address':
                user = get_user(user_id)

                # 不再讓使用者可以更改地址，而是只能新增
                # update_user_field(user_id, 'address', user['temp_value'])
                # append_address(user_id, user['temp_value'])

                full_address = user['temp_value']

                try:
                    available_addresses = json.load(f)

                    # 檢查完整的地址是否存在於列表中
                    address_exists = any(item["address"] == full_address for item in available_addresses)

                    if address_exists:
                        # 如果地址存在，將完整地址暫存，並進入下一步驟詢問密碼
                        update_temp_value(user_id, full_address)
                        update_user_step(user_id, 'ask_password')
                        
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="此地址存在，請輸入該地址的綁定密碼：")
                        )
                    else:
                        # 如果地址不存在，給予錯誤提示，並讓使用者重填
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="此地址不存在於可新增列表中，請確認後重新輸入門牌號碼")
                        )
                        clear_temp_value(user_id)
                        update_user_step(user_id, None)
                    """
                    with open('available_addresses.json', 'r+', encoding='utf-8') as f:
                        available_addresses = json.load(f)

                        if full_address in available_addresses:
                            # **只有在確認時才從檔案中刪除地址**
                            available_addresses.remove(full_address)
                            f.seek(0)
                            json.dump(available_addresses, f, ensure_ascii=False, indent=2)
                            f.truncate()

                            # 將地址寫入使用者資料
                            append_address(user_id, full_address)
                            clear_temp_value(user_id)
                            update_user_step(user_id, None)
                            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 新地址已成功新增！\n完成所有填答啦！"))
                        else:
                            # 如果地址已經被其他使用者新增了，給出提示
                            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="此地址已被其他使用者新增，請聯繫管理員。"))
                            clear_temp_value(user_id)
                            update_user_step(user_id, None)
                    """
                except FileNotFoundError:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="地址清單檔案不存在，請聯繫管理員。"))
                    clear_temp_value(user_id)
                    update_user_step(user_id, None)
                return

        elif msg == '重填':
            if step in ['ask_id_number', 'ask_name', 'ask_birthday', 'ask_phone', 'ask_email']:
                clear_temp_value(user_id)
                question = {
                    'ask_id_number': "請重新輸入你的身分證字號：",
                    'ask_name': "請重新輸入你的名字：",
                    'ask_birthday': "請重新輸入你的生日（格式 yyyy-mm-dd）：",
                    'ask_phone': "請重新輸入你的電話號碼：",
                    'ask_email': "請重新輸入你的 Email：",
                }
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=question[step]))
                return
            elif step == 'ask_address':
                update_user_step(user_id, "ask_address_1")
                with open('addresses.json', 'r', encoding='utf-8') as f:
                    addresses = json.load(f)

                # 將地址轉換為 ButtonTemplate 的 actions
                actions = [
                    MessageAction(
                        label=addr,
                        text=addr
                    ) for addr in addresses
                ]
                address_selection_msg = TemplateSendMessage(
                    alt_text='請選擇你的戶名或門牌',
                    template=ButtonsTemplate(
                        title='請選擇你的戶名或門牌',
                        text='請從以下選項中選擇你的地址：',
                        actions=actions
                    )
                )
                line_bot_api.reply_message(event.reply_token, address_selection_msg)
                return
        # 新增地址的密碼
        elif step == "ask_password":
            entered_password = msg
            full_address = user['temp_value']
            
            try:
                with open('available_addresses.json', 'r', encoding='utf-8') as f:
                    available_addresses = json.load(f)

                # 找到對應地址的密碼
                correct_password = None
                for item in available_addresses:
                    if item["address"] == full_address:
                        correct_password = item["password"]
                        break
                
                if correct_password and correct_password == entered_password:
                    # 密碼正確，進入確認環節
                    append_address(user_id, full_address)
                    clear_temp_value(user_id)
                    update_user_step(user_id, None)

                    # 新增後更改密碼
                    new_password = generate_new_password()
                    update_address_info(full_address, new_password)
                    
                    reply_text = f"你的地址【{full_address}】的新密碼是：{new_password}"

                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ 新地址已成功新增！\n{reply_text}"))

                else:
                    # 密碼錯誤
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="密碼錯誤，請重新輸入：")
                    )
                    
            except FileNotFoundError:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="地址清單檔案不存在，請聯繫管理員。")
                )
            return

        elif step == 'ask_id_number':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的身分證字號是：{msg}，正確嗎？"
            confirm_msg = TemplateSendMessage(
                alt_text='請確認身分證字號',
                template=ConfirmTemplate(
                    text=reply_text,
                    actions=[
                        MessageAction(label='✅ 正確', text='確認'),
                        MessageAction(label='🔁 重填', text='重填')
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_msg)
            return

        elif step == 'ask_name':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的名字是：{msg}，正確嗎？"
            confirm_msg = TemplateSendMessage(
                alt_text='請確認名字',
                template=ConfirmTemplate(
                    text=reply_text,
                    actions=[
                        MessageAction(label='✅ 正確', text='確認'),
                        MessageAction(label='🔁 重填', text='重填')
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_msg)
            return

        elif step == 'ask_birthday':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的生日是：{msg}，正確嗎？"
            confirm_msg = TemplateSendMessage(
                alt_text='請確認生日',
                template=ConfirmTemplate(
                    text=reply_text,
                    actions=[
                        MessageAction(label='✅ 正確', text='確認'),
                        MessageAction(label='🔁 重填', text='重填')
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_msg)
            return

        elif step == 'ask_phone':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的電話號碼是：{msg}，正確嗎？"
            confirm_msg = TemplateSendMessage(
                alt_text='請確認電話號碼',
                template=ConfirmTemplate(
                    text=reply_text,
                    actions=[
                        MessageAction(label='✅ 正確', text='確認'),
                        MessageAction(label='🔁 重填', text='重填')
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_msg)
            return

        elif step == 'ask_email':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的 Email 是：{msg}，正確嗎？"
            confirm_msg = TemplateSendMessage(
                alt_text='請確認 Email',
                template=ConfirmTemplate(
                    text=reply_text,
                    actions=[
                        MessageAction(label='✅ 正確', text='確認'),
                        MessageAction(label='🔁 重填', text='重填')
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_msg)
            return

        # 在使用者想要新增戶名時，先產生選單給使用者選擇
        # 順序 ask_address_1 -> ask_address
        elif step == 'ask_address_1':

            update_temp_value(user_id, msg)
            reply_text = f"您選擇的戶名是：{msg}，請輸入門牌"
            update_user_step(user_id, 'ask_address')
            line_bot_api.reply_message(event.reply_token,  TextSendMessage(text=reply_text))


        elif step == 'ask_address':
            full_address = f"{user['temp_value']}_{msg}"
    
            # 檢查地址是否存在，但先不刪除
            try:
                with open('available_addresses.json', 'r', encoding='utf-8') as f:
                    available_addresses = json.load(f)

                    address_exists = any(item["address"] == full_address for item in available_addresses)
                    
                    if address_exists:
                        # 地址存在，將完整地址暫存
                        update_temp_value(user_id, full_address)
                        
                        reply_text = f"您輸入的戶名或門牌是：{full_address}，正確嗎？"
                        confirm_msg = TemplateSendMessage(
                            alt_text='請確認戶名或門牌',
                            template=ConfirmTemplate(
                                text=reply_text,
                                actions=[
                                    MessageAction(label='✅ 正確', text='確認'),
                                    MessageAction(label='🔁 重填', text='重填')
                                ]
                            )
                        )
                        line_bot_api.reply_message(event.reply_token, confirm_msg)

                    else:
                        # 讓使用者停在這個狀態，可以一直輸入戶名
                        update_user_step(user_id, 'ask_address')
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text="此地址不存在於可新增列表中，請確認後再試一次。")
                        )
                        
            except FileNotFoundError:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="地址清單檔案不存在，請聯繫管理員。")
                )
            return


    # 雖然不期望他們選擇訪客，但還是做一下
    elif user['identity'] == '我是訪客':
        if msg == '我要報修':
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先輸入身分才能報修喔"))
            return

if __name__ == "__main__":
    app.run()



# https://docs.google.com/forms/d/e/1FAIpQLSe_eMdAWSUVn7Ze6ZgF5F5aL3Dt2c4pEQGzZBzqFmuOp40EvQ/viewform?usp=pp_url&entry.1742058975=%E9%99%B3%E5%BA%A0%E5%AE%87&entry.1219801190=%E6%96%B0%E7%AB%B9%E5%B8%82%E6%98%8E%E6%B9%96%E8%B7%AF&entry.1168269233=0963656329&entry.83825998=shine.u.chen@gmail.com