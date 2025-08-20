from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

from dotenv import load_dotenv
import os
from db import *
from imagemap import create_identity_imagemap

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

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
                update_user_step(user_id, 'ask_id')
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
            update_user_step(user_id, 'ask_id')
            update_user_mode(user_id, 'initial_fill')
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"你選擇的身分是：{msg}\n請輸入您的身分字號：")
            )

        # TBD 讓使用者修改個人資訊
        elif msg == "修改個人資料":

            # 將 mode 更改，讓修改資訊過程不是預設的線性流程回答，而只更改單一欄位。
            update_user_mode(user_id, 'modify_data')
            
            message = TemplateSendMessage(
                alt_text="修改個人資料",
                template=CarouselTemplate(
                    columns=[
                        CarouselColumn(
                            title="基本資料",
                            text="請選擇要修改的欄位：",
                            actions=[
                                MessageAction(label="身分證字號", text="修改_身分證字號"),
                                MessageAction(label="名字", text="修改_名字"),
                                MessageAction(label="生日", text="修改_生日"),
                            ]
                        ),
                        CarouselColumn(
                            title="聯絡資料",
                            text="請選擇要修改的欄位：",
                            actions=[
                                MessageAction(label="電話", text="修改_電話"),
                                MessageAction(label="Email", text="修改_Email"),
                                MessageAction(label="戶名或門牌", text="修改_戶名或門牌"),
                            ]
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, message)
            return
        
        elif msg.startswith("修改_"):
            update_user_mode(user_id, 'modify_data')
            field_map = {
                "修改_身分證字號": ("ask_id", "請輸入新的身分證字號："),
                "修改_名字": ("ask_name", "請輸入新的名字："),
                "修改_生日": ("ask_birthday", "請輸入新的生日（yyyy-mm-dd）："),
                "修改_電話": ("ask_phone", "請輸入新的電話號碼："),
                "修改_Email": ("ask_email", "請輸入新的 Email："),
                "修改_戶名或門牌": ("ask_address", "請輸入新的戶名或門牌："),
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

            if mode == 'modify_data':
                update_user_step(user_id, None)
                clear_user_mode(user_id)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 資料修改完畢，謝謝你的配合！"))
                return

            if step == 'ask_id':
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
                update_user_step(user_id, 'ask_address')
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入你的戶名或門牌："))
                return

            elif step == 'ask_address':
                update_user_field(user_id, 'address', user['temp_value'])
                clear_temp_value(user_id)
                update_user_step(user_id, None)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 所有資料已填寫完畢，謝謝你的配合！"))
                return

        elif msg == '重填':
            if step in ['ask_id', 'ask_name', 'ask_birthday', 'ask_phone', 'ask_email', 'ask_address']:
                clear_temp_value(user_id)
                question = {
                    'ask_id': "請重新輸入你的身分證字號：",
                    'ask_name': "請重新輸入你的名字：",
                    'ask_birthday': "請重新輸入你的生日（格式 yyyy-mm-dd）：",
                    'ask_phone': "請重新輸入你的電話號碼：",
                    'ask_email': "請重新輸入你的 Email：",
                    'ask_address': "請重新輸入你的戶名或門牌："
                }
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=question[step]))
                return

        elif step == 'ask_id':
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

        elif step == 'ask_address':
            update_temp_value(user_id, msg)
            reply_text = f"您輸入的戶名或門牌是：{msg}，正確嗎？"
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
            return


    # 雖然不期望他們選擇訪客，但還是做一下
    elif user['identity'] == '我是訪客':
        if msg == '我要報修':
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請先輸入身分才能報修喔"))
            return

if __name__ == "__main__":
    app.run()



# https://docs.google.com/forms/d/e/1FAIpQLSe_eMdAWSUVn7Ze6ZgF5F5aL3Dt2c4pEQGzZBzqFmuOp40EvQ/viewform?usp=pp_url&entry.1742058975=%E9%99%B3%E5%BA%A0%E5%AE%87&entry.1219801190=%E6%96%B0%E7%AB%B9%E5%B8%82%E6%98%8E%E6%B9%96%E8%B7%AF&entry.1168269233=0963656329&entry.83825998=shine.u.chen@gmail.com