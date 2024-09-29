import os
import re
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import my_commands.database as db
from my_commands.stock_gpt import stock_gpt, get_reply
from my_commands.lottery_gpt import lottery_gpt
from my_commands.gold_gpt import gold_gpt
from my_commands.platinum_gpt import platinum_gpt
from my_commands.money_gpt import money_gpt
from my_commands.one04_gpt import one04_gpt, get_reply
from my_commands.partjob_gpt import partjob_gpt, get_reply
from my_commands.crypto_coin_gpt import crypto_gpt  # 新增這行，匯入 crypto_coin_gpt 模組

# 設定 LINE API 金鑰
line_token = os.getenv('LINE_TOKEN')
api = LineBotApi(line_token)

handler = WebhookHandler(os.getenv('LINE_SECRET'))
linenotify_token = os.getenv('LINENOTIFY_TOKEN')

app = Flask(__name__)

# 初始化對話歷史
conversation_history = []
# 設定最大對話記憶長度
MAX_HISTORY_LEN = 10


# 你的 LINE Channel Access Token
line_token = os.getenv('LINE_TOKEN')

# 要檢查 LINE Webhook URL 的函數
def check_line_webhook():
    url = "https://api.line.me/v2/bot/channel/webhook/endpoint"
    headers = {
        "Authorization": f"Bearer {line_token}"
    }
    response = requests.get(url, headers=headers)   # 發送 GET 請求檢查當前 Webhook URL
    if response.status_code == 200:
        current_webhook = response.json().get("endpoint", "無法取得 Webhook URL")
        print(f"當前 Webhook URL: {current_webhook}")
        return current_webhook
    else:
        print(f"檢查 Webhook URL 失敗，狀態碼: {response.status_code}, 原因: {response.text}")
        return None

# 更新 LINE Webhook URL 的函數
def update_line_webhook():
    ### 設定新的 Webhook URL ###
    new_webhook_url = "https://ed80e15d-dd5f-4d40-8280-a77fe6c70cdd-00-3nehzisex4ybh.sisko.replit.dev/"

    # 獲取當前的 Webhook URL
    current_webhook_url = check_line_webhook()

    # 如果當前的 Webhook URL 不同於新 URL，則更新
    if current_webhook_url != new_webhook_url:
        url = "https://api.line.me/v2/bot/channel/webhook/endpoint"
        headers = {
            "Authorization": f"Bearer {line_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "endpoint": new_webhook_url
        }

        response = requests.put(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Webhook URL 更新成功: {new_webhook_url}")
        else:
            print(f"更新失敗，狀態碼: {response.status_code}, 原因: {response.text}")
    else:
        print("當前的 Webhook URL 已是最新，無需更新。")
        

# 單人聊天室(...) 等待動畫
def start_loading_animation(chat_id, loading_seconds=5):
    url = 'https://api.line.me/v2/bot/chat/loading/start'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {line_token}'
    }
    data = {
        "chatId": chat_id,
        "loadingSeconds": loading_seconds
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.text

# 上線的Notify提醒機器人
def send_line_notify(message, sticker_package_id=None, sticker_id=None):
    url = 'https://notify-api.line.me/api/notify'
    headers = {
        'Authorization': f'Bearer {linenotify_token}',
    }
    payload = {
        'message': message,
    }
    if sticker_package_id and sticker_id:
        payload['stickerPackageId'] = sticker_package_id
        payload['stickerId'] = sticker_id

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print('訊息發送成功')
    else:
        print(f'發送失敗，狀態碼: {response.status_code}')

# 離線檢查機器人(google app script)
def call_google_apps_script():
    url = 'https://script.google.com/macros/s/AKfycbwiOSOYBPCluhETz8B-nWi3K-khT7TM9DUxDwMGxU0i1JzvXWQlOuJMWvVebkMCgbft/exec'  # 替換為您的 Google Apps Script URL
    response = requests.get(url)
    if response.status_code == 200:
        print('Google Apps Script 呼叫成功')
    else:
        print(f'Google Apps Script 呼叫失敗，狀態碼: {response.status_code}')

# 處理訊息事件
@app.post("/")
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("電子簽名錯誤，請檢查密鑰是否正確？")
        abort(400)

    return 'OK'

# 回應心跳事件
@app.route("/heartbeat", methods=['GET'])
def heartbeat():
    return "OK", 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global conversation_history

    user_message = event.message.text
    conversation_history.append({"role": "user", "content": user_message + " reply in 繁體中文"})

    if len(conversation_history) > MAX_HISTORY_LEN * 2:
        conversation_history = conversation_history[-MAX_HISTORY_LEN * 2:]

    # 將對話歷史加入消息列表
    msg = conversation_history[-MAX_HISTORY_LEN:]

    # 台股代碼邏輯：4-5個數字，且可選擇性有一個英文字母
    stock_code = re.search(r'\b\d{4,5}[A-Za-z]?\b', user_message)
    # 美股代碼邏輯：1-5個字母
    stock_symbol = re.search(r'\b[A-Za-z]{1,5}\b', user_message)

    # 顯示 start_loading(單人與機器人聊天才會有顯示)
    chat_id = event.source.user_id
    access_token = os.getenv('LINE_TOKEN')
    start_loading_animation(chat_id, 10)

    # 處理樂透信息
    if any(lottery_key.lower() in user_message.lower() for lottery_key in ["威力", "雙贏彩", "3星彩", "4星彩", "四星", "三星", "三星彩", "38樂合彩", "39樂合彩", "49樂合彩", "運彩"]):
        reply_text = lottery_gpt(user_message)
    elif user_message.lower().startswith("大盤") or user_message.lower().startswith("台股"):
        reply_text = stock_gpt("大盤")
    elif user_message.lower().startswith("美盤") or user_message.lower().startswith("美股"):  # 新增這行來處理「美盤」
        reply_text = stock_gpt("美盤")
    elif user_message.lower() == "539":
        reply_text = lottery_gpt(user_message)
    elif user_message.lower() == "大樂透" or user_message.lower() == "big":
        reply_text = lottery_gpt(user_message)
    elif any(user_message.lower().startswith(currency.lower()) for currency in ["金價", "金", "黃金", "gold"]):
        reply_text = gold_gpt()
    elif any(user_message.lower().startswith(currency.lower()) for currency in ["鉑", "鉑金", "platinum", "白金"]):
        reply_text = platinum_gpt()
    elif user_message.lower().startswith(tuple(["日幣", "日元", "jpy", "換日幣"])):
        reply_text = money_gpt("JPY")
    elif any(user_message.lower().startswith(currency.lower()) for currency in ["美金", "usd", "美元", "換美金"]):
        reply_text = money_gpt("USD")
    elif user_message.startswith("104:"):
        reply_text = one04_gpt(user_message[4:])
    elif user_message.startswith("pt:"):
        reply_text = partjob_gpt(user_message[3:])
    elif user_message.startswith("cb:"):  # 新增這個條件來處理加密貨幣查詢
        coin_id = user_message[3:].strip()
        reply_text = crypto_gpt(coin_id)
    elif user_message.startswith("$:"):  # 新增這個條件來處理加密貨幣查詢
        coin_id = user_message[2:].strip()
        reply_text = crypto_gpt(coin_id)
    elif stock_code:
        stock_id = stock_code.group()
        reply_text = stock_gpt(stock_id)
    elif stock_symbol:
        stock_id = stock_symbol.group()
        reply_text = stock_gpt(stock_id)
    else:
        print("*else*")
        msg.append({"role": "user", "content": user_message + " use zh-TW 繁體中文 回覆"})
        reply_text = get_reply(msg)

    conversation_history.append({"role": "assistant", "content": reply_text + "翻成繁體中文回答"})

    api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text))

   # print("AI醬版本: v1.3")
    print(user_message)
   


if __name__ == "__main__":
    try:
       # update_line_webhook()  # 啟動時自動更新 LINE Webhook URL#
        send_line_notify('重新上線', '446', '1989')
     #   call_google_apps_script() #訂時檢查離線API
        app.run(host='0.0.0.0', port=8080)  # 使用Replit默認的端口8080
    except Exception as e:
        send_line_notify(f"Ai醬發生錯誤: {e}", '446', '1989')
    finally:
        send_line_notify('Ai醬下線了', '11539', '52114121')
