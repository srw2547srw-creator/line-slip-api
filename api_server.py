from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
import requests, cv2, numpy as np
from pyzbar.pyzbar import decode
import io

app = Flask(__name__)

# 🧩 ใส่ Token และ Secret ของคุณ
CHANNEL_ACCESS_TOKEN = "wGObwEuHAdaO21oZJRoPx0Yt/DZAWN4ZyU2v9xk3JT4cSZ1DqxUb9IxpEgCCWm+eI+tv2XCtDBSHl7WvbcXfA0N7ePQGgrOnT2Ui2mfi8EpDjPfRsU4Dybz6AHCdjTSYn3ZRHhJAAkA7es1BCpojEgdB04t89/1O/w1cDnyilFU="
CHANNEL_SECRET = "784eb2c57f781e4f0fed63a065f0d251"

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

# เมื่อได้รับ “ข้อความ”
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text.lower()
    if "สลิป" in msg or "ตรวจ" in msg:
        reply = "📸 กรุณาส่งรูปสลิปเงินโอนเพื่อทำการตรวจสอบ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# เมื่อได้รับ “รูปภาพ”
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # ดาวน์โหลดรูปภาพจาก LINE
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = io.BytesIO(message_content.content)
    img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)

    # 🔍 ตรวจหา QR Code
    decoded_objs = decode(img)
    if not decoded_objs:
        reply = "❌ ไม่พบ QR Code ในสลิป กรุณาลองใหม่อีกครั้ง"
    else:
        data = decoded_objs[0].data.decode('utf-8')
        # ตรวจสอบว่า QR เป็นของ PromptPay / Slip Verification
        if "000201" in data:
            # ✅ ตัวอย่างขั้นตอนตรวจสลิป
            reply = check_slip_detail(data)
        else:
            reply = "⚠️ QR Code ไม่ตรงตามรูปแบบสลิปโอนเงิน"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

def check_slip_detail(qr_data):
    """
    ฟังก์ชันตรวจสอบ QR Code ว่าเป็น slip จริงหรือไม่
    ปกติธนาคารมี endpoint สำหรับตรวจสอบ Slip Verification
    แต่ในตัวอย่างนี้จะจำลองผลลัพธ์
    """
    # ตัวอย่างจำลองผล (คุณสามารถเชื่อมต่อ API ธนาคารได้จริง)
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
