#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lop luu tru FAQ (thuan Python, khong phu thuoc discord.py) cho bot FAQ.

Dung chung cho lenh /faq-add, /faq-list, /faq-del: doc/ghi faq.json,
validate entry moi, sinh id, dinh dang danh sach. Bot chi goi cac ham
nay — logic khop van nam o matcher.py (tai su dung ham normalize() o
do, khong viet lai logic chuan hoa khac).

Dinh dang file giu nguyen nhu ban goc: JSON 1 dong, sort_keys=True,
ensure_ascii=False, khong newline cuoi file.
"""
import json
import os
import re

from matcher import normalize

MAX_ANSWER_LEN = 1900  # de cho tin nhan Discord (gioi han 2000 ky tu)
MAX_TRIGGERS = 30
_CUSTOM_RE = re.compile(r"^custom_(\d+)$")


def load_data(faq_path):
    """Doc toan bo faq.json (dict)."""
    with open(faq_path, encoding="utf-8") as fh:
        return json.load(fh)


def save_data(faq_path, data):
    """Ghi faq.json theo kieu atomic: ghi file tam roi os.replace,
    tranh file bi do dang neu bot chet giua chung."""
    tmp = faq_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, faq_path)


def parse_triggers(raw):
    """Tach chuoi trigger bang dau phay -> list trigger da chuan hoa
    (dung normalize() cua matcher), loai rong + trung, giu thu tu."""
    out = []
    for part in (raw or "").split(","):
        nt = normalize(part)
        if nt and nt not in out:
            out.append(nt)
    return out


def build_answer(answer, answer_en=None):
    """Ghep dap an + dong English theo dung dinh dang entry co san."""
    text = (answer or "").strip()
    en = (answer_en or "").strip()
    if en:
        text += "\n🌐 English: " + en
    return text


def validate_new_entry(triggers_raw, answer, answer_en=None):
    """Kiem tra entry moi. Tra (triggers, full_answer, error):
    error None neu hop le, neu khong thi la thong bao loi tieng Viet."""
    triggers = parse_triggers(triggers_raw)
    full = build_answer(answer, answer_en)
    if not (answer or "").strip():
        return [], "", "Đáp án không được để trống."
    if not triggers:
        return [], "", ("Cần ít nhất 1 cụm trigger (các cụm cách nhau "
                        "bằng dấu phẩy).")
    if len(triggers) > MAX_TRIGGERS:
        return [], "", (f"Tối đa {MAX_TRIGGERS} trigger mỗi entry "
                        f"(hiện có {len(triggers)}).")
    if not any(len(t.split()) >= 2 for t in triggers):
        return [], "", ("Cần ít nhất 1 trigger có từ 2 từ trở lên sau "
                        "khi chuẩn hoá — trigger toàn 1 từ thì bot sẽ "
                        "không bao giờ trả lời entry này (matcher chỉ "
                        "trả lời khi khớp cụm từ 2 từ trở lên). Ví dụ: "
                        "'pass giai nen' thay vì chỉ 'pass'.")
    if len(full) > MAX_ANSWER_LEN:
        return [], "", (f"Đáp án quá dài ({len(full)} ký tự, tối đa "
                        f"{MAX_ANSWER_LEN} ký tự kể cả dòng English).")
    return triggers, full, None


def next_custom_id(existing_ids):
    """Sinh id dang custom_NNN, khong trung id cu (max+1)."""
    max_n = 0
    for eid in existing_ids:
        m = _CUSTOM_RE.match(eid)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"custom_{max_n + 1:03d}"


def add_entry(faq_path, triggers_raw, answer, answer_en=None):
    """Them entry vao faq.json. Tra (entry, error): error None neu
    thanh cong."""
    triggers, full, err = validate_new_entry(triggers_raw, answer,
                                             answer_en)
    if err:
        return None, err
    data = load_data(faq_path)
    entry_id = next_custom_id(e["id"] for e in data["entries"])
    entry = {
        "id": entry_id,
        "title": triggers[0],
        "answer": full,
        "triggers": triggers,
    }
    data["entries"].append(entry)
    save_data(faq_path, data)
    return entry, None


def delete_entry(faq_path, entry_id):
    """Xoa entry theo id. Tra entry da xoa, None neu khong co."""
    entry_id = (entry_id or "").strip()
    data = load_data(faq_path)
    for i, e in enumerate(data["entries"]):
        if e["id"] == entry_id:
            removed = data["entries"].pop(i)
            save_data(faq_path, data)
            return removed
    return None


def format_entry_line(entry):
    """1 dong cho /faq-list: id + trigger dau + 60 ky tu dau dap an."""
    triggers = entry.get("triggers") or [""]
    first = triggers[0]
    preview = " ".join((entry.get("answer") or "").split())[:60]
    return f"`{entry['id']}` · {first} — {preview}"


def chunk_lines(lines, limit=1900):
    """Gom cac dong thanh tung tin <= limit ky tu (gioi han 2000
    cua Discord, de du 100 ky tu)."""
    chunks = []
    cur = ""
    for line in lines:
        piece = line if not cur else "\n" + line
        if len(cur) + len(piece) > limit and cur:
            chunks.append(cur)
            cur = line
        else:
            cur += piece
    if cur:
        chunks.append(cur)
    return chunks
