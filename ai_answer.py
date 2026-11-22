#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lop tra loi AI (Google Gemini, goi mien phi) cho bot FAQ.

Chi chay khi matcher tu khoa KHONG khop cau hoi nao: hoi Gemini
dua tren toan bo FAQ entries lam ngu canh (grounded). Model chi
duoc tra loi bang thong tin co trong FAQ — cau hoi ngoai FAQ thi
model tra marker KHONG_BIET va bot im lang nhu cu.

Khong bao gio lam sap bot: ask_ai() tra None (khong raise) khi
khong co key, het gioi han ngay, timeout, loi HTTP, JSON loi,
model tra marker, dap an rong. Ly do that bai gan nhat nam o
LAST_FAILURE de bot.py log 1 dong ngan (None neu lan goi gan
nhat thanh cong hoac model tra KHONG_BIET — khong biet la
binh thuong, khong phai loi).
"""
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

MODEL = "gemini-3.5-flash-lite"  # model chinh (chay on dinh, 1.3s)
# Danh sach fallback: 3.8-flash (model moi nhat) hay qua tai 503 o goi
# mien phi (11/2026) — thu lan luot, model nao loi thi sang model sau.
# 2.0-flash va 2.5-flash da bi Google khai tu / khoa voi user moi.
MODELS = [MODEL, "gemini-3.7-flash", "gemini-3.8-flash"]
API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
TIMEOUT_SECONDS = 20
MAX_ANSWER_LEN = 800
DAILY_LIMIT = 100
UNKNOWN_MARKER = "KHONG_BIET"

VN_TZ = timezone(timedelta(hours=7))

SYSTEM_PROMPT = (
    "Bạn là trợ lý FAQ của một server Discord cộng đồng game Việt Nam. "
    "Nhiệm vụ: trả lời câu hỏi của thành viên CHỈ dựa trên nội dung FAQ "
    "dưới đây.\n\n"
    "Quy tắc bắt buộc:\n"
    "- Chỉ dùng thông tin có trong FAQ. Không bịa thêm, không đoán, "
    "không dùng kiến thức ngoài FAQ.\n"
    "- Xưng hô thân mật kiểu bé–chú: bạn là \"bé/em\", người hỏi là \"chú\".\n"
    "- Trả lời bằng cùng ngôn ngữ với câu hỏi (mặc định tiếng Việt; "
    "câu hỏi tiếng Anh thì trả lời tiếng Anh).\n"
    "- Đáp án ngắn gọn, tối đa 800 ký tự.\n"
    "- Nếu câu hỏi KHÔNG có đáp án trong FAQ, chỉ trả về đúng chuỗi "
    "KHONG_BIET, không thêm bất cứ chữ nào khác."
)

# Ly do that bai gan nhat (de bot.py log). None neu lan goi gan
# nhat thanh cong hoac model tra KHONG_BIET.
LAST_FAILURE = None

# Model da tra dap an o lan goi gan nhat (None neu that bai).
LAST_MODEL = None

# Dem luot goi AI trong ngay (gio VN), reset luc 0h.
_USAGE = {"date": None, "count": 0}


def _today_vn():
    return datetime.now(VN_TZ).date().isoformat()


def reset_usage():
    """Reset bo dem ngay (dung cho test)."""
    _USAGE["date"] = None
    _USAGE["count"] = 0


def _under_daily_limit():
    today = _today_vn()
    if _USAGE["date"] != today:
        _USAGE["date"] = today
        _USAGE["count"] = 0
    if _USAGE["count"] >= DAILY_LIMIT:
        return False
    _USAGE["count"] += 1
    return True


def _trigger_text(trigger):
    # Matcher luu trigger dang tuple (text, weight, wordcount);
    # faq.json goc luu dang chuoi — chap nhan ca hai.
    if isinstance(trigger, (list, tuple)):
        return str(trigger[0])
    return str(trigger)


def build_context(entries):
    """Gom toan bo FAQ entries thanh khoi text lam ngu canh cho AI."""
    blocks = []
    for e in entries or []:
        triggers = ", ".join(_trigger_text(t) for t in e.get("triggers", []))
        blocks.append(
            f"[{e.get('id', '?')}] {e.get('title', '')}\n"
            f"Cách hỏi: {triggers}\n"
            f"Đáp án: {e.get('answer', '')}")
    return "\n\n".join(blocks)


def build_payload(question, entries):
    """Body JSON gui len Gemini: system instruction + FAQ + cau hoi."""
    user_text = (
        "Dưới đây là toàn bộ nội dung FAQ của server:\n\n"
        f"{build_context(entries)}\n\n"
        f"Câu hỏi của thành viên: {question}")
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 400,
        },
    }


def ask_ai(question, entries, key):
    """Hoi Gemini. Tra dap an (str, toi da 800 ky tu) hoac None.
    Thu lan luot cac model trong MODELS — model nao loi (503 qua
    tai, timeout, loi mang...) thi sang model sau. Khong bao gio
    raise exception."""
    global LAST_FAILURE, LAST_MODEL
    LAST_FAILURE = None
    LAST_MODEL = None
    if not (key or "").strip():
        LAST_FAILURE = "chua co GEMINI_API_KEY"
        return None
    if not (question or "").strip():
        LAST_FAILURE = "cau hoi rong"
        return None
    if not _under_daily_limit():
        LAST_FAILURE = f"het gioi han ngay ({DAILY_LIMIT} luot)"
        return None
    body = json.dumps(build_payload(question, entries),
                      ensure_ascii=False).encode("utf-8")
    headers = {"x-goog-api-key": key.strip(),
               "Content-Type": "application/json"}
    for model in MODELS:
        try:
            req = urllib.request.Request(
                f"{API_URL_BASE}{model}:generateContent",
                data=body, method="POST", headers=headers)
            with urllib.request.urlopen(req,
                                        timeout=TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = (data.get("candidates") or [{}])[0] \
                .get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
        except urllib.error.HTTPError as exc:
            LAST_FAILURE = f"Gemini HTTP {exc.code}"
            continue
        except Exception as exc:  # noqa: BLE001 - timeout/JSON/mang
            LAST_FAILURE = f"loi goi Gemini ({type(exc).__name__})"
            continue
        if not text:
            LAST_FAILURE = "model tra dap an rong"
            continue
        if text.rstrip(".! \n") == UNKNOWN_MARKER:
            # Khong biet la dinh (ngoai FAQ) — khong can thu model
            # khac, LAST_FAILURE giu None de bot khong log spam.
            LAST_FAILURE = None
            return None
        LAST_MODEL = model
        LAST_FAILURE = None
        return text[:MAX_ANSWER_LEN]
    return None
