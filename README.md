# 🧠 AI Business OS - Hệ Điều Hành Tự Động Hóa Doanh Nghiệp (v11.0)

## 1. Triết lý thiết kế (Core Philosophy)
Hệ thống được thiết kế tối ưu hóa cho môi trường phát triển độc lập và đa nhiệm. Tự động hóa giám sát thị trường, quản lý chiến lược và vận hành đa luồng.
* **"Con rùa hiện đại":** Chấp nhận độ trễ (chạy qua GitHub Actions Cronjob 5 phút/lần) để đổi lấy sự bền bỉ, miễn phí và không bao giờ chết luồng.
* **"Vơ bèo vặt tép":** Tối ưu 100% chi phí API bằng Trạm Kiểm Định động, vắt kiệt tài nguyên miễn phí từ OpenRouter, DeepSeek (via DS2API) và Gemini.
* **Decoupled & Bất tử:** Thiết kế tách rời hoàn toàn bằng **Outbox Pattern**. Telegram (T0) chỉ ghi sự kiện. Worker (T2) chỉ đọc và xử lý.

## 2. Kiến trúc Hệ Sinh Thái
* **T0 (Cổng giao tiếp):** Trạm Telegram Gateway.
* **T1 (Bộ lọc - Lên lịch):** Tiền xử lý dữ liệu thô.
* **T2 (Chiến lược gia):** Worker nòng cốt (MongoDB -> LiteLLM -> JSON).
* **Trái tim & Trí nhớ:** MongoDB (Chứa Outbox, Products, Reports) & Redis (Bộ nhớ ngắn hạn).
