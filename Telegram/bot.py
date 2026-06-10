# ==================================================
# FILE: ./Telegram/bot.py
# ==================================================
import os
import telebot
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from Core.config import TELEGRAM_BOT_TOKEN
from Core.redis_client import redis_client
from Core.mongo import db

# Khởi tạo thực thể bot lõi từ thư viện pyTelegramBotAPI
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)

# Khởi tạo chuỗi định danh duy nhất cho tiến trình khi nổ máy (Singleton Lock ID)
INSTANCE_ID = str(uuid.uuid4())
lock_key = "singleton_bot_instance_lock"

def check_singleton_lock():
    """
    Background Thread chạy song song gia hạn quyền sinh sát độc quyền mỗi 30 giây.
    Nếu phát hiện có instance thứ hai cố tình chạy đè, instance cũ sẽ tự động tự sát.
    """
    print(f"🛡️ [SINGLETON] Trạm chỉ huy khởi động với ID thực thể: {INSTANCE_ID}")
    
    while True:
        try:
            # Thử chiếm quyền sở hữu khóa độc quyền trên Redis (TTL 45 giây)
            acquired = redis_client.set(lock_key, INSTANCE_ID, ex=45, nx=True)
            
            if acquired:
                pass # Đang giữ chốt an toàn
            else:
                current_holder = redis_client.get(lock_key)
                if current_holder == INSTANCE_ID:
                    # Nếu chính ta đang cầm khóa, tiến hành gia hạn thời gian sống (Keep-alive)
                    redis_client.expire(lock_key, 45)
                else:
                    print(f"🚨 [SINGLETON] Phát hiện thực thể Bot mới trùng lặp ({current_holder}) đã chiếm quyền điều khiển! Tiến trình tự hủy...")
                    os._exit(0) # Ngắt khẩn cấp cấp độ hệ điều hành để tránh lặp tin nhắn
                    
        except Exception as e:
            print(f"⚠️ [SINGLETON] Lỗi tuần tra khóa độc quyền Redis: {e}")
            
        time.sleep(30)

def outbox_listener_loop():
    """
    Luồng lắng nghe Outbox độc lập: Phát hiện sự kiện báo cáo từ Worker để ting-ting cho Giám đốc.
    Tuân thủ tuyệt đối Outbox Pattern.
    """
    print("🎧 [TELEGRAM_LISTENER] Đang dỏng tai nghe ngóng sự kiện báo cáo từ các Worker...")
    wait = 2
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Quét tìm các sự kiện gửi về Telegram (Hiện tại là STRATEGY_GENERATED)
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
            
            wait = 2 # Reset độ trễ khi có việc
            payload = event.get("payload", {})
            event_type = event.get("event_type")
            
            if event_type == "STRATEGY_GENERATED":
                project_name = payload.get("project_name", "Không rõ tên")
                text_msg = (
                    f"🔔 *Ting Ting!*\n\n"
                    f"Bản vẽ chiến lược cho dự án `{project_name}` đã được Worker T2 thiết kế xong.\n\n"
                    f"👉 Xin mời Giám đốc vào mục *Duyệt Chiến Lược Đang Chờ* để thẩm định lập tức."
                )
                
                # Bắn tin nhắn cho toàn bộ Admin đang active
                admins = db.system_admins.find({"status": "active"})
                for admin in admins:
                    chat_id = admin.get("telegram_id")
                    if chat_id:
                        try:
                            bot.send_message(chat_id, text_msg, parse_mode="Markdown")
                        except Exception as e:
                            print(f"⚠️ [TELEGRAM_LISTENER] Không thể gửi thông báo cho Admin {chat_id}: {e}")

            # Commit hoàn thành tác vụ vòng lặp
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
