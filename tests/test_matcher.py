#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test matcher cua bot FAQ.
  - POSITIVE: cau hoi mau THAT trong faq-draft.md (3 cau/cum x 18 cum
    + 5 cau le) — moi cau phai match dung entry cua no.
  - PARAPHRASE: cach hoi khac (user co the go khac di) — phai match
    dung entry.
  - NEGATIVE: small-talk / cau gameplay / cau phat bieu / trigger 1 tu
    don le — phai match KHONG entry nao (bot im lang).
  - NORMALIZE: kiem tra chuan hoa tieng Viet.
Chay: python3 test_matcher.py (khong can discord.py).
Exit 0 neu tat ca pass, 1 neu co fail.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matcher import FAQMatcher, normalize  # noqa: E402

M = FAQMatcher()

# (cau hoi, entry id mong doi) — trich nguyen van tu faq-draft.md
POSITIVE = [
    ("hookshot rồi longshot nữa hả", "hookshot_longshot"),
    ("Hookshoot đổi tên thành longshoot hả ae", "hookshot_longshot"),
    ("hiện tại Longshot ngon hơn hay NX2 ae nhỉ", "hookshot_longshot"),
    ("sao mình cũng bị blackscreen", "crash_blackscreen"),
    ("cài hookshot bị lỗi này là sao vậy ae", "crash_blackscreen"),
    ("Ae ai bị crash lúc load boss ko", "crash_blackscreen"),
    ("mình xin link zelda botw version 1.9.0 nhé", "link_game"),
    ("ai còn fe fortuna weave recomp gửi mình với", "link_game"),
    ("Would anyone be so kind as to send me Pokopia in .nup format?",
     "link_game"),
    ("why is there 3 parts / are they all important?", "extract_parts"),
    ("After extracting all three game files I still only see one file "
     "that shows as 9 GB. How do I get the 24 GB one?", "extract_parts"),
    ("Cho hỏi sao em giải nén các file .nup Part1.2.3.4.5 bấm giải nén "
     "xong nó không cho lưu", "extract_parts"),
    ("how do I do actual full screen with nxnavi and how do I get "
     "performance metrics to show up?", "graphics_settings"),
    ("Which frame gen / upscaling are you using?", "graphics_settings"),
    ("làm sao để bật dlss5 nhỉ", "graphics_settings"),
    ("ủa cái bloom của Oot tải ở đâu z ae", "oot_graphics_bugs"),
    ("có bác nào biết fix lỗi 1 vài thứ như thùng, hàng rào bị tàn hình ko",
     "oot_graphics_bugs"),
    ("Cơ mà nó vẫn lỗi chớp đen", "oot_graphics_bugs"),
    ("tui tải laucher và file game về ròi h làm gì nữa vậy mấy ông Zelda BOTW",
     "install_guide"),
    ("thực sự thì tôi không hiểu làm sao để chơi được duskblood ông ạ",
     "install_guide"),
    ("lên clip hướng dẫn tải bản longshot đc ko ad... chưa bt cài như nào",
     "install_guide"),
    ("ae ai chỉ giúp cho em cách VH game zela remake với ạ", "viet_hoa"),
    ("ae nào còn file VH, cho mình xin với", "viet_hoa"),
    ("bro có biêt copy viet hóa game zelda oot vào hookshot ko?", "viet_hoa"),
    ("link dlc demon soul remake bị lỗi ạ", "broken_link"),
    ("the copying never works for me in google drive i keep getting an error",
     "broken_link"),
    ("Sao em k tải đc Ocarina of Time trên link bác Ba Mon nhỉ",
     "broken_link"),
    ("pass giải nén 5 part của FEFW là gì á mấy sếp", "extract_password"),
    ("pass giải nén pokopia là gì v ad", "extract_password"),
    ("also, where to find password for unzip?", "extract_password"),
    ("sao mình thoát game vào lại thì nó lại build shader lại từ đầu vậy",
     "shader_build"),
    ("mik phai setting hnu nao de no tu build hay no build trong qua "
     "trinh choi a?", "shader_build"),
    ("Giờ làm sao để build được hết shader trước thì chơi ngon luôn",
     "shader_build"),
    ("game bạn chia sẻ đã là bản v1.9.0 chưa?", "botw_version"),
    ("b có riêng update v1.9.0.nsp không? mình tải trên mạng ghi v1.9.0, "
     "nhưng tải về là v1.6.0", "botw_version"),
    ("I downloaded savage wind and the game but it says it needs to be updated",
     "botw_version"),
    ("Vậy chơi giả lập, b có hướng dẫn không?", "emulator_vs_port"),
    ("Giả lập có 120fps ko b?", "emulator_vs_port"),
    ("bác dùng giả lập nào vậy?", "emulator_vs_port"),
    ("how i install the bananza dlc after i installed the game",
     "dlc_update_install"),
    ("when the DLC comes would this mean i need to redownload a brand new "
     "game with the dlc... or will there just be like a installation patch",
     "dlc_update_install"),
    ("giờ có base game với dlc đều file nup hết thì làm sao bỏ vào được thế",
     "dlc_update_install"),
    ("Is there any update on stable graphics for Zelda?", "new_update"),
    ("Have there been any new releases for the OoT ROM or just the emulator?",
     "new_update"),
    ("update ko ae nhỉ? tưởng bản 5.3 mới rồi", "new_update"),
    ("2 file bin làm gì vậy", "amiibo"),
    ("Bác cho mình hỏi cách tải Amiibo của zelda totk được không", "amiibo"),
    ("bản ocarina của hookshot mình quét amiibo như video mà nó hiện dấu "
     "tròn gạch chéo chứ không rơi đồ là sao vậy bác", "amiibo"),
    ("Bro có biết link nào tải mod cheat, mod hiện tay cầm xbox,... ?",
     "mods_cheats"),
    ("hi, where can i get mods and cheats for legends za", "mods_cheats"),
    ("Phải tạo folder mod à? Hãy như nào bác?", "mods_cheats"),
    ("14600kf 4070s chơi nổi ko nhỉ", "can_i_run_it"),
    ("Astro bot chơi tay cầm ko có motioncontrol đc ko nhỉ", "can_i_run_it"),
    ("ae nào có cách tối ưu tarkov không", "can_i_run_it"),
    ("Mình donate rồi mà chưa đc cấp role nhỉ", "donate_no_role"),
    ("Cho e hỏi kytyps5 chơi demon soul remake có cách nào hiện trophy không ạ",
     "kyty_trophy"),
    ("cho mình hỏi file prod.keys có cần giải nén để chạy file TOTK setup k ạ",
     "prod_keys"),
    ("tình hình là mình cài game bị lỗi 2 lần rồi", "install_error_drive"),
    ("Đang build giữa chừng tắt máy xong build tiếp được không",
     "build_resume"),
]

# Cach hoi khac (paraphrase) — van phai match dung entry.
PARAPHRASE = [
    ("cho mình hỏi pass giải nén là gì", "extract_password"),
    ("có update mới không mọi người", "new_update"),
    ("game bị crash hoài", "crash_blackscreen"),
    ("máy mình 3050 chơi nổi không", "can_i_run_it"),
    ("cho mình xin link game", "link_game"),
    ("tải mod ở đâu vậy", "mods_cheats"),
    ("cài việt hoá sao vậy", "viet_hoa"),
    ("link tải bị lỗi rồi", "broken_link"),
    ("mình donate rồi sao chưa có role vậy", "donate_no_role"),
    ("hookshot sập rồi à mọi người", "hookshot_longshot"),
    ("longshot là gì vậy ae", "hookshot_longshot"),
    ("làm sao bật fullscreen vậy", "graphics_settings"),
    ("có cách nào hiện trophy trên kytyps5 không", "kyty_trophy"),
    ("cho mình hỏi tải amiibo ở đâu", "amiibo"),
    ("cài dlc bananza như nào vậy", "dlc_update_install"),
    ("giải nén part 1 bằng gì vậy", "extract_parts"),
    ("sao game cứ build shader hoài vậy", "shader_build"),
    ("botw phải bản 1.9.0 mới chơi được à", "botw_version"),
    ("chơi giả lập hay port pc ngon hơn", "emulator_vs_port"),
    ("tải game về rồi làm gì nữa", "install_guide"),
    ("đồ vật bị tàng hình fix sao vậy", "oot_graphics_bugs"),
]

# Phai match KHONG entry nao.
NEGATIVE = [
    "anh chơi ko ạ?",
    "video bị gỡ luôn r hả a",
    "làm sao để cho cha này xuống",
    "hố sụt này có báu vật gì không",
    "hello mọi người",
    "game này hay quá",
    "mình mới chơi tới đoạn Saria",
    "ai chơi chung không",
    "cho mình hỏi làm sao để qua được chỗ này",
    "pass qua đoạn này đi",
    "link này hay nè",
    "update game đi anh",
    "dlss ngon quá",
    "mod này đẹp",
    "shader đẹp vãi",
    "hookshot chơi ngon",
    "longshot ngon",
    "cảm ơn anh",
    "cho em xin link discord",
    "tắt máy đi ngủ đây",
    "máy mình 3060 chơi ngon lắm",
    "có ai biết chỗ này đi đâu không",
    "chơi game vui quá mọi người ơi",
    "khi nào anh ra video mới",
    "cho mình hỏi pass wifi quán này là gì",
    "ai có link server discord khác không",
    "mình thích chơi game này lắm",
    "tối nay có ai online không",
]

NORMALIZE_CASES = [
    ("Tiếng Việt có dấu", "tieng viet co dau"),
    ("prod.keys", "prod keys"),
    ("v1.9.0", "v1 9 0"),
    ("Đường Đèo", "duong deo"),
    ("  NHIỀU   khoảng   trắng  ", "nhieu khoang trang"),
    ("HookShot v2.2.0-rc1!", "hookshot v2 2 0 rc1"),
]


def main():
    fails = 0
    total = 0

    print("=== NORMALIZE ===")
    for src, want in NORMALIZE_CASES:
        total += 1
        got = normalize(src)
        ok = got == want
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {src!r} -> {got!r}"
              + ("" if ok else f" (muon {want!r})"))

    print(f"=== POSITIVE ({len(POSITIVE)} cau mau that) ===")
    for q, want in POSITIVE:
        total += 1
        got = M.match_id(q)
        ok = got == want
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} [{want}] {q[:60]}"
              + ("" if ok else f" -> match {got}"))

    print(f"=== PARAPHRASE ({len(PARAPHRASE)}) ===")
    for q, want in PARAPHRASE:
        total += 1
        got = M.match_id(q)
        ok = got == want
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} [{want}] {q[:60]}"
              + ("" if ok else f" -> match {got}"))

    print(f"=== NEGATIVE ({len(NEGATIVE)} — phai im lang) ===")
    for q in NEGATIVE:
        total += 1
        got = M.match_id(q)
        ok = got is None
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {q[:60]}"
              + ("" if ok else f" -> match {got} (SAI, phai im lang)"))

    print(f"\nTONG: {total - fails}/{total} pass, {fails} fail")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
