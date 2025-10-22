from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
import requests, cv2, numpy as np, io

app = Flask(__name__)

# 🧩 LINE credentials
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


# 🗨️ เมื่อผู้ใช้พิมพ์ข้อความ
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text.lower()
    if "สลิป" in msg or "ตรวจ" in msg:
        reply = "📸 กรุณาส่งรูปสลิปเงินโอนเพื่อทำการตรวจสอบ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


# 🖼️ เมื่อผู้ใช้ส่ง “รูปภาพ”
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # ดาวน์โหลดรูปจาก LINE
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = io.BytesIO(message_content.content)

    # แปลงเป็น array สำหรับ OpenCV
    img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)

    # 🔍 ตรวจหา QR Code ด้วย OpenCV
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)

    if not data:
        reply = "❌ ไม่พบ QR Code ในสลิป กรุณาลองใหม่อีกครั้ง"
    else:
        # ตรวจสอบข้อมูลใน QR
        if "000201" in data:  # ลักษณะเฉพาะของ PromptPay QR
            reply = check_slip_detail(data)
        else:
            reply = f"⚠️ พบ QR แต่ไม่ใช่สลิปโอนเงิน:\n{data[:60]}..."

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def check_slip_detail(qr_data):
    """
    ฟังก์ชันตรวจสอบข้อมูล QR (จำลอง)
    ในระบบจริงสามารถเชื่อมต่อ API ธนาคารสำหรับตรวจสอบ slip verification ได้
    """
    result = {
        "status": "valid",
        "bank": "SCB",
        "amount": "500.00",
        "date": "21/10/2025 10:12"
    }

    if result["status"] == "valid":
        return (
            f"✅ สลิปถูกต้อง\n"
            f"ธนาคาร: {result['bank']}\n"
            f"จำนวนเงิน: {result['amount']} บาท\n"
            f"วันที่โอน: {result['date']}"
        )
    else:
        return "❌ สลิปปลอม หรือไม่สามารถตรวจสอบได้"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
