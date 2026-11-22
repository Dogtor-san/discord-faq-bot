#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test matcher cho 8 entry moi duoc duyet 16/11/2026.
Cau hoi mau THAT lay tu bao cao tuan 15/11 + cach hoi paraphrase.
Chay: python3 test_new8.py (sau khi faq-new da copy sang
faq.json). Exit 0 neu tat ca pass.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matcher import FAQMatcher  # noqa: E402

M = FAQMatcher()

# (cau hoi, entry id mong doi)
CASES = [
    # custom_001 — update Bloodborne len 1.09
    ("ae nào up lên 1.09 rồi chỉ tôi với được không, làm cách nào cũng "
     "chỉ 1.00", "custom_001"),
    ("có ai bik cách patch bản 1.09 vô 1.0 k ạ", "custom_001"),
    ("làm sao để lên 1.09 vậy mọi người", "custom_001"),
    # custom_002 — 1.09 + Viet hoa
    ("có ai bik cách patch bản 1.09 vô 1.0 k ạ? e cài chung với việt "
     "hóa của cánh cụt team", "custom_002"),
    # custom_003 — Play khong chay sau 1.09
    ("các bác cho e hỏi e update lên bản 01.09 r nhma bấm play thì game "
     "ko chạy là sao nhỉ", "custom_003"),
    ("bấm play mà game không chạy là sao", "custom_003"),
    ("update lên 1.09 rồi mà bấm play ko chạy", "custom_003"),
    # custom_004 — Rom cutscene
    ("sau khi đấm xong con boss Rom game bình thường sẽ tiến vào "
     "cutscene nhưng e lại bị đen màn hình tối thui", "custom_004"),
    ("đánh xong boss Rom vào cutscene thì đen màn luôn không skip "
     "được", "custom_004"),
    # custom_005 — TOTK mods not use
    ("Vô menu check thấy có nhưng lại có dòng not use", "custom_005"),
    ("Không liên quan tới patch, bác cho e hỏi mod cho bản recomp của "
     "totk như nào vậy ạ", "custom_005"),
    ("mod totk để trong folder mods rồi mà vô game nó hiện not use",
     "custom_005"),
    # custom_006 — save Longshot
    ("anh em biết file save của longshot game zelda remake nào ở mục "
     "nào không ạ em tìm không thấy để add file save cũ qua",
     "custom_006"),
    ("save longshot nằm ở đâu vậy", "custom_006"),
    # custom_007 — Sewer texture ro
    ("Đầu game chơi rất bình thường nhưng qua đến khu cống Sewer là "
     "texture bị vỡ nhìn rất rỗ mắt", "custom_007"),
    ("texture bị rỗ ở khu sewer fix sao", "custom_007"),
    # custom_008 — camera tu zoom
    ("bác có cách nào chỉnh camera ko? cứ chạy là camera zoom ra xa "
     "rồi từ từ lại gần khó chịu quá", "custom_008"),
    ("camera zoom ra xa rồi lại gần", "custom_008"),
]

# Cau khong duoc match 8 entry moi (hoi quy — tranh hieu lam)
NEGATIVE_NEW = [
    # hoi viet hoa chung (khong nhac 1.09) -> viet_hoa, khong phai custom_002
    ("ae ai chỉ giúp cho em cách VH game zela remake với ạ",
     "viet_hoa"),
    # hoi link game chung -> link_game
    ("mình xin link zelda botw version 1.9.0 nhé", "link_game"),
]


def main():
    fails = 0
    for q, want in CASES + NEGATIVE_NEW:
        got = M.match_id(q)
        if got != want:
            fails += 1
            print(f"FAIL: muon {want}, duoc {got} | {q[:80]}")
    total = len(CASES) + len(NEGATIVE_NEW)
    print(f"{total - fails}/{total} pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
