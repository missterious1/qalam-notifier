#!/data/data/com.termux/files/usr/bin/bash
# One-time setup of the QALAM notifier on an Android phone (Termux).
set -e
DIR="$HOME/qalam"
RAW="https://raw.githubusercontent.com/missterious1/qalam-notifier/main"
echo "== Installing Python (takes 1-3 minutes) =="
pkg update -y >/dev/null 2>&1 || true
pkg install -y python >/dev/null 2>&1
pip install -q requests beautifulsoup4
mkdir -p "$DIR"
curl -fsSL "$RAW/qalam_notifier.py" -o "$DIR/qalam_notifier.py"
curl -fsSL "$RAW/start.sh" -o "$DIR/start.sh"
chmod +x "$DIR/start.sh"

echo
echo "== Your details (saved only on this phone) =="
read -r -p "QALAM username: " QU < /dev/tty
read -r -s -p "QALAM password (hidden while typing): " QP < /dev/tty; echo
read -r -p "ntfy topic name: " NT < /dev/tty
umask 077
{
  printf 'export QALAM_USER=%q\n' "$QU"
  printf 'export QALAM_PASS=%q\n' "$QP"
  printf 'export NTFY_TOPIC=%q\n' "$NT"
  printf 'export STATE_FILE=%q\n' "$DIR/state.json"
} > "$DIR/.env"

. "$DIR/.env"
echo
echo "== Sending a test notification to your phone =="
python "$DIR/qalam_notifier.py" --test
echo
echo "== Testing QALAM login =="
python "$DIR/qalam_notifier.py" --summary
echo
"$DIR/start.sh"
