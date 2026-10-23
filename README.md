# 📰 tintuc — Tool tổng hợp tin tức trong Terminal

Gõ 1 lệnh là xem ngay tin công nghệ, thời sự thế giới, lập trình... bằng tiếng Việt,
gọn gàng trong cửa sổ terminal. Nguồn RSS từ VnExpress, Tuổi Trẻ, Genk, Tinh tế, Dev.to.

Viết bằng Python thuần — **không cần cài thư viện gì thêm**.

![demo](https://img.shields.io/badge/python-3.x-blue) ![no deps](https://img.shields.io/badge/dependencies-0-green)

---

## ⚙️ Yêu cầu

- **Python 3** (máy Mac và Linux thường có sẵn — kiểm tra bằng `python3 --version`).
  - Windows: tải tại https://www.python.org/downloads/

## 🚀 Cài đặt (1 phút)

1. Chép thư mục `tintuc` về máy (ví dụ để ở thư mục Home: `~/tintuc`).

2. (Tuỳ chọn) Tạo lệnh tắt `tintuc` cho gọn:

   **macOS / Linux (zsh):**
   ```bash
   echo "alias tintuc='python3 $HOME/tintuc/tintuc.py'" >> ~/.zshrc
   source ~/.zshrc
   ```
   **macOS / Linux (bash):**
   ```bash
   echo "alias tintuc='python3 $HOME/tintuc/tintuc.py'" >> ~/.bashrc
   source ~/.bashrc
   ```

   Nếu không tạo alias thì chạy trực tiếp: `python3 ~/tintuc/tintuc.py`

## 📖 Cách dùng

```bash
tintuc                 # Xem tất cả tin mới nhất
tintuc congnghe        # Chỉ xem 1 chuyên mục
tintuc -n 5            # Mỗi mục lấy 5 tin
tintuc -d              # Hiện thêm mô tả ngắn
tintuc --open 7        # Mở bài số 7 trên trình duyệt
tintuc --refresh       # Bỏ cache, tải tin mới ngay
tintuc --list          # Liệt kê các chuyên mục
tintuc --help          # Trợ giúp
```

## 📂 Các chuyên mục

| Lệnh       | Nội dung                  | Nguồn                       |
|------------|---------------------------|-----------------------------|
| `thegioi`  | 🌍 Thời sự thế giới        | VnExpress, Tuổi Trẻ         |
| `congnghe` | 💻 Công nghệ               | VnExpress, Genk, Tinh tế    |
| `khoahoc`  | 🔬 Khoa học & Công nghệ    | VnExpress                   |
| `laptrinh` | 👨‍💻 Lập trình              | Dev.to                      |
| `moinhat`  | 📰 Tin mới nhất            | VnExpress                   |

## 🔧 Tuỳ biến nguồn tin

Mở `tintuc.py`, phần `FEEDS` ở đầu file. Thêm/bớt nguồn chỉ cần sửa ở đó —
mỗi nguồn là 1 dòng `("Tên hiển thị", "link RSS")`.

## 💡 Ghi chú

- Tin được cache 20 phút trong `~/.cache/tintuc/` để mở cho nhanh; dùng `--refresh` để tải mới.
- Tool chỉ đọc RSS công khai, không thu thập dữ liệu cá nhân.
