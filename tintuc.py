#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tintuc - Tool tổng hợp tin tức hằng ngày trong terminal.
Tin công nghệ, thời sự thế giới, lập trình... Nguồn tiếng Việt.
Chỉ dùng thư viện chuẩn của Python, không cần cài gì thêm.

Dùng:
    tintuc                 # Xem tất cả tin mới nhất
    tintuc congnghe        # Chỉ xem 1 chuyên mục (xem danh sách bên dưới)
    tintuc -n 5            # Mỗi mục lấy 5 tin
    tintuc --refresh       # Bỏ qua cache, tải mới
    tintuc --open 7        # Mở bài số 7 (ở lần xem gần nhất) trên trình duyệt
    tintuc --list          # Liệt kê các chuyên mục
"""

import argparse
import concurrent.futures
import html
import json
import os
import re
import sys
import time
import webbrowser
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen

# ----------------------------------------------------------------------------
# Cấu hình nguồn tin. Muốn thêm/bớt nguồn thì sửa ngay ở đây.
# Mỗi mục: key -> (Tên hiển thị, màu, [danh sách (nguồn, url)])
# ----------------------------------------------------------------------------
FEEDS = {
    "thegioi": {
        "label": "🌍  THỜI SỰ THẾ GIỚI",
        "color": "\033[38;5;39m",   # xanh dương
        "sources": [
            ("VnExpress", "https://vnexpress.net/rss/the-gioi.rss"),
            ("Tuổi Trẻ",  "https://tuoitre.vn/rss/the-gioi.rss"),
        ],
    },
    "congnghe": {
        "label": "💻  CÔNG NGHỆ",
        "color": "\033[38;5;208m",  # cam
        "sources": [
            ("VnExpress", "https://vnexpress.net/rss/so-hoa.rss"),
            ("Genk",      "https://genk.vn/rss/home.rss"),
            ("Tinh tế",   "https://tinhte.vn/rss"),
        ],
    },
    "khoahoc": {
        "label": "🔬  KHOA HỌC & CÔNG NGHỆ",
        "color": "\033[38;5;49m",   # xanh ngọc
        "sources": [
            ("VnExpress", "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"),
        ],
    },
    "laptrinh": {
        "label": "👨‍💻  LẬP TRÌNH",
        "color": "\033[38;5;171m",  # tím
        "sources": [
            ("Dev.to", "https://dev.to/feed"),
        ],
    },
    "moinhat": {
        "label": "📰  TIN MỚI NHẤT",
        "color": "\033[38;5;245m",  # xám
        "sources": [
            ("VnExpress", "https://vnexpress.net/rss/tin-moi-nhat.rss"),
        ],
    },
}

# Thứ tự hiển thị các chuyên mục
ORDER = ["thegioi", "congnghe", "khoahoc", "laptrinh", "moinhat"]

CACHE_DIR = os.path.expanduser("~/.cache/tintuc")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
CACHE_TTL = 20 * 60           # 20 phút
HTTP_TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 (Macintosh; tintuc-cli)"

# Màu ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREY = "\033[38;5;240m"
WHITE = "\033[38;5;255m"
LINK = "\033[38;5;75m"

VN_TZ = timezone(timedelta(hours=7))


# ----------------------------------------------------------------------------
def term_width():
    try:
        return max(40, os.get_terminal_size().columns)
    except OSError:
        return 80


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=VN_TZ)
        return dt
    except (TypeError, ValueError, IndexError):
        return None


def time_ago(dt):
    if dt is None:
        return ""
    now = datetime.now(timezone.utc)
    delta = now - dt.astimezone(timezone.utc)
    secs = delta.total_seconds()
    if secs < 0:
        return "vừa xong"
    mins = int(secs // 60)
    if mins < 1:
        return "vừa xong"
    if mins < 60:
        return f"{mins} phút trước"
    hours = mins // 60
    if hours < 24:
        return f"{hours} giờ trước"
    days = hours // 24
    if days == 1:
        return "hôm qua"
    if days < 7:
        return f"{days} ngày trước"
    return dt.astimezone(VN_TZ).strftime("%d/%m")


def fetch_feed(source, url):
    """Tải và parse 1 feed RSS. Trả về list dict item. Lỗi -> []."""
    import xml.etree.ElementTree as ET
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = resp.read()
        root = ET.fromstring(data)
    except Exception:
        return []

    items = []
    # RSS 2.0: channel/item ; Atom: entry
    nodes = root.iter("item")
    found = False
    for item in nodes:
        found = True
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or ""
        dt = parse_date(pub)
        items.append({
            "title": strip_html(title),
            "link": link.strip(),
            "desc": strip_html(desc),
            "source": source,
            "ts": dt.timestamp() if dt else 0,
        })
    if not found:
        # Thử Atom
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.iter(ns + "entry"):
            title = entry.findtext(ns + "title") or ""
            link_el = entry.find(ns + "link")
            link = link_el.get("href") if link_el is not None else ""
            desc = entry.findtext(ns + "summary") or ""
            pub = entry.findtext(ns + "published") or entry.findtext(ns + "updated") or ""
            dt = parse_date(pub)
            items.append({
                "title": strip_html(title),
                "link": (link or "").strip(),
                "desc": strip_html(desc),
                "source": source,
                "ts": dt.timestamp() if dt else 0,
            })
    return items


def gather(selected_keys, per_source_limit=12):
    """Tải tất cả feed của các chuyên mục đã chọn (song song)."""
    jobs = []
    for key in selected_keys:
        for source, url in FEEDS[key]["sources"]:
            jobs.append((key, source, url))

    results = {key: [] for key in selected_keys}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        future_map = {
            ex.submit(fetch_feed, source, url): (key, source)
            for (key, source, url) in jobs
        }
        for fut in concurrent.futures.as_completed(future_map):
            key, _source = future_map[fut]
            try:
                items = fut.result()
            except Exception:
                items = []
            results[key].extend(items[:per_source_limit])

    # Sắp xếp mỗi mục theo thời gian mới nhất, loại trùng theo link
    for key in results:
        seen = set()
        uniq = []
        for it in sorted(results[key], key=lambda x: x["ts"], reverse=True):
            if it["link"] in seen or not it["title"]:
                continue
            seen.add(it["link"])
            uniq.append(it)
        results[key] = uniq
    return results


# ----------------------------------------------------------------------------
def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_cache(payload):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


# ----------------------------------------------------------------------------
def render(results, per_cat_limit, show_desc):
    width = term_width()
    now = datetime.now(VN_TZ)
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
                "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    header = f"  TIN TỨC HÔM NAY · {weekdays[now.weekday()]}, {now.strftime('%d/%m/%Y · %H:%M')}  "
    bar = "─" * len(header)
    print()
    print(f"{BOLD}{WHITE}{header}{RESET}")
    print(f"{GREY}{bar}{RESET}")

    index = 1
    flat = []  # để map số -> link cho --open
    for key in ORDER:
        if key not in results:
            continue
        items = results[key][:per_cat_limit]
        if not items:
            continue
        cfg = FEEDS[key]
        print()
        print(f"{cfg['color']}{BOLD}{cfg['label']}{RESET}")
        print(f"{cfg['color']}{'─' * min(len(cfg['label']) + 2, width)}{RESET}")
        for it in items:
            num = f"{DIM}{index:>2}.{RESET}"
            meta = f"{GREY}({it['source']}"
            ta = time_ago(datetime.fromtimestamp(it["ts"], timezone.utc)) if it["ts"] else ""
            if ta:
                meta += f" · {ta}"
            meta += f"){RESET}"

            title = it["title"]
            prefix_len = 5  # "nn. "
            max_title = width - prefix_len
            if len(title) > max_title:
                title = title[:max_title - 1] + "…"
            print(f" {num} {WHITE}{title}{RESET}")
            print(f"     {meta}")
            if show_desc and it["desc"]:
                d = it["desc"]
                maxd = width - 6
                if len(d) > maxd:
                    d = d[:maxd - 1] + "…"
                print(f"     {DIM}{d}{RESET}")
            print(f"     {GREY}{LINK}{it['link']}{RESET}")
            flat.append({"title": it["title"], "link": it["link"]})
            index += 1
    print()
    print(f"{GREY}  Mẹo: 'tintuc --open <số>' để mở bài trên trình duyệt · "
          f"'tintuc --refresh' để tải mới{RESET}")
    print()
    return flat


# ----------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Tool tổng hợp tin tức hằng ngày trong terminal.",
        add_help=False,
    )
    p.add_argument("category", nargs="?", default="all",
                   help="Chuyên mục muốn xem (mặc định: tất cả)")
    p.add_argument("-n", "--num", type=int, default=8,
                   help="Số tin mỗi chuyên mục (mặc định 8)")
    p.add_argument("-r", "--refresh", action="store_true",
                   help="Bỏ qua cache, tải mới")
    p.add_argument("-d", "--desc", action="store_true",
                   help="Hiện mô tả ngắn của mỗi tin")
    p.add_argument("-o", "--open", type=int, metavar="SỐ", dest="open_idx",
                   help="Mở bài số N (từ lần xem gần nhất) trên trình duyệt")
    p.add_argument("-l", "--list", action="store_true",
                   help="Liệt kê các chuyên mục")
    p.add_argument("-h", "--help", action="store_true", help="Trợ giúp")
    args = p.parse_args()

    if args.help:
        print(__doc__)
        return

    if args.list:
        print(f"\n{BOLD}Các chuyên mục:{RESET}")
        for key in ORDER:
            srcs = ", ".join(s for s, _ in FEEDS[key]["sources"])
            print(f"  {FEEDS[key]['color']}{key:<10}{RESET} {FEEDS[key]['label']}  {GREY}({srcs}){RESET}")
        print(f"\n  Ví dụ: {BOLD}tintuc congnghe{RESET}\n")
        return

    # --open: đọc cache, mở bài
    if args.open_idx is not None:
        cache = load_cache()
        if not cache or "flat" not in cache:
            print("Chưa có dữ liệu. Chạy 'tintuc' trước đã nhé.")
            return
        flat = cache["flat"]
        i = args.open_idx
        if i < 1 or i > len(flat):
            print(f"Số không hợp lệ. Hiện có bài 1 đến {len(flat)}.")
            return
        art = flat[i - 1]
        print(f"Đang mở: {art['title']}\n{art['link']}")
        webbrowser.open(art["link"])
        return

    # Chọn chuyên mục
    if args.category == "all":
        selected = list(ORDER)
    elif args.category in FEEDS:
        selected = [args.category]
    else:
        print(f"Không có chuyên mục '{args.category}'. "
              f"Chạy 'tintuc --list' để xem danh sách.")
        return

    # Dùng cache nếu còn mới và đúng phạm vi
    cache = load_cache()
    use_cache = (
        cache
        and not args.refresh
        and cache.get("selected") == selected
        and (time.time() - cache.get("fetched_at", 0)) < CACHE_TTL
    )

    if use_cache:
        results = {k: cache["results"].get(k, []) for k in selected}
    else:
        sys.stderr.write("Đang tải tin mới...\r")
        sys.stderr.flush()
        results = gather(selected)
        sys.stderr.write(" " * 30 + "\r")

    flat = render(results, args.num, args.desc)

    save_cache({
        "fetched_at": cache["fetched_at"] if use_cache else time.time(),
        "selected": selected,
        "results": results,
        "flat": flat,
    })


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
