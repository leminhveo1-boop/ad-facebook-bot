# Toàn Tập: Hệ Thống Tự Động Hóa Facebook Ads (Quần Jean Nữ)

*Ngày cập nhật: 14/05/2026*
*Mục đích: Lưu trữ toàn bộ quy trình, nguyên lý hoạt động và các bài học xử lý lỗi Facebook API để vận hành hệ thống Ads Auto không phụ thuộc vào AI.*

---

## 1. Bản Đồ Các File Hệ Thống (Nằm trong `Projects/tool-super-ai/`)

Hệ thống được vận hành bởi các file Python chạy tự động qua Graph API. Dưới đây là chức năng của từng file:

*   **`run-fb-workflow.bat`**: Trái tim của hệ thống. Đây là file anh sẽ click đúp vào chạy mỗi sáng. Nó tự động nạp Token và kích hoạt vòng lặp tối ưu quảng cáo.
*   **`fb-workflow.py`**: Chứa não bộ tư duy (SOP Quần Jean). Quy định rõ:
    *   *ROAS >= 3.0x*: Camp khỏe, giữ nguyên.
    *   *ROAS >= 5.0x*: Tự động tăng ngân sách 20%.
    *   *ROAS < 1.0x (Tiêu > 100k)*: Tự động tắt (PAUSE) cắt lỗ ngay.
*   **`fb-audience-builder.py`**: Tự động tạo phễu đối tượng (BOF 14 ngày, MOF Lookalike 1%).
*   **`fb-campaign-creator.py`**: Tự động tạo khung Campaign + Ad Set cho tệp BOF và MOF.
*   **`fb-test-campaign.py`**: Dùng khi cần tạo nhánh Test sản phẩm mới (Nhập link Reels vào là nó tự bắn thành Ad Set).
*   **`exchange_token.py`**: Tool tự động nâng cấp Token ngắn hạn (1h) thành Token dài hạn (60 ngày) bằng App Secret.

---

## 2. Quy Trình Vận Hành Hàng Ngày

Để làm việc nhàn hạ, anh chỉ cần lặp lại chu trình sau:

1. **Buổi sáng (Bảo trì):** Click chạy file `run-fb-workflow.bat`. Tool sẽ in ra màn hình hôm nay tắt/bật camp nào, tiêu bao nhiêu tiền, đang lãi hay lỗ.
2. **Khi ra Sản Phẩm Mới (Testing):**
   * Đăng bài lên Fanpage.
   * Cung cấp ID Bài viết cho file `fb-test-campaign.py`.
   * Chạy file để nó tự tạo Chiến dịch DOANH SỐ (MESSAGING_PURCHASE_CONVERSION), chia đều mỗi mẫu 100k test Broad trong 3 ngày.
3. **Gia hạn Token (Mỗi 60 ngày):** Khi hệ thống báo lỗi 190 (Token Expired), vào Facebook Developer lấy Token mới, bỏ vào file `exchange_token.py` để lấy Token 60 ngày, sau đó chép vào file `.bat`.

---

## 3. Cẩm Nang Xử Lý Lỗi Meta API v24 (Cực Kỳ Quan Trọng)

Dưới đây là những luật ngầm của Facebook API bản v24 mà chúng ta đã phải vượt qua. Nếu sau này anh thuê Coder khác, hãy đưa họ xem phần này để không mất thời gian dò dẫm:

| Lỗi / Tình huống | Lý do từ Facebook | Cách chúng ta Fix trong Code |
| :--- | :--- | :--- |
| **Báo lỗi `subtype` khi tạo tệp** | Bản v24 đã khai tử tham số `subtype` cho Custom Audience tương tác Page. | Gỡ bỏ `subtype`, chuyển sang dùng `event_name: PageEngagedUsers`. |
| **Báo lỗi `1815433` (Vị trí không hợp lệ)** | Mục tiêu Tin Nhắn không còn hỗ trợ hiển thị ở `video_feeds` và một số vị trí `reels`. | Chuyển `facebook_positions` về Advantage+ Placements (Tự động vị trí hoàn toàn). |
| **Báo lỗi `2490487` (Thiếu Giá Thầu)** | Chạy mục tiêu Tin Nhắn nếu dùng ABO bắt buộc phải khai báo Chiến lược giá thầu. | Thêm dòng `"bid_strategy": "LOWEST_COST_WITHOUT_CAP"` vào params của Ad Set. |
| **Báo lỗi `1870227` (Thiếu cờ Advantage)** | API v24 bắt buộc phải khai báo rõ Có hay Không dùng Tính năng mở rộng đối tượng Advantage+. | Thêm block `"targeting_automation": {"advantage_audience": 0}` (Tắt mở rộng). |
| **Báo lỗi `1870189` (Tuổi max < 65)** | NẾU BẬT Advantage+ (cờ = 1) thì FB bắt buộc tuổi max phải là 65+. | Ép `advantage_audience = 0` để được quyền khống chế độ tuổi tệp khách Nữ 22-40 theo SOP. |
| **Báo lỗi không tạo được Ads từ Reels** | Một số Reels chứa nhạc bản quyền hoặc sai định dạng Message không thể chạy trực tiếp qua API. | Bỏ qua bước tạo Ad tự động. Chỉ tạo Ad Set qua API, sau đó vào trình duyệt up thẳng Video từ máy tính. |

---

## 4. SOP Tối Ưu Quần Jean (Tóm tắt chiến lược)

*   **Test rải rác - Scale tập trung:** 5 sản phẩm phải nằm ở 5 Ad Sets khác nhau. Tiền chạy riêng biệt.
*   **Retarget kiểu "Vét lưới":** Ở phễu Đáy (BOF - Người đã nhắn tin), không chạy lại 1 sản phẩm cũ, mà chạy dạng Album/Carousel chứa toàn bộ top sản phẩm để tăng tỷ lệ chốt chéo.
*   **Quy tắc 3 ngày:** Không tắt bật campaign test trước 3 ngày. Sau 3 ngày, con nào ROAS > 3 thì giữ, ROAS < 1 thì tiễn!
