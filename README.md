# Bot Discord FAQ

Bot tự động trả lời câu hỏi thường gặp trong server Discord, chạy độc lập
với bot chính. Đáp án lấy từ `faq.json` — 31 entry, đào từ lịch sử chat và
đã được chủ server duyệt tay. Bot ưu tiên khớp từ khoá với 1 entry FAQ;
không khớp thì hỏi AI (Gemini, chỉ trả lời dựa trên FAQ — xem mục "Trả lời
bằng AI" bên dưới), câu hỏi ngoài FAQ thì im lặng (không bịa đáp án).

- Chỉ trả lời ở các kênh cấu hình trong `ALLOWED_CHANNELS` (mặc định:
  chat-chung, chat-game, english-chat, #requests). Không trả lời DM, kênh
  tin tức, kênh ticket, kênh log admin.
- Cooldown 60 giây mỗi user (mỗi user tối đa 1 câu trả lời tự động mỗi phút).
- Mọi câu trả lời tự động được log vào `faq-bot.log` (JSON lines: thời gian,
  kênh, user, id FAQ, đoạn tin gốc) để kiểm tra sau.

## Cài đặt (làm 1 lần)

Làm trên trình duyệt (điện thoại/máy tính đều được):

**1. Tạo app bot**
- Mở https://discord.com/developers/applications → **New Application** →
  đặt tên, vd `Ba Mon FAQ` → Create.
- Vào mục **Bot** → **Reset Token** → copy token (giữ kín, không gửi qua chat).

**2. Bật Message Content intent (BẮT BUỘC)**
- Vẫn trong mục **Bot** → kéo xuống **Privileged Gateway Intents** → bật
  **MESSAGE CONTENT INTENT** → **Save Changes**. Không bật thì bot không đọc
  được nội dung tin nhắn và sẽ không trả lời gì cả.

**3. Mời bot vào server**
- Mục **OAuth2 → URL Generator** → tick scope **bot** → tick quyền
  **Send Messages** + **Read Message History** (+ **View Channel** nếu có) →
  mở link tạo ra, chọn server của bạn → Authorize.

**4. Clone repo + paste token vào máy chủ**
- SSH vào máy chủ Linux nơi bạn chạy bot:
  ```
  git clone https://github.com/Dogtor-san/discord-faq-bot.git ~/discord-faq-bot
  cd ~/discord-faq-bot
  cp .env.example .env
  nano .env
  ```
  Ghi token vừa copy vào dòng `DISCORD_TOKEN=...` rồi lưu (Ctrl+O, Enter, Ctrl+X).
- Cài dependencies:
  ```
  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
  ```

**5. Cài service (chạy 1 lần, cần sudo)**
```
sudo bash setup.sh
```
Script này chỉ copy service + enable, KHÔNG start bot.

**6. Chạy bot**
```
sudo systemctl start faq-bot
sudo systemctl status faq-bot
```
Xem log trực tiếp: `journalctl -u faq-bot -f`
Xem log các câu đã trả lời: `cat ~/discord-faq-bot/faq-bot.log`

## Quản lý database FAQ ngay trong Discord (chỉ chủ server)

Không cần sửa file — dùng 3 lệnh slash (chỉ chủ server dùng được, trả lời
riêng tư ephemeral). Thêm/xoá xong bot tự reload, trả lời ngay được:

- `/faq-add` — thêm 1 câu hỏi mới.
  - `cau_hoi`: các cụm trigger, cách nhau bằng dấu phẩy. Ít nhất 1 cụm
    phải có từ 2 từ trở lên (vd `pass giai nen`) — trigger toàn 1 từ
    thì bot không bao giờ trả lời entry đó.
  - `tra_loi`: đáp án (tối đa 1900 ký tự kể cả dòng English).
  - `tra_loi_en`: dòng English (không bắt buộc).
  - Ví dụ: `/faq-add` cau_hoi: `pass wifi quan, mat khau wifi` —
    tra_loi: `Pass wifi quán là 12345678 nha chú.` — bot trả id mới
    dạng `custom_001`.
- `/faq-list` — liệt kê mọi entry (id + trigger đầu + 60 ký tự đầu đáp án).
- `/faq-del` — xoá 1 entry theo id (xem id bằng `/faq-list`).

## Trả lời bằng AI (Google Gemini, gói miễn phí)

Khi matcher từ khoá không khớp câu hỏi nào, bot hỏi Gemini (model
chính `gemini-3.5-flash-lite`, fallback `gemini-3.7-flash` rồi
`gemini-3.8-flash` nếu model trước lỗi/quá tải) với toàn bộ FAQ làm
ngữ cảnh — AI chỉ được trả lời bằng thông tin có trong FAQ, không
bịa. Câu hỏi ngoài FAQ thì AI trả marker `KHONG_BIET` và bot vẫn im
lặng như cũ. Câu trả lời của AI được log vào `faq-bot.log` với
`"source": "ai"` để kiểm tra sau.

- **Bật AI:** tạo key miễn phí tại https://aistudio.google.com/apikey
  (đăng nhập Google → Create API Key — key AI Studio bắt đầu bằng
  `AIza`, key Google Cloud có thể bắt đầu bằng `AQ.` — cả hai đều
  dùng được), thêm dòng `GEMINI_API_KEY=<key>` vào file `.env`
  (cùng file với `DISCORD_TOKEN`), rồi restart:
  `sudo systemctl restart faq-bot`.
- **Chưa có key** thì AI tắt, bot chạy y như cũ (chỉ matcher) — log có
  dòng `AI: tat (chua co GEMINI_API_KEY)`.
- **Giới hạn:** tối đa 100 lượt gọi AI/ngày (giờ VN) — hết giới hạn
  thì bot tự quay về chỉ dùng matcher, không tốn tiền. Hết quota miễn
  phí của Google hoặc lỗi API thì bot cũng chỉ im lặng, không sập.
- Đáp án AI tối đa 800 ký tự, giọng bé–chú như đáp án FAQ, trả lời
  cùng ngôn ngữ với câu hỏi.

## Cập nhật code sau này

- Sửa `faq.json` trực tiếp vẫn được (thêm entry hoặc sửa
  `triggers`/`answer`), rồi restart: `sudo systemctl restart faq-bot`
  (lệnh /faq-add, /faq-del ở trên thì không cần restart).
- Muốn đổi kênh được trả lời hoặc cooldown: sửa `ALLOWED_CHANNELS` /
  `COOLDOWN_SECONDS` trong `bot.py`, rồi restart service.

## Chạy test

Không cần discord.py hay token — test chạy thuần Python:

```
python3 tests/test_matcher.py    # 114 test khớp từ khoá
python3 tests/test_faq_store.py  # 38 test thêm/xoá entry
python3 tests/test_ai.py         # 45 test AI fallback (mock API)
python3 tests/test_new8.py       # 20 test 8 entry duyệt 16/11/2026
```

Mỗi file exit 0 khi tất cả test pass.

## Ghi chú

- Bot này chỉ có 3 lệnh slash quản lý FAQ ở trên, không quản lý
  donate/ticket — mọi việc đó vẫn do bot chính phụ trách.
- Token bot FAQ KHÁC token bot chính — không dùng chung.

## License

MIT — xem file `LICENSE`.
