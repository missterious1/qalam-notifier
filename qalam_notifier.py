#!/usr/bin/env python3
"""
QALAM marks notifier.

Logs in to QALAM (NUST's LMS), reads the gradebook of every course on your
dashboard, compares it with the last run, and sends a push notification to
your phone (via ntfy.sh) when marks appear or change.

Config (environment variables):
  QALAM_USER      your QALAM login (CMS ID / username)
  QALAM_PASS      your QALAM password
  NTFY_TOPIC      a long random topic name, e.g. qalam-x7f3k9q2m1  (subscribe to it in the ntfy app)
  NTFY_SERVER     optional, default https://ntfy.sh
  STATE_FILE      optional, default state.json

Usage:
  python qalam_notifier.py            # check once, notify on changes
  python qalam_notifier.py --test     # send a test notification only
  python qalam_notifier.py --summary  # log in and list courses found (no marks shown)
  python qalam_notifier.py --dump     # log in and print what was scraped (debugging)
  python qalam_notifier.py --loop 600 # check every 600 seconds forever
"""
import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://qalam.nust.edu.pk"
LOGIN_URL = f"{BASE}/web/login"
DASHBOARD_URL = f"{BASE}/student/dashboard"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

STATE_FILE = os.environ.get("STATE_FILE", "state.json")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")


# ----------------------------------------------------------------- notify ---
def notify(title, message, priority="high", tags="mortar_board"):
    if not NTFY_TOPIC:
        print("[notify] NTFY_TOPIC not set; would have sent:", title, "|", message)
        return
    r = requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8"), "Priority": priority,
                 "Tags": tags, "Click": DASHBOARD_URL},
        timeout=20,
    )
    r.raise_for_status()
    print("[notify] sent:", title)


# ------------------------------------------------------------------ login ---
def login(user, password):
    s = requests.Session()
    s.headers.update(HEADERS)
    page = s.get(LOGIN_URL, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, "html.parser")
    form = soup.find("form", attrs={"action": re.compile("login")}) or soup.find("form")
    data = {}
    if form:  # keep hidden fields such as csrf_token / redirect
        for inp in form.find_all("input"):
            if inp.get("name"):
                data[inp["name"]] = inp.get("value", "")
    data["login"] = user
    data["password"] = password
    action = urljoin(LOGIN_URL, form.get("action")) if form and form.get("action") else LOGIN_URL
    r = s.post(action, data=data, timeout=30)
    r.raise_for_status()
    if "/web/login" in r.url and ('name="password"' in r.text):
        raise RuntimeError("Login failed: check QALAM_USER / QALAM_PASS")
    return s


# --------------------------------------------------------------- scraping ---
def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def find_courses(s):
    """Return {course_id: course_name} from the student dashboard."""
    r = s.get(DASHBOARD_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    courses = {}
    for a in soup.find_all("a", href=True):
        m = re.search(r"/student/course/[a-z_]+/(\d+)", a["href"])
        if m:
            cid = m.group(1)
            name = clean(a.get_text(" "))
            if name and (cid not in courses or len(name) > len(courses[cid])):
                courses[cid] = name[:80]
            courses.setdefault(cid, f"Course {cid}")
    return courses


def scrape_gradebook(s, cid):
    """Return a list of text rows from a course's gradebook page.

    Generic on purpose: every table row on the page becomes one line like
    'Quiz 1 | 8 | 10 | ...'. Any new or changed line counts as a marks update.
    """
    url = f"{BASE}/student/course/gradebook/{cid}"
    r = s.get(url, timeout=30)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("table tr"):
        cells = [clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c]
        if cells and tr.find("td"):  # skip pure header rows
            rows.append(" | ".join(cells))
    return rows


def snapshot(s):
    data = {}
    for cid, name in find_courses(s).items():
        rows = scrape_gradebook(s, cid)
        data[cid] = {"name": name, "rows": rows}
    return data


# ------------------------------------------------------------------ state ---
def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1, ensure_ascii=False, sort_keys=True)


def diff(old, new):
    """Yield (course_name, [new_or_changed_rows])."""
    for cid, cur in new.items():
        before = set(old.get(cid, {}).get("rows", []))
        added = [r for r in cur["rows"] if r not in before]
        if added:
            yield cur["name"], added


# ------------------------------------------------------------------- main ---
def check_once(user, password):
    s = login(user, password)
    new = snapshot(s)
    if not new:
        print("No courses found on dashboard; QALAM layout may have changed. Run with --dump.")
        return
    old = load_state()
    if old is None:
        save_state(new)
        n = sum(len(c["rows"]) for c in new.values())
        print(f"First run: saved baseline ({len(new)} courses, {n} rows). No notification sent.")
        notify("QALAM notifier active",
               f"Watching {len(new)} courses. You'll be pinged when new marks appear.",
               priority="default", tags="white_check_mark")
        return
    changes = list(diff(old, new))
    for course, rows in changes:
        body = "\n".join(rows[:8]) + (f"\n…and {len(rows) - 8} more" if len(rows) > 8 else "")
        notify(f"New marks: {course}", body)
    save_state(new)
    print(time.strftime("%Y-%m-%d %H:%M"), f"Checked {len(new)} courses, {len(changes)} with updates.", flush=True)


def main():
    args = sys.argv[1:]
    if "--test" in args:
        notify("QALAM notifier test", "If you see this, notifications work 🎉")
        return
    user, password = os.environ.get("QALAM_USER"), os.environ.get("QALAM_PASS")
    if not user or not password:
        sys.exit("Set QALAM_USER and QALAM_PASS environment variables.")
    if "--summary" in args:
        s = login(user, password)
        snap = snapshot(s)
        print(f"Login OK. Found {len(snap)} courses:")
        for c in snap.values():
            print(f"  - {c['name']}: {len(c['rows'])} marks rows")
        return
    if "--dump" in args:
        s = login(user, password)
        print(json.dumps(snapshot(s), indent=2, ensure_ascii=False))
        return
    if "--loop" in args:
        interval = int(args[args.index("--loop") + 1]) if len(args) > args.index("--loop") + 1 else 600
        while True:
            try:
                check_once(user, password)
            except Exception as e:  # keep looping through network hiccups
                print(time.strftime("%Y-%m-%d %H:%M"), "Error:", e, flush=True)
            time.sleep(interval)
    check_once(user, password)


if __name__ == "__main__":
    main()
