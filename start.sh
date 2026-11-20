#!/data/data/com.termux/files/usr/bin/bash
# Start (or restart) the QALAM checker in the background.
DIR="$HOME/qalam"
. "$DIR/.env"
pkill -f "qalam_notifier.py --loop" 2>/dev/null
termux-wake-lock 2>/dev/null
nohup python "$DIR/qalam_notifier.py" --loop 600 >> "$DIR/log.txt" 2>&1 &
echo "QALAM checker is running in the background (checks every 10 minutes)."
echo "To see what it's doing: tail $DIR/log.txt"
