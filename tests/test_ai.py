#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test lop tra loi AI (ai_answer.py) cua bot FAQ.
  - Stub urllib.request.urlopen — khong goi Gemini that.
  - Dap an grounded hop le duoc tra ve; marker KHONG_BIET -> None;
    HTTP 403/429/timeout/JSON loi -> None; khong co key -> None;
    gioi han ngay 100 luot roi None, reset khi sang ngay moi;
    prompt chua noi dung FAQ + huong dan marker; dap an cat 800 ky tu.
Chay: python3 test_ai.py (khong can discord.py).
Exit 0 neu tat ca pass, 1 neu co fail.
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_answer  # noqa: E402

FAILS = []
TOTAL = [0]

# Entry dang raw (trigger la chuoi) + dang matcher (trigger la tuple).
SAMPLE_ENTRIES = [
    {"id": "extract_password", "title": "Mat khau giai nen",
     "triggers": ["pass giai nen", "mat khau rar"],
     "answer": "Pass giải nén tất cả file là @bamon.gaming nha chú."},
    {"id": "link_game", "title": "Xin link game",
     "triggers": [("xin link game", 3, 3), ("link tai o dau", 4, 4)],
     "answer": "Chú bấm nút 🎮 trong panel ở #requests để lấy link nha."},
]
QUESTION = "cho em hỏi pass giải nén file game là gì vậy"
KEY = "test-key-khong-that"


def check(name, cond, extra=""):
    TOTAL[0] += 1
    if cond:
        print(f"  PASS {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL {name} {extra}")


class FakeResponse:
    def __init__(self, data_bytes):
        self._data = data_bytes

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gemini_payload(text):
    return {"candidates": [{"content": {"parts": [{"text": text}],
                                        "role": "model"}}]}


class UrlopenStub:
    """Ghi lai request, tra payload tuy theo che do."""

    def __init__(self, mode="ok", text=""):
        self.mode = mode
        self.text = text
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        if self.mode == "http403":
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden",
                                         {}, None)
        if self.mode == "http429":
            raise urllib.error.HTTPError(req.full_url, 429,
                                         "Too Many Requests", {}, None)
        if self.mode == "all503":
            raise urllib.error.HTTPError(req.full_url, 503,
                                         "Service Unavailable", {}, None)
        if self.mode == "fail_first_503":
            # Model chinh 503 qua tai, model fallback tra loi binh thuong.
            if ai_answer.MODELS[0] in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 503,
                                             "Service Unavailable",
                                             {}, None)
        if self.mode == "timeout":
            raise TimeoutError("timed out")
        if self.mode == "badjson":
            return FakeResponse(b"not json{{")
        if self.mode == "nocandidates":
            return FakeResponse(json.dumps({"candidates": []}).encode())
        return FakeResponse(json.dumps(
            gemini_payload(self.text)).encode())


def header_of(req, name):
    """Lay header khong phan biet hoa/thuong."""
    for k, v in req.headers.items():
        if k.lower() == name.lower():
            return v
    return None


def run_with_stub(stub, question=QUESTION, entries=SAMPLE_ENTRIES,
                  key=KEY):
    """Chay ask_ai voi urlopen da stub. Tra (ket qua, stub)."""
    orig = urllib.request.urlopen
    urllib.request.urlopen = stub
    try:
        return ai_answer.ask_ai(question, entries, key), stub
    finally:
        urllib.request.urlopen = orig


def main():
    # --- build_context: chap nhan ca trigger chuoi va tuple ---
    print("=== BUILD CONTEXT ===")
    ctx = ai_answer.build_context(SAMPLE_ENTRIES)
    check("chua id + title",
          "[extract_password] Mat khau giai nen" in ctx, f"-> {ctx[:120]}")
    check("chua trigger chuoi", "pass giai nen" in ctx)
    check("chua trigger tuple", "xin link game" in ctx)
    check("chua dap an", "@bamon.gaming" in ctx)
    check("entries rong -> chuoi rong",
          ai_answer.build_context([]) == "")

    # --- Dap an hop le ---
    print("=== DAP AN HOP LE ===")
    ai_answer.reset_usage()
    ans, stub = run_with_stub(UrlopenStub(
        "ok", "Pass giải nén là @bamon.gaming nha chú."))
    check("tra dap an", ans == "Pass giải nén là @bamon.gaming nha chú.",
          f"-> {ans!r}")
    check("LAST_FAILURE None sau thanh cong",
          ai_answer.LAST_FAILURE is None)

    # --- Prompt: chua FAQ + huong dan marker, header key, model ---
    print("=== PROMPT + REQUEST ===")
    req = stub.requests[0]
    body = json.loads(req.data.decode("utf-8"))
    sys_text = body["system_instruction"]["parts"][0]["text"]
    user_text = body["contents"][0]["parts"][0]["text"]
    check("system prompt co huong dan marker",
          "KHONG_BIET" in sys_text)
    check("system prompt chi dung FAQ",
          "CHỈ dựa trên nội dung FAQ" in sys_text)
    check("user text chua noi dung FAQ",
          "@bamon.gaming" in user_text and "🎮" in user_text)
    check("user text chua cau hoi", QUESTION in user_text)
    check("header x-goog-api-key dung key",
          header_of(req, "x-goog-api-key") == KEY)
    check("URL dung model chinh (gemini-3.5-flash-lite)",
          ai_answer.MODELS[0] in req.full_url
          and ai_answer.MODEL == "gemini-3.5-flash-lite",
          f"-> {req.full_url}")
    check("danh sach fallback dung thu tu",
          ai_answer.MODELS == ["gemini-3.5-flash-lite",
                               "gemini-3.7-flash", "gemini-3.8-flash"],
          f"-> {ai_answer.MODELS}")
    check("temperature thap (factual)",
          body["generationConfig"]["temperature"] == 0.2)

    # --- Marker KHONG_BIET ---
    print("=== MARKER KHONG_BIET ===")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("ok", "KHONG_BIET"))
    check("marker dung -> None", ans is None, f"-> {ans!r}")
    check("marker khong phai loi (LAST_FAILURE None)",
          ai_answer.LAST_FAILURE is None)
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("ok", "KHONG_BIET."))
    check("marker kem dau cham -> None", ans is None, f"-> {ans!r}")

    # --- Loi HTTP / timeout / JSON ---
    print("=== LOI MANG + API ===")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("http403"))
    check("HTTP 403 -> None", ans is None)
    check("403 ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE == "Gemini HTTP 403",
          f"-> {ai_answer.LAST_FAILURE!r}")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("http429"))
    check("HTTP 429 -> None", ans is None)
    check("429 ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE == "Gemini HTTP 429")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("timeout"))
    check("timeout -> None (khong raise)", ans is None)
    check("timeout ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE is not None
          and "TimeoutError" in ai_answer.LAST_FAILURE,
          f"-> {ai_answer.LAST_FAILURE!r}")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("badjson"))
    check("JSON loi -> None", ans is None)
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("nocandidates"))
    check("khong co candidates -> None", ans is None)
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("ok", "   "))
    check("dap an rong -> None", ans is None)

    # --- Fallback model khi model chinh 503 ---
    print("=== FALLBACK MODEL ===")
    ai_answer.reset_usage()
    ans, stub = run_with_stub(UrlopenStub(
        "fail_first_503", "Pass giải nén là @bamon.gaming nha chú."))
    check("model chinh 503 -> fallback tra dap an",
          ans == "Pass giải nén là @bamon.gaming nha chú.", f"-> {ans!r}")
    check("fallback goi dung 2 model",
          len(stub.requests) == 2, f"-> {len(stub.requests)}")
    check("LAST_MODEL la model fallback",
          ai_answer.LAST_MODEL == ai_answer.MODELS[1],
          f"-> {ai_answer.LAST_MODEL!r}")
    check("fallback thanh cong thi LAST_FAILURE None",
          ai_answer.LAST_FAILURE is None)
    ai_answer.reset_usage()
    ans, stub = run_with_stub(UrlopenStub("all503"))
    check("tat ca model 503 -> None", ans is None)
    check("503 het luot thi thu du 3 model",
          len(stub.requests) == 3, f"-> {len(stub.requests)}")
    check("503 het luot ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE == "Gemini HTTP 503",
          f"-> {ai_answer.LAST_FAILURE!r}")
    check("that bai het thi LAST_MODEL None",
          ai_answer.LAST_MODEL is None)

    # --- Khong co key: khong goi HTTP ---
    print("=== KHONG CO KEY ===")
    ai_answer.reset_usage()
    stub = UrlopenStub("ok", "hello")
    ans, stub = run_with_stub(stub, key="")
    check("key rong -> None", ans is None)
    check("key rong thi khong goi HTTP", len(stub.requests) == 0)
    check("key rong ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE == "chua co GEMINI_API_KEY")

    # --- Cat dap an 800 ky tu ---
    print("=== CAT DAP AN ===")
    ai_answer.reset_usage()
    long_text = "x" * 1200
    ans, _ = run_with_stub(UrlopenStub("ok", long_text))
    check("dap an 1200 ky tu cat con 800",
          ans is not None and len(ans) == 800,
          f"-> len={len(ans) if ans else None}")
    ai_answer.reset_usage()
    ans, _ = run_with_stub(UrlopenStub("ok", "y" * 800))
    check("dap an dung 800 ky tu giu nguyen",
          ans is not None and len(ans) == 800)

    # --- Gioi han ngay ---
    print("=== GIOI HAN NGAY ===")
    ai_answer.reset_usage()
    stub = UrlopenStub("ok", "dap an")
    orig = urllib.request.urlopen
    urllib.request.urlopen = stub
    try:
        results = [ai_answer.ask_ai(QUESTION, SAMPLE_ENTRIES, KEY)
                   for _ in range(101)]
    finally:
        urllib.request.urlopen = orig
    check("100 luot dau deu co dap an",
          all(r == "dap an" for r in results[:100]))
    check("luot 101 -> None", results[100] is None)
    check("luot 101 khong goi HTTP",
          len(stub.requests) == 100, f"-> {len(stub.requests)}")
    check("het gioi han ghi LAST_FAILURE",
          ai_answer.LAST_FAILURE is not None
          and "100" in ai_answer.LAST_FAILURE,
          f"-> {ai_answer.LAST_FAILURE!r}")

    # Sang ngay moi: counter reset, goi lai duoc.
    orig_today = ai_answer._today_vn
    ai_answer._today_vn = lambda: "2999-01-02"
    try:
        ans, stub2 = run_with_stub(UrlopenStub("ok", "dap an moi"))
    finally:
        ai_answer._today_vn = orig_today
    check("sang ngay moi goi lai duoc", ans == "dap an moi",
          f"-> {ans!r}")

    print(f"\n{ TOTAL[0] - len(FAILS)}/{TOTAL[0]} PASS")
    if FAILS:
        print("FAILURES:", ", ".join(FAILS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
