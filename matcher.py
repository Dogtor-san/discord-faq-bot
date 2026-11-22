#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAQ matcher (thuan Python, khong phu thuoc discord.py) cho bot FAQ.

Quy tac khop:
  - Chuan hoa tin nhan: lowercase, bo dau tieng Viet (NFKD + đ->d),
    bo dau cau, gop khoang trang.
  - Trigger la cum tu da chuan hoa san trong faq.json; khop theo bien
    tu (cum tu lien tiep trong tin nhan).
  - Diem: moi trigger khop cong max(2, so tu). Entry thang la entry
    co tong diem cao nhat; hoa thi uu tien tong so tu khop, roi so
    trigger khop, roi thu tu dinh nghia trong faq.json.
  - QUAN TRONG: mot entry chi duoc tra loi khi khop it nhat 1 trigger
    TU 2 TU TRO LEN. Trigger 1 tu (vd "pass", "link", "mod") chi cong
    diem phu khi da co trigger dai — tranh bot tra loi bua khi user
    chi nhac vu vơ 1 tu ("pass qua di", "mod nay dep").
  - Exclusion: tin chua cum trong danh sach exclusions thi khong tra
    loi (vd "xin link discord" khong phai xin link game).
  - Khong chac thi IM LANG: match() tra None.
"""
import json
import os
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, "faq.json")

_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def normalize(text):
    """Lowercase + bo dau tieng Viet + bo dau cau + gop khoang trang."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # đ/Đ khong bi tach boi NFKD nen xu ly tay.
    text = text.replace("đ", "d").replace("Đ", "d")
    text = text.lower()
    text = _NON_ALNUM.sub(" ", text)
    return _WS.sub(" ", text).strip()


def trigger_weight(trigger):
    return max(2, len(trigger.split()))


class FAQMatcher:
    def __init__(self, faq_path=FAQ_PATH):
        with open(faq_path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.exclusions = [normalize(e) for e in data.get("exclusions", [])]
        self.entries = []
        for e in data["entries"]:
            triggers = []
            for t in e["triggers"]:
                nt = normalize(t)
                triggers.append((nt, trigger_weight(nt), len(nt.split())))
            self.entries.append({
                "id": e["id"],
                "title": e.get("title", e["id"]),
                "answer": e["answer"],
                "triggers": triggers,
            })

    def match(self, text):
        """Tra {'entry', 'triggers', 'score'} neu khop, None neu khong."""
        norm = normalize(text)
        if not norm:
            return None
        padded = f" {norm} "
        for ex in self.exclusions:
            if f" {ex} " in padded:
                return None
        best = None
        for idx, entry in enumerate(self.entries):
            matched = [t for t in entry["triggers"]
                       if f" {t[0]} " in padded]
            if not matched:
                continue
            if not any(t[2] >= 2 for t in matched):
                continue
            score = sum(t[1] for t in matched)
            words = sum(t[2] for t in matched)
            key = (score, words, len(matched), -idx)
            if best is None or key > best[0]:
                best = (key, entry, [t[0] for t in matched])
        if best is None:
            return None
        return {"entry": best[1], "triggers": best[2], "score": best[0][0]}

    def match_id(self, text):
        """Tien ich cho test: tra entry id hoac None."""
        r = self.match(text)
        return r["entry"]["id"] if r else None
