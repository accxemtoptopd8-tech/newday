# ==================================================
# FILE: ./Telegram/bot.py
# ==================================================
import os
import telebot
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from flask import Flask # THÊM THƯ VIỆN NÀY ĐỂ TẠO WEBVIEW
from Core.config import TELEGRAM_BOT_TOKEN
from Core.redis_client import redis_client
from Core.mongo import db

# Khởi tạo thực thể bot lõi từ thư viện pyTelegramBotAPI
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)

# Khởi tạo chuỗi định danh duy nhất cho tiến trình khi nổ máy (Singleton Lock ID)
INSTANCE_ID = str(uuid.uuid4())
lock_key = "singleton_bot_instance_lock"

# ==========================================
# TRẠM GÁC WEB CHỐNG SẬP RENDER (DUMMY SERVER)
# ==========================================
app = Flask(__name__)

@app.route('/')
def health_check():
    """Đường dẫn để Render ping kiểm tra sức khỏe hệ thống"""
    return f"🟢 Trạm T0 (ID: {INSTANCE_ID}) đang hoạt động ổn định!", 200

def run_dummy_web_server():
    """Khởi chạy máy chủ Web giả trên một luồng riêng biệt"""
    # Render sẽ tự động gán biến môi trường PORT, mặc định fallback về 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 [WEBVIEW] Đang mở cổng mạng {port} để qua mặt Render Health Check...")
    # Tắt log của Flask để tránh rác console
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port)

# ==========================================
# CÁC LUỒNG XỬ LÝ LÕI CỦA HỆ THỐNG
# ==========================================
def check_singleton_lock():
    """Bảo vệ chống trùng lặp tiến trình (Singleton Lock)"""
    print(f"🛡️ [SINGLETON] Trạm chỉ huy khởi động với ID thực thể: {INSTANCE_ID}")
    while True:
        try:
            acquired = redis_client.set(lock_key, INSTANCE_ID, ex=45, nx=True)
            if acquired:
                pass
            else:
                current_holder = redis_client.get(lock_key)
                if current_holder == INSTANCE_ID:
                    redis_client.expire(lock_key, 45)
                else:
                    print(f"🚨 [SINGLETON] Phát hiện Bot trùng lặp ({current_holder})! Tự hủy...")
                    os._exit(0)
        except Exception as e:
            print(f"⚠️ [SINGLETON] Lỗi Redis: {e}")
        time.sleep(30)

def outbox_listener_loop():
    """Luồng dỏng tai nghe Outbox chờ tin nhắn báo cáo từ Worker"""
    print("🎧 [TELEGRAM_LISTENER] Đang dỏng tai nghe ngóng sự kiện báo cáo...")
    wait = 2
    while True:
        try:
            now = datetime.now(timezone.utc)
            event = db.outbox_events.find_one_and_update(
                {
                    "status": "pending",
                    "event_type": {"$in": ["STRATEGY_GENERATED"]}, 
                    "next_retry_at": {"$lte": now}
                },
                {"$set": {
                    "status": "processing",
                    "claimed_by": f"telegram_bot_{INSTANCE_ID}",
                    "claimed_at": now,
                    "claim_timeout": now + timedelta(minutes=2)
                }},
                sort=[("created_at", 1)]
            )

            if not event:
                time.sleep(wait)
                wait = min(10, wait * 2)
                continue
            
            wait = 2 
            payload = event.get("payload", {})
            
            if event.get("event_type") == "STRATEGY_GENERATED":
                project_name = payload.get("project_name", "Không rõ tên")
                text_msg = (
                    f"🔔 *Ting Ting!*\n\n"
                    f"Bản vẽ chiến lược cho dự án `{project_name}` đã hoàn tất.\n"
                    f"👉 Xin mời Giám đốc vào mục *Duyệt Chiến Lược Đang Chờ*."
                )
                
                admins = db.system_admins.find({"status": "active"})
                for admin in admins:
                    chat_id = admin.get("telegram_id")
                    if chat_id:
                        try:
                            bot.send_message(chat_id, text_msg, parse_mode="Markdown")
                        except Exception:
                            pass

            db.outbox_events.update_one(
                {"_id": event["_id"]},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
            )
        except Exception:
            time.sleep(5)

def run_singleton_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ [TELEGRAM] TELEGRAM_BOT_TOKEN trống rỗng!")
        return
        
    # 1. Kích hoạt Trạm gác Web (Chống sập Render)
    web_thread = threading.Thread(target=run_dummy_web_server, daemon=True)
    web_thread.start()

    # 2. Kích hoạt Bảo vệ độc quyền
    monitor_thread = threading.Thread(target=check_singleton_lock, daemon=True)
    monitor_thread.start()
    
    # 3. Kích hoạt Luồng lắng nghe Outbox
    listener_thread = threading.Thread(target=outbox_listener_loop, daemon=True)
    listener_thread.start()
    
    print("🚀 [TELEGRAM] Hệ thống lõi đang kéo data (Infinity Polling)...")
    bot.infinity_polling(timeout=20, long_polling_timeout=25)

if __name__ == "__main__":
    run_singleton_bot()
            db.outbox_events.update_one(
                {"_id": event["_id"]},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc)}}
            )

        except Exception as e:
            print(f"🚨 [TELEGRAM_LISTENER] Lỗi vòng lặp quét Outbox: {e}")
            time.sleep(5)


def run_singleton_bot():
    """Kích hoạt trạm chỉ huy an toàn tuyệt đối"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ [TELEGRAM] TELEGRAM_BOT_TOKEN trống rỗng! Không thể nổ máy T0.")
        return
        
    # Khởi chạy Thread giám sát trùng lặp tiến trình
    monitor_thread = threading.Thread(target=check_singleton_lock, daemon=True)
    monitor_thread.start()
    
    # Khởi chạy Thread lắng nghe Outbox
    listener_thread = threading.Thread(target=outbox_listener_loop, daemon=True)
    listener_thread.start()
    
    print("🚀 [TELEGRAM] Bot Telegram đang bắt đầu cơ chế infinity_polling chủ động kéo data...")
    # Sử dụng infinity_polling theo Kế hoạch v10.1: Không mở port, tự phục hồi khi rớt mạng mạng nhà
    bot.infinity_polling(timeout=20, long_polling_timeout=25)

if __name__ == "__main__":
    run_singleton_bot()
