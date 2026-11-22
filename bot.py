#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Discord FAQ (bot THU HAI, rieng biet voi bot chinh "AI cua Ba Mon").

Tu dong tra loi cau hoi thuong gap trong server bang dap an da duyet
trong faq.json (dao tu lich su chat, user duyet 15/11/2026). Bot chi
tra loi khi chac chan khop 1 entry FAQ — khong chac thi im lang.

Lop du phong AI (ai_answer.py, Google Gemini goi mien phi): khi
matcher tu khoa khong khop cau hoi nao, bot hoi Gemini dua tren
toan bo FAQ lam ngu canh (grounded, khong bia). Cau hoi ngoai FAQ
thi model tra marker KHONG_BIET va bot van im lang. Can key
GEMINI_API_KEY trong .env — chua co key thi AI tat, bot chay y
nhu cu (chi matcher), toi da 100 luot goi AI/ngay.

Quan ly database ngay trong Discord (chi chu server):
  /faq-add  — them 1 cau hoi (trigger + dap an)
  /faq-list — liet ke moi entry
  /faq-del  — xoa 1 entry theo id
Them/xoa xong bot tu reload faq.json, khong can restart.

Cai dat:
  - Can Message Content intent (bat trong Developer Portal).
  - Token doc tu .env cung thu muc (DISCORD_TOKEN). Chua co token thi
    bot thoat ngay voi thong bao ro rang — xem README.md.
  - Chi tra loi trong 4 kenh chat cong khai (xem ALLOWED_CHANNELS).
    Khong tra loi DM, kenh tin tuc, kenh ticket, kenh log admin.
  - Cooldown 60 giay moi user.
  - Moi cau tra loi tu dong duoc log vao faq-bot.log (JSON lines).
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import ai_answer  # noqa: E402
from faq_store import (add_entry, chunk_lines, delete_entry,  # noqa: E402
                       format_entry_line, load_data)
from matcher import FAQMatcher, FAQ_PATH, normalize  # noqa: E402

ENV_PATH = os.path.join(BASE_DIR, ".env")
LOG_PATH = os.path.join(BASE_DIR, "faq-bot.log")

GUILD_ID = 1311631379787808799  # DONG NGHIEN GAME

# Kenh duoc phep tra loi (chat-chung, chat-game, english-chat, #requests).
ALLOWED_CHANNELS = {
    1399880372447219742,  # chat-chung
    1448160342898380910,  # chat-game
    1568153301751701596,  # english-chat
    1399880441322016829,  # #requests
}
COOLDOWN_SECONDS = 60
MIN_WORDS = 3  # tin ngan hon thi bo qua


def load_faq():
    """Nap (hoac nap lai) faq.json thanh matcher moi."""
    return FAQMatcher(FAQ_PATH)


def log_answer(channel, author, entry, triggers, excerpt):
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel.id,
        "channel": getattr(channel, "name", "?"),
        "user_id": author.id,
        "user": str(author),
        "faq_id": entry["id"],
        "faq_title": entry["title"],
        "triggers": triggers,
        "message": excerpt[:200],
    }
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def log_ai_answer(channel, author, question, answer):
    """Log 1 cau tra loi cua lop AI (nguon 'ai', co model)."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel.id,
        "channel": getattr(channel, "name", "?"),
        "user_id": author.id,
        "user": str(author),
        "source": "ai",
        "model": ai_answer.LAST_MODEL or ai_answer.MODEL,
        "question": question[:200],
        "answer": answer[:500],
    }
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def is_owner(interaction):
    guild = interaction.guild
    return guild is not None and guild.owner_id == interaction.user.id


async def refuse_non_owner(interaction):
    await interaction.response.send_message(
        "Lệnh này chỉ chủ server dùng được.", ephemeral=True)


class FAQBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        # commands.Bot (thay vi discord.Client) de co .tree cho slash
        # command — giong bot chinh. Khong co text command nao dang ky,
        # on_message ben duoi cung khong goi process_commands nen
        # prefix "!" khong co tac dung gi.
        super().__init__(command_prefix="!", intents=intents)
        self.matcher = load_faq()
        self.last_reply = {}  # user_id -> monotonic timestamp
        self._ai_err_logged = {}  # ly do loi AI -> monotonic (chong spam)
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if self.gemini_key:
            print(f"[bot] AI: bat (Gemini {ai_answer.MODEL}, "
                  f"fallback {', '.join(ai_answer.MODELS[1:])}, "
                  f"toi da {ai_answer.DAILY_LIMIT} luot/ngay)",
                  flush=True)
        else:
            print("[bot] AI: tat (chua co GEMINI_API_KEY)", flush=True)
        self.tree.add_command(faq_add_cmd)
        self.tree.add_command(faq_list_cmd)
        self.tree.add_command(faq_del_cmd)

    async def setup_hook(self):
        # Sync lenh ve guild (mau bot chinh: copy_global_to + sync).
        guild_obj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_obj)
        synced = await self.tree.sync(guild=guild_obj)
        print(f"[bot] Da sync {len(synced)} slash command ve guild "
              f"{GUILD_ID}: {[c.name for c in synced]}", flush=True)

    def reload_matcher(self):
        """Nap lai faq.json sau khi them/xoa. Loi thi giu matcher cu."""
        try:
            self.matcher = load_faq()
            return True
        except Exception as exc:  # noqa: BLE001 - bao loi, khong sap bot
            print(f"[faq] reload that bai: {exc}", flush=True)
            return False

    async def _try_ai(self, content):
        """Hoi AI khi matcher khong khop. Tra dap an hoac None.
        Goi API dong bo trong thread rieng de khong block event loop."""
        if not self.gemini_key:
            return None
        try:
            answer = await asyncio.to_thread(
                ai_answer.ask_ai, content, self.matcher.entries,
                self.gemini_key)
        except Exception as exc:  # noqa: BLE001 - khong bao gio sap bot
            print(f"[ai] loi khong mong doi: {exc}", flush=True)
            return None
        if answer is None:
            reason = ai_answer.LAST_FAILURE
            if reason:
                # Log loi AI, moi ly do toi da 1 lan/gio de khong spam.
                now = time.monotonic()
                if now - self._ai_err_logged.get(reason, 0) > 3600:
                    self._ai_err_logged[reason] = now
                    print(f"[ai] khong tra loi duoc: {reason}", flush=True)
        return answer

    async def on_ready(self):
        print(f"FAQ bot online: {self.user} (id {self.user.id})",
              flush=True)
        print(f"FAQ entries: {len(self.matcher.entries)} | "
              f"kenh cho phep: {sorted(ALLOWED_CHANNELS)}", flush=True)

    async def on_message(self, message):
        if message.author.bot or message.webhook_id is not None:
            return
        if message.guild is None:  # khong tra loi DM
            return
        if message.channel.id not in ALLOWED_CHANNELS:
            return
        content = message.content or ""
        if content.startswith("/"):  # lenh slash / lenh bot khac
            return
        if len(normalize(content).split()) < MIN_WORDS:
            return
        result = self.matcher.match(content)
        now = time.monotonic()
        last = self.last_reply.get(message.author.id, 0)
        if now - last < COOLDOWN_SECONDS:
            return
        if result is not None:
            reply_text = result["entry"]["answer"]
            entry = result["entry"]
        else:
            # Matcher khong khop: thu AI (grounded tren FAQ). AI tra
            # None (ngoai FAQ / loi / het gioi han) thi im lang.
            # Kiem tra cooldown truoc khi goi AI de tiet kiem quota.
            reply_text = await self._try_ai(content)
            if reply_text is None:
                return
            entry = None
        try:
            await message.reply(reply_text, mention_author=False)
        except discord.HTTPException as exc:
            print(f"[faq] reply that bai: {exc} | kenh="
                  f"#{getattr(message.channel, 'name', '?')} "
                  f"({message.channel.id}) | entry="
                  f"{entry['id'] if entry else 'AI'} | user="
                  f"{message.author}", flush=True)
            return
        self.last_reply[message.author.id] = now
        if entry is not None:
            log_answer(message.channel, message.author, entry,
                       result["triggers"], content)
            print(f"[faq] {entry['id']} -> {message.author} "
                  f"#{getattr(message.channel, 'name', '?')}", flush=True)
        else:
            log_ai_answer(message.channel, message.author, content,
                          reply_text)
            print(f"[faq-ai] -> {message.author} "
                  f"#{getattr(message.channel, 'name', '?')}", flush=True)


@app_commands.command(
    name="faq-add",
    description="[Chủ server] Thêm 1 câu hỏi vào database FAQ")
@app_commands.describe(
    cau_hoi="Các cụm trigger, cách nhau bằng dấu phẩy "
            "(vd: pass giai nen, mat khau rar)",
    tra_loi="Đáp án bot sẽ trả lời",
    tra_loi_en="Dòng English (không bắt buộc)")
@app_commands.default_permissions(manage_roles=True)
async def faq_add_cmd(interaction: discord.Interaction, cau_hoi: str,
                      tra_loi: str, tra_loi_en: str = ""):
    if not is_owner(interaction):
        await refuse_non_owner(interaction)
        return
    entry, err = add_entry(FAQ_PATH, cau_hoi, tra_loi, tra_loi_en)
    if err:
        await interaction.response.send_message(
            f"❌ Không thêm được: {err}", ephemeral=True)
        return
    bot = interaction.client
    if not bot.reload_matcher():
        await interaction.response.send_message(
            "⚠️ Đã ghi vào file nhưng reload matcher lỗi — bot vẫn dùng "
            "database cũ. Báo lại để kiểm tra.", ephemeral=True)
        return
    shown = entry["answer"]
    if len(shown) > 800:
        shown = shown[:800] + "…"
    await interaction.response.send_message(
        "✅ Đã thêm entry mới (bot đã reload, trả lời ngay được):\n"
        f"**ID:** `{entry['id']}`\n"
        f"**Trigger:** {', '.join(entry['triggers'])}\n"
        f"**Đáp án:** {shown}",
        ephemeral=True)


@app_commands.command(
    name="faq-list",
    description="[Chủ server] Liệt kê mọi câu hỏi trong database FAQ")
@app_commands.default_permissions(manage_roles=True)
async def faq_list_cmd(interaction: discord.Interaction):
    if not is_owner(interaction):
        await refuse_non_owner(interaction)
        return
    data = load_data(FAQ_PATH)
    entries = data["entries"]
    if not entries:
        await interaction.response.send_message(
            "Database FAQ hiện trống.", ephemeral=True)
        return
    lines = [f"**Database FAQ — {len(entries)} entry:**"]
    lines += [format_entry_line(e) for e in entries]
    chunks = chunk_lines(lines)
    await interaction.response.send_message(chunks[0], ephemeral=True)
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk, ephemeral=True)


@app_commands.command(
    name="faq-del",
    description="[Chủ server] Xoá 1 câu hỏi khỏi database FAQ")
@app_commands.describe(
    id="ID entry cần xoá (xem bằng /faq-list)")
@app_commands.default_permissions(manage_roles=True)
async def faq_del_cmd(interaction: discord.Interaction, id: str):
    if not is_owner(interaction):
        await refuse_non_owner(interaction)
        return
    removed = delete_entry(FAQ_PATH, id)
    if removed is None:
        await interaction.response.send_message(
            f"❌ Không tìm thấy entry id `{id.strip()}`.",
            ephemeral=True)
        return
    bot = interaction.client
    if not bot.reload_matcher():
        await interaction.response.send_message(
            "⚠️ Đã xoá khỏi file nhưng reload matcher lỗi — bot vẫn dùng "
            "database cũ. Báo lại để kiểm tra.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"✅ Đã xoá entry `{removed['id']}` "
        f"(trigger đầu: {removed['triggers'][0] if removed['triggers'] else '—'}).",
        ephemeral=True)


def main():
    load_dotenv(ENV_PATH)
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        print("LOI: chua co DISCORD_TOKEN.", file=sys.stderr)
        print(f"Hay tao file {ENV_PATH} voi dong:", file=sys.stderr)
        print("  DISCORD_TOKEN=<token cua bot FAQ>",
              file=sys.stderr)
        print("Lay token: https://discord.com/developers/applications "
              "-> app bot FAQ -> Bot -> Token (Reset Token).",
              file=sys.stderr)
        print("Xem huong dan day du trong README.md cung thu muc.",
              file=sys.stderr)
        sys.exit(1)
    bot = FAQBot()
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("LOI: token khong dung hoac da het han. Kiem tra lai "
              f"DISCORD_TOKEN trong {ENV_PATH}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
