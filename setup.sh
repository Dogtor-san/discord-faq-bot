#!/usr/bin/env bash
# Cai dat service faq-bot — chay 1 LAN voi sudo (sau khi code da co
# san trong ~/discord-faq-bot). Chi enable service, KHONG start
# (can paste token vao .env truoc).
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Chay voi sudo: sudo bash $0"
  exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Cai service faq-bot tu $DIR ..."

if [ ! -x "$DIR/venv/bin/python" ]; then
  echo "LOI: chua co venv ($DIR/venv). Cai deps truoc:"
  echo "  cd $DIR && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

cp "$DIR/faq-bot.service" /etc/systemd/system/faq-bot.service
systemctl daemon-reload
systemctl enable faq-bot

echo "Xong. Service da enable nhung CHUA start."
if [ ! -f "$DIR/.env" ]; then
  echo "CANH BAO: chua co file $DIR/.env (chua co token)."
  echo "Hay tao .env voi dong DISCORD_TOKEN=<token bot FAQ> roi chay:"
else
  echo "Da co file .env. De chay bot, chay:"
fi
echo "  sudo systemctl start faq-bot"
echo "Kiem tra: sudo systemctl status faq-bot"
echo "Xem log:  journalctl -u faq-bot -f"
