#!/data/data/com.termux/files/usr/bin/bash
# One-time setup of the QALAM notifier on an Android phone (Termux).
set -e
DIR="$HOME/qalam"
RAW="https://raw.githubusercontent.com/missterious1/qalam-notifier/main"
echo "== Installing Python (takes 1-3 minutes) =="
pkg update -y >/dev/null 2>&1 || true
pkg install -y python >/dev/null
pip install -q requests beautifulsoup4
mkdir -p "$DIR"
curl -fsSL "$RAW/qalam_notifier.py" -o "$DIR/qalam_notifier.py"
curl -fsSL "$RAW/start.sh" -o "$DIR/start.sh"
chmod +x "$DIR/start.sh"

echo
echo "== Your details (saved only on this phone) =="
read -r -p "QALAM username: " QU
read -r -s -p "QALAM password (hidden while typing): " QP; echo
read -r -p "ntfy topic name: " NT
umask 077
cat > "$DIR/.env" <<EOT
export QALAM_USER='$QU'
export QALAM_PASS='$QP'
export NTFY_TOPIC='$NT'
export STATE_FILE='$DIR/state.json'
EOT

. "$DIR/.env"
echo
echo "== Sending a test notification to your phone =="
python "$DIR/qalam_notifier.py" --test
echo
echo "== Testing QALAM login =="
python "$DIR/qalam_notifier.py" --summary
echo
"$DIR/start.sh"
