import os
import random
import threading
import time
import requests
from flask import Flask, render_template_string, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop_auto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

BANK_ID = "abbank"         
BANK_ACCOUNT = "0935507211"  
BANK_NAME = "LE TAN MINH PHU"  
TELEGRAM_BOT_TOKEN = "9276996931:AAEDu-6XrUyaKbYJlxVwG9lj8qg4Bp1Skrc"
TELEGRAM_CHAT_ID = "6329210433"

class ProductKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    key_value = db.Column(db.String(255), unique=True, nullable=False)
    is_sold = db.Column(db.Boolean, default=False)

class Order(db.Model):
    order_code = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="PENDING") 
    delivered_key = db.Column(db.String(255), nullable=True)

def init_db():
    with app.app_context():
        db.create_all()
        if not ProductKey.query.first():
            db.session.add(ProductKey(product_name="Netflix 3 DAY", key_value="KEY 3 NGÀY"))
            db.session.add(ProductKey(product_name="Netflix 1 DAY", key_value="KEY 1 NGÀY"))
            db.session.commit()

def send_telegram(message):
    try:
        url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

def telegram_auto_updater():
    last_update_id = 0
    try:
        url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/getUpdates"
        res = requests.get(url, timeout=5).json()
        if res.get("result"): last_update_id = res["result"][-1]["update_id"]
    except: pass

    while True:
        try:
            time.sleep(2)
            url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url, timeout=5).json()
            if not response.get("result"): continue
                
            for update in response["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    text_msg = update["message"]["text"]
                    
                    with app.app_context():
                        pending_orders = Order.query.filter_by(status="PENDING").all()
                        for order in pending_orders:
                            search_term = f"DH{order.order_code}"
                            if search_term in text_msg:
                                key_item = ProductKey.query.filter_by(product_name=order.product_name, is_sold=False).first()
                                if key_item:
                                    key_item.is_sold = True
                                    order.status = "PAID"
                                    order.delivered_key = key_item.key_value
                                    db.session.commit()
                                    send_telegram(f"🤖 *AUTO DUYỆT THÀNH CÔNG!*\n📌 Đơn: `{search_term}`\n🔑 Đã cấp key: `{key_item.key_value}`")
                                    break
        except: pass

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8"><title>Hệ Thống Bán Key Tự Động 100%</title>
<link rel="stylesheet" href="https://jsdelivr.net"></head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark mb-4"><div class="container"><a class="navbar-brand fw-bold" href="/">🚀 ROBOT AUTO KEY SHOP</a></div></nav>
    <div class="container">{{ content | safe }}</div>
</body></html>
"""

@app.route('/')
def index():
    content = """
    <h2 class="text-center my-4 fw-bold">Mua Hàng Tự Động Xử Lý Sau 3 Giây</h2>
    <div class="row text-center">
        <div class="col-md-6 mb-4"><div class="card p-4 shadow-sm">
            <h4>Netflix Premium 1 Tháng</h4><h3 class="text-danger my-3">20,000đ</h3>
            <form action="/buy" method="POST">
                <input type="hidden" name="product_name" value="Netflix 1 Month"><input type="hidden" name="price" value="20000">
                <button type="submit" class="btn btn-primary w-100">Mua Bằng VietQR (Tự Động)</button>
            </form>
        </div></div>
        <div class="col-md-6 mb-4"><div class="card p-4 shadow-sm">
            <h4>Spotify Premium 1 Năm</h4><h3 class="text-danger my-3">50,000đ</h3>
            <form action="/buy" method="POST">
                <input type="hidden" name="product_name" value="Spotify 1 Year"><input type="hidden" name="price" value="50000">
                <button type="submit" class="btn btn-primary w-100">Mua Bằng VietQR (Tự Động)</button>
            </form>
        </div></div>
    </div>"""
    return render_template_string(HTML_LAYOUT, content=content)

@app.route('/buy', methods=['POST'])
def buy():
    product_name = request.form.get('product_name')
    price = int(request.form.get('price'))
    order_code = random.randint(100000, 999999)
    
    new_order = Order(order_code=order_code, product_name=product_name, amount=price, status="PENDING")
    db.session.add(new_order)
    db.session.commit()
    
    qr_url = f"https://vietqr.io{BANK_ID}-{BANK_ACCOUNT}-compact2.png?amount={price}&addInfo=DH{order_code}&accountName={BANK_NAME}"
    content = f"""
    <div class="card shadow mx-auto p-4 text-center" style="max-width: 500px;">
        <h4 class="fw-bold text-success">Vui Lòng Chuyển Khoản Đặt Hàng</h4>
        <img src="{qr_url}" class="img-fluid my-3 mx-auto" style="max-width: 280px;">
        <div class="alert alert-danger text-start">
            <b>Nội dung CK bắt buộc điền:</b> <span class="badge bg-danger fs-5">DH{order_code}</span>
        </div>
        <p class="text-muted">Sau khi chuyển khoản thành công, hệ thống tự nhận diện tiền sau vài giây và hiển thị key.</p>
        <a href="/check-order?order_code={order_code}" class="btn btn-success btn-lg w-100">Kiểm Tra Trạng Thái Nhận Key</a>
    </div>"""
    return render_template_string(HTML_LAYOUT, content=content)

@app.route('/check-order')
def check_order():
    order_code = request.args.get('order_code')
    order = Order.query.filter_by(order_code=order_code).first()
    
    if order and order.status == "PAID":
        content = f"""<div class="alert alert-success text-center mt-5">
            <h3>🎉 Hệ thống đã nhận được tiền thành công!</h3><p>Đây là key của bạn:</p>
            <div class="bg-white p-3 border fs-4 fw-bold text-danger my-3">{order.delivered_key}</div>
            <a href="/" class="btn btn-secondary btn-sm">Quay lại trang chủ</a>
        </div>"""
    else:
        content = f"""<div class="text-center mt-5">
            <div class="spinner-border text-success mb-3"></div>
            <h4>Đang chờ Robot quét thông báo chuyển khoản của bạn...</h4>
            <p class="text-muted">Đơn hàng: <b>DH{order_code}</b>. Hệ thống tự động làm việc khi tài khoản nhận được tiền.</p>
            <a href="/check-order?order_code={order_code}" class="btn btn-primary mt-2">Bấm tải lại trang để kiểm tra</a>
        </div>"""
    return render_template_string(HTML_LAYOUT, content=content)

if __name__ == '__main__':
    init_db()
    updater_thread = threading.Thread(target=telegram_auto_updater, daemon=True)
    updater_thread.start()
    app.run(debug=False, port=5000)
