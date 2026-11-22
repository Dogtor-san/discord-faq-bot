#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test quan ly database FAQ (faq_store.py) dung cho /faq-add,
/faq-list, /faq-del.
  - Them/xoa/reload chay tren BAN SAO TAM cua faq.json trong
    tempfile — KHONG bao gio dung file faq.json that.
  - Validation: trigger chi 1 tu thi bi tu choi, dap an rong bi tu
    choi, dap an qua dai bi tu choi, id sinh khong trung.
  - Matcher moi (mo phong load_faq()) thay entry moi ngay sau khi
    them, va khong thay entry da xoa.
Chay: python3 test_faq_store.py (khong can discord.py).
Exit 0 neu tat ca pass, 1 neu co fail.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faq_store import (add_entry, build_answer, chunk_lines,  # noqa: E402
                       delete_entry, format_entry_line, load_data,
                       next_custom_id, parse_triggers)
from matcher import FAQMatcher  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_FAQ = os.path.join(ROOT, "faq.json")

FAILS = []
TOTAL = [0]


def check(name, cond, extra=""):
    TOTAL[0] += 1
    if cond:
        print(f"  PASS {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL {name} {extra}")


def fresh_copy(tmpdir):
    """Ban sao faq.json that vao thu muc tam, tra duong dan."""
    dst = os.path.join(tmpdir, "faq.json")
    shutil.copy(REAL_FAQ, dst)
    return dst


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with open(REAL_FAQ, "rb") as fh:
            real_before = fh.read()
        # --- parse_triggers: chuan hoa giong matcher, dedupe ---
        print("=== PARSE TRIGGERS ===")
        got = parse_triggers("Pass Giải Nén, pass giai nen, , MẬT KHẨU rar")
        check("normalize + dedupe",
              got == ["pass giai nen", "mat khau rar"], f"-> {got}")
        check("rong -> []", parse_triggers(" , , ") == [])
        check("prod.keys -> prod keys",
              parse_triggers("prod.keys") == ["prod keys"])

        # --- next_custom_id ---
        print("=== NEXT CUSTOM ID ===")
        check("khong co custom -> custom_001",
              next_custom_id(["a", "b"]) == "custom_001")
        check("max+1 (custom_002, custom_010 -> 011)",
              next_custom_id(["custom_002", "x", "custom_010"])
              == "custom_011")

        # --- build_answer ---
        print("=== BUILD ANSWER ===")
        check("khong co EN",
              build_answer("  Tra loi viet  ") == "Tra loi viet")
        check("co EN",
              build_answer("Tra loi", "Answer") ==
              "Tra loi\n🌐 English: Answer")

        # --- add hop le + reload + matcher thay entry moi ---
        print("=== ADD HOP LE ===")
        path = fresh_copy(tmp)
        before = len(load_data(path)["entries"])
        next_id = next_custom_id(
            [e["id"] for e in load_data(path)["entries"]])
        entry, err = add_entry(
            path, "pass wifi quan, mat khau wifi",
            "Pass wifi quán là 12345678 nha chú.", "WiFi password.")
        check("add thanh cong", err is None and entry is not None,
              f"err={err}")
        check("id = next custom id", entry["id"] == next_id,
              f"-> {entry['id']}")
        check("title = trigger dau",
              entry["title"] == "pass wifi quan")
        check("so entry +1",
              len(load_data(path)["entries"]) == before + 1)
        check("dap an co dong EN",
              "\n🌐 English: WiFi password." in entry["answer"])
        m = FAQMatcher(path)  # mo phong load_faq() sau khi them
        check("matcher moi thay entry moi",
              m.match_id("cho mình hỏi pass wifi quán là gì")
              == next_id)
        check("matcher van dung cho entry goc",
              m.match_id("pass giải nén pokopia là gì")
              == "extract_password")

        # --- add thu 2: id khong trung ---
        next_id2 = next_custom_id(
            [e["id"] for e in load_data(path)["entries"]])
        entry2, err2 = add_entry(path, "cach doi avatar",
                                 "Vào setting đổi avatar nha chú.")
        check("add thu 2 -> id ke tiep",
              err2 is None and entry2["id"] == next_id2,
              f"-> {entry2['id'] if entry2 else err2}")

        # --- validation: trigger chi 1 tu ---
        print("=== VALIDATION ===")
        e, err = add_entry(path, "pass, mod, link",
                           "Dap an gi do.")
        check("chi trigger 1 tu -> bi tu choi",
              e is None and err is not None and "2 từ" in err,
              f"err={err}")
        check("file khong doi sau khi bi tu choi",
              len(load_data(path)["entries"]) == before + 2)
        # trigger 1 tu + 1 trigger 2 tu thi OK
        e, err = add_entry(path, "pass, mat khau game",
                           "Dap an gi do.")
        check("1 tu + 2 tu -> duoc them",
              err is None and e is not None, f"err={err}")
        # dap an rong
        e, err = add_entry(path, "cau hoi dai", "   ")
        check("dap an rong -> bi tu choi",
              e is None and err is not None and "trống" in err,
              f"err={err}")
        # dap an qua dai (1901 ky tu)
        e, err = add_entry(path, "cau hoi dai", "x" * 1901)
        check("dap an 1901 ky tu -> bi tu choi",
              e is None and err is not None and "quá dài" in err,
              f"err={err}")
        # dap an dung 1900 ky tu -> OK
        e, err = add_entry(path, "cau hoi dai dung", "y" * 1900)
        check("dap an dung 1900 ky tu -> duoc them",
              err is None and e is not None, f"err={err}")
        # dap an + EN vuot 1900 -> bi tu choi
        e, err = add_entry(path, "cau hoi dai en", "z" * 1890,
                           "0123456789")
        check("dap an + EN vuot 1900 -> bi tu choi",
              e is None and err is not None, f"err={err}")
        # khong co trigger nao
        e, err = add_entry(path, " , ", "Dap an.")
        check("khong co trigger -> bi tu choi",
              e is None and err is not None, f"err={err}")

        # --- delete ---
        print("=== DELETE ===")
        n_before = len(load_data(path)["entries"])
        removed = delete_entry(path, next_id)
        check("xoa entry vua them -> tra entry",
              removed is not None and removed["id"] == next_id)
        check("so entry -1",
              len(load_data(path)["entries"]) == n_before - 1)
        m2 = FAQMatcher(path)  # mo phong load_faq() sau khi xoa
        check("matcher moi khong thay entry da xoa",
              m2.match_id("cho mình hỏi pass wifi quán là gì")
              is None)
        check("entry khac van con",
              m2.match_id("cach doi avatar nhu nao")
              == next_id2)
        missing = delete_entry(path, "khong_co_id_nay")
        check("xoa id khong co -> None",
              missing is None)
        check("file khong doi khi xoa id khong co",
              len(load_data(path)["entries"]) == n_before - 1)
        # xoa entry goc tren ban sao (khong anh huong file that)
        removed2 = delete_entry(path, "amiibo")
        check("xoa entry goc (amiibo) tren ban sao duoc",
              removed2 is not None and removed2["id"] == "amiibo")
        check("matcher khong thay amiibo nua",
              FAQMatcher(path).match_id("2 file bin làm gì vậy")
              is None)

        # --- format + chunk cho /faq-list ---
        print("=== FORMAT / CHUNK (faq-list) ===")
        data = load_data(path)
        lines = [format_entry_line(e) for e in data["entries"]]
        check("dong list co id + trigger + preview",
              lines[0].startswith("`hookshot_longshot`")
              and "longshot nua" in lines[0])
        check("preview <= 60 ky tu",
              all(len(l.split(" — ", 1)[1]) <= 60 for l in lines
                  if " — " in l))
        chunks = chunk_lines(
            [f"**Database FAQ — {len(lines)} entry:**"] + lines)
        check("moi chunk <= 1900 ky tu",
              all(len(c) <= 1900 for c in chunks))
        rejoined = "\n".join(chunks)
        check("chunk ghep lai du dong",
              rejoined.count("\n") + 1 == len(lines) + 1)
        check("chunk rong -> []", chunk_lines([]) == [])

        # --- file that khong bi dung toi ---
        print("=== FILE THAT NGUYEN VEN ===")
        with open(REAL_FAQ, "rb") as fh:
            real_after = fh.read()
        check("faq.json that khong doi (byte-identical)",
              real_after == real_before)
        real = load_data(REAL_FAQ)
        check("faq.json that van du entry",
              len(real["entries"]) == before,
              f"-> {len(real['entries'])}")

    print(f"\nTONG: {TOTAL[0] - len(FAILS)}/{TOTAL[0]} pass, "
          f"{len(FAILS)} fail")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
