
# 🧠 AI Business OS - Hệ Điều Hành Tự Động Hóa Doanh Nghiệp (v11.0)

## 🌟 1. TRIẾT LÝ THIẾT KẾ CỐT LÕI (CORE PHILOSOPHY)
Hệ thống được xây dựng để vận hành hoàn hảo trong môi trường độc lập, tối ưu hóa tuyệt đối về mặt chi phí nhưng đạt hiệu suất kiến trúc ở cấp độ công nghiệp. Mọi module xoay quanh 3 trục tư duy chiến lược:

* **"Con rùa hiện đại" (Batch-Driven Resiliency):** Chấp nhận độ trễ (hệ thống được đánh thức qua GitHub Actions Cronjob 5 phút/lần) để đổi lấy sự bền bỉ, tính sẵn sàng cao, hoàn toàn miễn phí và không bao giờ lo chết tiến trình nền.
* **"Vơ bèo vặt tép" (Dynamic API Key Optimization):** Tối ưu hóa 100% chi phí vận hành AI. Hệ thống sử dụng một "Trạm Kiểm Định" (`verify_and_save.py`) có khả năng tự động nạp bất kỳ nguồn API Key nào (OpenAI, Gemini, OpenRouter, Custom API Base), dội bom quét qua danh sách model để tìm mạch sống, tự động cấu hình `.env` và ép MongoDB định tuyến luồng xử lý mà không cần can thiệp thủ công vào mã nguồn.
* **"Kiến trúc bất tử" (Decoupled Outbox Pattern):** Tách rời hoàn toàn cổng tiếp nhận và bộ não xử lý thông qua cơ sở dữ liệu MongoDB. Cổng giao tiếp không gọi trực tiếp LLM mà chỉ phát sự kiện vào kho lưu trữ. Nếu bộ não AI sập hoặc hết quota, sự kiện vẫn nằm chờ an toàn trong Outbox, không bao giờ rơi rớt dữ liệu.

---

## 🗺️ 2. BẢN ĐỒ KIẾN TRÚC LUỒNG DỮ LIỆU (EVENT-DRIVEN FLOW)

Hệ thống phân tách rạch ròi thành 3 tầng tác chiến (T0, T1, T2):


```
[ Người dùng ]
│  (Ngôn ngữ tự nhiên)
▼
┌────────────────────────────────────────────────────────┐
│ TẤT CẢ MODULES ĐỀU GIAO TIẾP QUA TRÁI TIM MONGODB      │
│                                                        │
│  1. T0 (Telegram Gateway): Tiếp nhận -> Ghi Outbox     │
│  2. Outbox Events: Lưu trữ trạng thái sự kiện chờ     │
│  3. T2 (AI Strategy Worker): Bốc việc -> Xử lý -> JSON │
└────────────────────────────────────────────────────────┘
│
▼
[ Màn hình Telegram ] (Ting-ting nhận báo cáo chiến lược)
```

1.  **TẦNG CHỈ HUY - T0 (Telegram Gateway):** Nơi Giám đốc ra lệnh trực tiếp bằng điện thoại. Bot tiếp nhận ý tưởng dự án, lập tức đóng gói nhiên liệu thô và bắn một Đại sự kiện `PHASE_1_COMPLETED` vào bảng `outbox_events` trong MongoDB.
2.  **TRÁI TIM HỆ THỐNG - MONGODB & REDIS:** Kho lưu trữ trung tâm, giữ vai trò kết nối trung gian và quản lý hạn mức ngân sách, chống spam quota của API.
3.  **TẦNG THỰC THI - T2 (AI Strategy Worker):** Được kích hoạt tự động mỗi 5 phút bởi GitHub Actions. Worker thức dậy, rút sự kiện từ Outbox, gọi LLM, kích hoạt bộ tự vá cấu trúc JSON, xuất bản đồ chiến lược hoàn chỉnh ghi vào kho dữ liệu, và phát sự kiện báo cáo thành công.

---

## 🚦 3. TRẠNG THÁI HIỆN TẠI CỦA REPO (CURRENT REPO STATE)
* `Core/config.py`: Quản lý cấu hình biến môi trường hệ thống.
* `Workers/strategy_generator.py`: Bộ não xử lý Giai đoạn 1 (T2 Worker). Đã được nâng cấp tích hợp công tắc thông minh `RUN_ONCE` để tự động ngắt máy khi dọn sạch kho sự kiện, bảo vệ tuyệt đối số phút chạy miễn phí (Quota) của GitHub.
* `verify_and_save.py`: Trạm Lọc Máu API Key, tự động quét sinh tử model và cấu hình hệ thống.
* `trigger_e2e.py`: File mồi sự kiện cục bộ để phục vụ kiểm toán đường ống dữ liệu.
* `harvest.py`: Công cụ một chạm để lục tìm và xuất cục dữ liệu JSON Chiến lược cực phẩm từ cơ sở dữ liệu.

---

## 🚀 4. KẾ HOẠCH HÀNH ĐỘNG CHIẾN LƯỢC (ROADMAP)

### GIAI ĐOẠN 1: Khai Thông Kinh Mạch (Thông luồng chính thức)
* **Mục tiêu:** Nối liền trục **Telegram Bot <-> MongoDB <-> GitHub Actions <-> Telegram Bot**.
* **Hành động:** Nâng cấp `telegram_bot.py` thành một Event Gateway thực thụ. Thêm luồng lắng nghe (Listener) để khi Worker T2 hoàn thành bản vẽ chiến lược và lưu vào MongoDB, Bot sẽ tự động nhặt kết quả và "ting ting" gửi trả thẳng về tin nhắn Telegram của Giám đốc.

### GIAI ĐOẠN 2: Bơm Máu Tối Thượng (Tích hợp Hệ thống DS2API)
* **Mục tiêu:** Đấu nối thành công Repo `CJackHwang/ds2api` để biến giao diện Web Chat miễn phí của DeepSeek thành cổng API xịn có cấu trúc chuẩn OpenAI.
* **Hành động:** 1. Triển khai trạm trung gian DS2API để lấy cổng Endpoint tùy chỉnh.
    2. Cấu hình biến môi trường `CUSTOM_API_BASE` vào hệ thống.
    3. Nâng cấp Trạm Kiểm Định để LiteLLM tự động chuyển hướng đi qua cổng Custom Base này, vắt kiệt tư duy logic của DeepSeek V3/R1 với chi phí bằng 0.

---

## 📜 5. LUẬT CHƠI & KỶ LUẬT LÕI DÀNH CHO LLM BẢO TRÌ
Bất kỳ mô hình ngôn ngữ nào khi tiếp nhận Repo này để phát triển mã nguồn, **BẮT BUỘC** phải tuân thủ nghiêm ngặt các nguyên tắc kiến trúc sau:
1.  **Tuyệt đối không phá vỡ Outbox Pattern:** Các module không được phép gọi trực tiếp lẫn nhau. Mọi hành vi luân chuyển dữ liệu và trạng thái phải thông qua việc tạo và thay đổi trạng thái sự kiện trong Collection `outbox_events` của MongoDB.
2.  **Giữ vững công tắc tiết kiệm Quota:** Mọi mã nguồn viết cho Worker chạy trên GitHub Actions phải kế thừa và tôn trọng biến môi trường `RUN_ONCE`. Nếu kho việc trống, tiến trình phải tự ngắt (`break` hoặc `exit`), nghiêm cấm chạy vòng lặp vô hạn `while True` gây treo luồng Actions.
3.  **Tương thích Custom Base URL:** Khi cấu hình gọi LLM thông qua LiteLLM, luôn phải truyền tham số `api_base=CUSTOM_API_BASE` (nếu có) để sẵn sàng mở đường cho các cổng trung gian như DS2API hoặc OpenRouter hoạt động mượt mà.

```

