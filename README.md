# QALAM Marks Notifier

Sends a push notification to your phone when new marks show up on QALAM.

## 1. Phone setup (2 minutes)
1. Install the **ntfy** app (Play Store / App Store, free, no account needed).
2. Tap **+**, subscribe to a topic with a long random name, e.g. `qalam-x7f3k9q2m1zz`.
   Anyone who knows the topic name can read it, so don't use something guessable.

## 2. Run it free on GitHub Actions (every 15 min, no PC needed)
1. Create a **private** GitHub repo and upload these files (state.json will hold your marks, so keep it private).
2. Repo → Settings → Secrets and variables → Actions → add:
   - `QALAM_USER`: your QALAM username
   - `QALAM_PASS`: your QALAM password
   - `NTFY_TOPIC`: the topic from step 1
3. Actions tab → "Check QALAM marks" → **Run workflow**.
   The first run saves a baseline and sends "QALAM notifier active". Each later run notifies you about new or changed marks.

## Or run it on your own PC / laptop
```
pip install -r requirements.txt
export QALAM_USER=... QALAM_PASS=... NTFY_TOPIC=...
python qalam_notifier.py --test        # check the notification arrives
python qalam_notifier.py --dump        # check it actually reads your courses and marks
python qalam_notifier.py --loop 600    # check every 10 minutes
```

## Troubleshooting
- **No courses found / empty rows**: run `--dump` and look at the output. If QALAM uses different
  URLs than `/student/dashboard` and `/student/course/gradebook/<id>`, edit `DASHBOARD_URL`
  or `scrape_gradebook()` in `qalam_notifier.py`.
- **Login fails / timeout on GitHub Actions**: QALAM may block foreign IPs. Run it locally in Pakistan
  instead (PC, Raspberry Pi, or Termux on an old Android phone).
