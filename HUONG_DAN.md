# THE STAR ENGLISH CENTER — App quản lý trung tâm

App quản lý trung tâm tiếng Anh: học sinh, lớp, bài tập, điểm danh, học phí, báo cáo.
Phân quyền 6 cấp: **Admin · Giám đốc trung tâm · Quản lý lớp · Giáo viên · Phụ huynh · Học sinh**.

---

## 1. Chạy thử trên máy (Windows)

1. Bấm đúp vào file **`run.bat`**. Lần đầu sẽ tự cài thư viện (chờ vài phút).
2. Mở trình duyệt vào địa chỉ: **http://127.0.0.1:5000**
3. Đăng nhập tài khoản quản trị mặc định:
   - Tên đăng nhập: **admin**
   - Mật khẩu: **admin123**
4. **Đổi mật khẩu admin ngay** (góc trên phải → Đổi mật khẩu).

---

## 2. Thêm logo

Đặt file logo (định dạng PNG) vào thư mục `static` và đặt tên là **`logo.png`**:

```
the_star_app\static\logo.png
```

Logo này sẽ hiện ở màn hình đăng nhập và góc trên thanh menu.

---

## 3. Các bước dùng app (theo thứ tự)

1. **Người dùng** (chỉ admin): tạo tài khoản cho giám đốc, quản lý, giáo viên, phụ huynh, học sinh.
2. **Lớp học**: tạo lớp, gán giáo viên + quản lý lớp.
3. **Học sinh**: thêm học sinh, xếp vào lớp, liên kết tài khoản phụ huynh / học sinh.
4. **Bài tập**: giáo viên giao bài → học sinh nộp → giáo viên chấm điểm.
5. **Điểm danh**: chọn lớp + ngày → tích trạng thái → lưu.
6. **Học phí**: tạo phiếu theo lớp hoặc từng học sinh → thu tiền.
7. **Trang chủ**: giám đốc xem báo cáo tổng quan (số học sinh, lớp, học phí đã thu / còn nợ).

### Ai thấy được gì
| Vai trò | Quyền |
|---|---|
| Admin | Toàn bộ + quản lý tài khoản |
| Giám đốc | Xem toàn bộ trung tâm + báo cáo |
| Quản lý lớp | Lớp mình phụ trách |
| Giáo viên | Lớp mình dạy: bài tập, điểm danh, chấm điểm |
| Phụ huynh | Thông tin học tập + học phí của con |
| Học sinh | Lớp, bài tập của mình; nộp bài |

---

## 4. Đưa app lên mạng (Render — miễn phí)

Làm giống hệt app quản lý thanh toán trước đây:

1. Tạo repo mới trên GitHub, đẩy toàn bộ thư mục `the_star_app` lên (KHÔNG đẩy thư mục `venv`).
2. Vào https://render.com → **New → Web Service** → kết nối repo.
3. Cấu hình:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Phần **Environment** thêm 2 biến:
   - `SECRET_KEY` = một chuỗi ngẫu nhiên dài (để bảo mật phiên đăng nhập)
   - `DATA_DIR` = `/var/data` (cần tạo **Persistent Disk** mount vào `/var/data` để dữ liệu không bị mất mỗi lần deploy)
5. Bấm **Create Web Service**, chờ build xong là có link dùng được.

> Lưu ý: file upload (bài nộp) và database `data.db` được lưu trong `DATA_DIR`.
> Trên Render bắt buộc gắn Persistent Disk, nếu không dữ liệu sẽ mất khi app khởi động lại.

---

## 5. Cài app lên điện thoại (Android & iOS)

App đã hỗ trợ **PWA** — cài như app thật, có icon ngoài màn hình chính, mở toàn màn hình.

> **Bắt buộc:** phải deploy lên Render (mục 4) trước. Điện thoại mở bằng **link Render** (https), KHÔNG dùng được địa chỉ 127.0.0.1.

**Trên Android (trình duyệt Chrome):**
1. Mở link Render của app.
2. Bấm nút **⋮** (3 chấm) góc trên phải → **Thêm vào màn hình chính** / **Cài đặt ứng dụng**.
3. Xác nhận → icon THE STAR hiện ra ngoài màn hình như app thường.

**Trên iPhone / iPad (bắt buộc dùng Safari):**
1. Mở link Render bằng **Safari** (không dùng Chrome trên iOS).
2. Bấm nút **Chia sẻ** (hình vuông có mũi tên ↑) ở thanh dưới.
3. Chọn **Thêm vào MH chính** (Add to Home Screen) → **Thêm**.
4. Icon THE STAR xuất hiện ngoài màn hình.

> App chạy qua internet (không phải app offline). Cần có mạng để dùng.

---

## 6. Tài khoản mặc định
- `admin` / `admin123` → hãy đổi ngay sau lần đăng nhập đầu.
