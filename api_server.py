from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
import requests, cv2, numpy as np
from pyzbar.pyzbar import decode
import io
import os  # สำหรับดึง Environment Variables

app = Flask(__name__)

# 🧩 ใช้ Environment Variables แทนใส่ตรง ๆ
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# เมื่อได้รับข้อความ
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text.lower()
    if "สลิป" in msg or "ตรวจ" in msg:
        reply = "📸 กรุณาส่งรูปสลิปเงินโอนเพื่อทำการตรวจสอบ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# เมื่อได้รับรูปภาพ
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = io.BytesIO(message_content.content)
    img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)

    decoded_objs = decode(img)
    if not decoded_objs:
        reply = "❌ ไม่พบ QR Code ในสลิป กรุณาลองใหม่อีกครั้ง"
    else:
        data = decoded_objs[0].data.decode('utf-8')
        if "000201" in data:
            reply = check_slip_detail(data)
        else:
            reply = "⚠️ QR Code ไม่ตรงตามรูปแบบสลิปโอนเงิน"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

def check_slip_detail(qr_data):
    # ตัวอย่างจำลองผลลัพธ์
    result = {
        "status": "valid",
        "bank": "SCB",
        "amount": "500.00",
        "date": "21/10/2025 10:12"
    }

    if result["status"] == "valid":
        return f"✅ สลิปถูกต้อง\nธนาคาร: {result['bank']}\nจำนวนเงิน: {result['amount']} บาท\nวันที่โอน: {result['date']}"
    else:
        return "❌ สลิปปลอม หรือไม่สามารถตรวจสอบได้"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
