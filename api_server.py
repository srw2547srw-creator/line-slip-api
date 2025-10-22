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
    try:
        # ดาวน์โหลดรูปจาก LINE
        message_content = line_bot_api.get_message_content(event.message.id)
        image_data = io.BytesIO(message_content.content)

        # แปลงเป็น array สำหรับ OpenCV
        img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)

        # แปลงเป็นขาวดำและเพิ่มความคมชัด เพื่อให้ตรวจ QR ได้ดีขึ้น
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # 🔍 ตรวจหา QR Code ด้วย OpenCV
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(gray)

        # ตรวจสอบผลลัพธ์
        if not data:
            reply = "❌ ไม่พบ QR Code ในสลิป กรุณาลองใหม่อีกครั้ง"
        else:
            print("📄 QR Raw Data:", data[:200])  # แสดงข้อมูลดิบบางส่วนใน log

            # เงื่อนไขตรวจจับลักษณะ QR ที่ใช้ใน Slip จริง
            slip_patterns = [
                "000201",               # PromptPay base
                "A000000677010112",     # Thai QR Payment
                "billpayment",          # ใช้ใน slip บางธนาคาร
                "promptpay",            # keyword ทั่วไป
                "qrpayment",            # keyword ทั่วไป
                "SCB", "BBL", "KTB", "BAY"  # ธนาคารหลัก
            ]

            if any(keyword.lower() in data.lower() for keyword in slip_patterns):
                reply = check_slip_detail(data)
            else:
                reply = f"⚠️ พบ QR แต่ไม่ใช่สลิปโอนเงิน\n(ตัวอย่างข้อมูล):\n{data[:150]}..."

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"เกิดข้อผิดพลาด: {str(e)}"))


def check_slip_detail(qr_data):
    """
    ฟังก์ชันตรวจสอบข้อมูล QR (จำลอง)
    สามารถเชื่อม API ธนาคารจริงได้ในอนาคต
    """
    # 🔎 ตรวจสอบเบื้องต้นจากรูปแบบข้อมูล
    if "promptpay" in qr_data.lower() or "a000000677010112" in qr_data.lower():
        result = {
            "status": "valid",
            "bank": "SCB",
            "amount": "500.00",
            "date": "21/10/2025 10:12"
        }
        return (
            f"✅ ตรวจสอบแล้ว: สลิปถูกต้อง\n"
            f"ธนาคาร: {result['bank']}\n"
            f"จำนวนเงิน: {result['amount']} บาท\n"
            f"วันที่โอน: {result['date']}"
        )
    else:
        return "⚠️ ตรวจพบ QR แต่ไม่สามารถยืนยันว่าเป็นสลิปการโอนได้"



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
