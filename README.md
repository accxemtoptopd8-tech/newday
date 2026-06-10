Dưới đây là file README.md được thiết kế theo tư duy kiến trúc hệ thống hiện đại, tối ưu hóa cho mô hình **"0 đồng - 0 thẻ - Tự chủ"**. Bạn có thể sử dụng nội dung này cho mọi repository trong hệ sinh thái của mình.
# T2-CORE: Hệ thống Tự động hóa Dữ liệu "Zero-Cost & Self-Sustaining"
## 1. Triết lý hệ thống
 * **0 Đồng (Zero-Cost):** Loại bỏ hoàn toàn chi phí API, Subscription, và Hosting trả phí. Tận dụng tài nguyên miễn phí từ GitHub Actions, Oracle/Google Cloud Free Tier và sức mạnh tính toán tự thân.
 * **0 Thẻ (Zero-Card):** Không phụ thuộc vào các dịch vụ cần gắn thẻ tín dụng (Stripe/Paypal). Hệ thống sử dụng cơ chế xoay vòng tài khoản (account rotation) tự quản lý, loại bỏ rủi ro bị khóa tài khoản hoặc mất phí ẩn.
 * **Tính tự chủ (Self-Sustaining):** Hệ thống vận hành theo mô hình "Bus CPU" với các luồng xử lý độc lập (Quad-core), nơi dữ liệu tự vận động từ nguồn thô đến kho tri thức mà không cần sự can thiệp thủ công.
## 2. Sơ đồ khối kiến trúc (Architecture Flow)
```mermaid
graph TD
    %% Nguồn Dữ liệu (Bus)
    Input[("Nguồn Web (Finance/RealEstate/Crypto)")] --> Scrapling("Scrapling (Bus CPU)")
    
    %% Tầng xử lý - 4 Core (GitHub Actions)
    subgraph "Quad-Core Processing (GitHub Actions)"
        C1["Core 1: Crypto Logic"]
        C2["Core 2: Real Estate Data"]
        C3["Core 3: Finance/Exchange"]
        C4["Core 4: Tech/Utility"]
    end
    
    Scrapling --> C1 & C2 & C3 & C4
    
    %% Tầng Lưu trữ tạm & AI
    C1 & C2 & C3 & C4 --> GitHubRepo[("GitHub Repo (Kho Tạm)")]
    GitHubRepo --> Agent("AI Agent (ds2api - Local/Cloud)")
    
    %% Tầng Lưu trữ cuối
    Agent --> MongoDB[("MongoDB (Kho Tầng 2)")]
    
    %% Cơ chế quản lý
    style Scrapling fill:#f96,stroke:#333
    style GitHubRepo fill:#bbf,stroke:#333
    style MongoDB fill:#dfd,stroke:#333

```
## 3. Thành phần cốt lõi
### A. Bus CPU - Scrapling
 * **Vai trò:** Đóng vai trò là "Bus dữ liệu" hiệu năng cao, trích xuất dữ liệu thô (raw data) với cơ chế vượt qua bot detection mà không tốn phí proxy trả phí.
 * **Cơ chế:** Hoạt động như một trình xử lý trung gian, đẩy dữ liệu vào luồng Action tương ứng.
### B. Quad-Core (4 GitHub Actions)
Hệ thống được chia thành 4 luồng xử lý độc lập, chạy trên GitHub Actions (miễn phí):
 * **Core 1 (Crypto):** Phân tích biến động giá, whale activity, MFI/RSI tracking.
 * **Core 2 (Real Estate):** Thu thập giá bất động sản, đối soát dữ liệu môi giới.
 * **Core 3 (Exchange):** Giám sát tài khoản sàn, quản trị rủi ro (Margin calls, vị thế).
 * **Core 4 (Utility):** Phát triển công cụ, hỗ trợ AI Agents, xử lý tài liệu nội bộ.
### C. AI Agent & API (ds2api)
 * **Vai trò:** Chuyển đổi cookie tài khoản (DeepSeek/khác) thành chuẩn OpenAI API.
 * **Triết lý:** Sử dụng **Multi-account rotation** để không bao giờ bị rate-limit, đảm bảo "cơn khát token" luôn được giải quyết miễn phí.
### D. Kho lưu trữ (Storage Layer)
 * **GitHub (Kho tạm):** Lưu trữ dữ liệu thô, dùng làm "hệ thống file đệm" để đảm bảo tính an toàn dữ liệu trước khi AI xử lý.
 * **MongoDB (Kho tầng 2):** Lưu trữ kết quả đã phân tích, sẵn sàng cho việc truy vấn và đưa ra quyết định đầu tư/vận hành.
## 4. Nguyên tắc vận hành (Operating Principles)
 1. **Luôn giữ Offline-First:** Các thành phần lõi (emulator, data reader) phải tách rời khỏi nguồn dữ liệu để tránh bản quyền và rủi ro mất mát.
 2. **Tự động hóa hoàn toàn:** Mọi thao tác push/pull dữ liệu, chạy script phân tích, và log vào database đều phải thông qua CI/CD của GitHub.
 3. **Không phụ thuộc (Decoupling):** Nếu một Core bị lỗi, 3 Core còn lại vẫn vận hành bình thường. Nếu dịch vụ web mục tiêu thay đổi cấu trúc, chỉ cần chỉnh sửa Scrapling ở "Bus", không cần thay đổi tầng logic của AI Agent.
 4. **Tối ưu tài nguyên:** Sử dụng SQLite cho các tác vụ cần lưu trữ trạng thái nội bộ nếu cần thiết thay cho các dịch vụ DB đắt đỏ.
## 5. Cấu hình & triển khai
 * **Environment:** Dockerized (mọi dịch vụ chạy trên Docker để đảm bảo tính nhất quán giữa Local và Server).
 * **Auth:** Sử dụng biến môi trường (Environment Variables) để quản lý cookies/tokens. **Tuyệt đối không push file cấu hình lên public repository.**
 * **Monitoring:** Theo dõi logs thông qua chính GitHub Actions Run History.
*Hệ thống được thiết kế bởi Keith Howe (Nguyễn Tiến Hiển) - Tối ưu hóa vì sự bền vững và hiệu suất không giới hạn.*
================================================================================
## 📌 KẾ HOẠCH TRIỂN KHAI CHI TIẾT (Ghi nhận sau thảo luận ngày 10/06/2026)
================================================================================

### 1. Giữ Render thức 24/7
- **Giải pháp**: Dùng cron-job.org (miễn phí, không thẻ) tạo cron job mỗi 30 giây ping đến `https://your-app.onrender.com/health`.
- **Code**: Trong `Telegram/bot.py` đã có Flask app, chỉ cần thêm route `/health` (trả về "OK").
- **Không cần** GitHub Actions cho việc này.

### 2. Thay Playwright bằng Scrapling
- **Lý do**: Playwright quá nặng (cần browser ~300MB, dễ bị kill trên GitHub Actions). Scrapling nhẹ, nhanh, vẫn vượt bot tốt với `StealthyFetcher`.
- **So sánh kỹ thuật** (đã ghi nhận): Playwright dùng browser thật, Scrapling dùng HTTP + TLS fingerprint.
- **Hành động**:
  - Xóa `playwright` khỏi `requirements.txt`.
  - Viết lại `Workers/social_validator.py` dùng `scrapling` (import `from scrapling import StealthyFetcher`).
  - Bỏ `asyncio`, dùng đồng bộ.

### 3. Xóa ChromaDB
- Xóa file `Core/mem0_client.py`, bỏ `chromadb` khỏi `requirements.txt`.

### 4. Cơ chế xoay vòng 4 tài khoản MongoDB Atlas & Upstash
- **Mục tiêu**: Dùng chung 4 bộ DB + 4 Redis, tăng băng thông và tránh thắt cổ chai.
- **Cách thực hiện**:
  - Tạo `Core/account_rotator.py` quản lý danh sách URI.
  - Biến môi trường: `MONGODB_URIS='["uri1","uri2","uri3","uri4"]'` và `REDIS_URLS='["redis://...","redis://..."]'`.
  - Round‑robin: lưu index hiện tại vào Redis key `round_robin_mongo_index` hoặc collection MongoDB `round_robin_state`.
  - Khi kết nối thất bại, chuyển sang URI tiếp theo.
- **Áp dụng**: Sửa `Core/mongo.py` và `Core/redis_client.py` để gọi `get_next_uri()`.

### 5. Chỉ 1 repo duy nhất, không bắt buộc 4 workflow
- **Nguyên tắc**: Chỉ chia việc khi thực sự cần tránh xung đột. Nếu 1 luồng đủ tải, không cần chia.
- **Nếu phải chia**: Trong cùng repo, tạo nhiều workflow `.yml` với cron schedule lệch pha (ví dụ 0, 15, 30, 45 phút) để tránh trùng. Mỗi workflow set biến môi trường `CORE_ID=1..4` để phân biệt.
- **Giải pháp đơn giản nhất**: Chỉ cần 1 workflow xử lý tuần tự, dùng `account_rotator` để ghi vào 4 DB luân phiên.

### 6. Worker mới: `data_ingestor`
- **Nhiệm vụ**: Lắng nghe event `RAW_DATA_SCRAPED`, lưu vào MongoDB (collection `scraped_data`) và commit lên GitHub repo (dùng PyGithub).
- **Cấu hình**: Cần secret `GITHUB_REPO_TOKEN`, `GITHUB_REPO_NAME`.
- **Worker này chạy dưới dạng cron** (mỗi 2 phút) hoặc dùng outbox consumer như các worker khác.

### 7. Worker mới: `scrapling_crawler_base`
- **Nội dung**: Class `BaseCrawler` dùng `StealthyFetcher`, hỗ trợ crawl URL, parse HTML, publish event `RAW_DATA_SCRAPED`.
- **Dùng để xây dựng các crawler chuyên biệt (Crypto, Real Estate, ...)** nếu cần.

### 8. Workflow `health_check`
- **Cron**: mỗi 15 phút.
- **Nhiệm vụ**: Query MongoDB `worker_heartbeat` collection (hoặc Redis key `worker_heartbeat:*`). Nếu heartbeat cũ hơn 20 phút, ghi `sos_queue` và gửi Telegram cảnh báo.
- **Đặt trong `.github/workflows/health_check.yml`**.

### 9. Retry thông minh qua `next_retry_at`
- **Hiện tại**: `outbox_events` đã có trường `next_retry_at`, nhưng chưa dùng.
- **Cải tiến**: Khi worker thất bại với lỗi tạm thời (429, timeout, network error), tính `next_retry_at = now + exponential_backoff(retry_count)` và set `status='pending'`. Cron `outbox_sweeper` sẽ nhặt lại.

### 10. Các tệp cần tạo hoặc sửa (tóm tắt)
- **Tạo mới**:
  - `Core/account_rotator.py`
  - `Workers/data_ingestor.py`
  - `Workers/scrapling_crawler_base.py`
  - `.github/workflows/health_check.yml`
- **Sửa**:
  - `Telegram/bot.py` (thêm route `/health`, xóa listener thread)
  - `Workers/social_validator.py` (dùng Scrapling)
  - `Core/mongo.py`, `Core/redis_client.py` (tích hợp xoay vòng)
  - `requirements.txt` (thêm `scrapling`, `PyGithub`; bỏ `playwright`, `chromadb`)
  - `bootstrap.py` (tạo collection `round_robin_state`, `worker_heartbeat` nếu cần)

================================================================================
## 🗓️ Lộ trình thực hiện dự kiến
================================================================================
1. **Ngày 1**: Sửa `social_validator.py`, xóa `mem0_client.py`, cập nhật `requirements.txt`.
2. **Ngày 2**: Tạo `account_rotator.py`, sửa `mongo.py` và `redis_client.py`, kiểm thử kết nối round‑robin.
3. **Ngày 3**: Tạo `data_ingestor.py` và `scrapling_crawler_base.py`, tích hợp PyGithub.
4. **Ngày 4**: Thêm route `/health` vào `bot.py`, cấu hình cron-job.org, xóa listener thread.
5. **Ngày 5**: Tạo workflow `health_check.yml`, kiểm thử retry thông minh.
6. **Ngày 6**: Chạy kiểm thử tổng thể, tinh chỉnh cron schedule nếu cần.

Mọi thay đổi đều **không làm vỡ luồng Outbox** và tuân thủ kỷ luật hệ thống.
