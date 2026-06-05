#!/usr/bin/env python3
"""
Players Era 8 ticket monitor - WVU vs. Auburn, Nov 17, 2026, Las Vegas.
Checks the official pages and sends a phone push (via ntfy.sh) the moment
ticket-on-sale signals appear next to a "Players Era" mention.
"""
import os, re, json
from urllib.request import Request, urlopen
from datetime import datetime, timezone

TARGETS = [
    ("WVU MBB schedule", "https://wvusports.com/sports/mens-basketball/schedule"),
    ("WVU MBB news",     "https://wvusports.com/sports/mens-basketball/news"),
    ("Players Era site", "https://www.playersera.com/"),
    ("AXS - Michelob ULTRA Arena",
     "https://www.axs.com/venues/110363/michelob-ultra-arena-at-mandalay-bay-tickets"),
]
TICKET_SIGNALS = [
    "buy tickets","get tickets","tickets on sale","on sale now","purchase tickets",
    "tickets available","single session","single-session","buy now","presale",
    "on-sale","find tickets","axs.com","ticketmaster","/tickets",
]
EVENT_ANCHOR = "players era"
WINDOW_BEFORE, WINDOW_AFTER = 150, 600

NTFY_TOPIC  = os.environ.get("NTFY_TOPIC", "")            # set as a GitHub secret
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
STATE_FILE  = os.environ.get("STATE_FILE", "state.json")
UA = "Mozilla/5.0 (compatible; TicketMonitor/1.0; +knack-build.com)"

def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def visible_text(doc):
    doc = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", doc)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", doc)).lower()

def signals_near_event(text):
    found = set()
    for m in re.finditer(re.escape(EVENT_ANCHOR), text):
        w = text[max(0, m.start()-WINDOW_BEFORE): m.end()+WINDOW_AFTER]
        for s in TICKET_SIGNALS:
            if s in w:
                found.add(s)
    return found

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)

def push(title, message, click_url):
    if not NTFY_TOPIC:
        print("[dry run] no NTFY_TOPIC set. Would push:", title, "|", message)
        return
    req = Request(f"{NTFY_SERVER}/{NTFY_TOPIC}",
                  data=message.encode("utf-8"),
                  headers={"Title": title, "Priority": "urgent",
                           "Tags": "tickets", "Click": click_url})
    try:
        urlopen(req, timeout=30)
        print("Push sent.")
    except Exception as e:
        print("[warn] push failed:", e)

def main():
    state = load_state(); hits = []
    for label, url in TARGETS:
        try:
            sigs = signals_near_event(visible_text(fetch(url)))
        except Exception as e:
            print(f"[warn] {label}: {e}"); continue
        prev = set(state.get(url, {}).get("signals", []))
        fresh = sigs - prev
        if fresh:
            hits.append((label, url, sorted(fresh)))
        state[url] = {"signals": sorted(sigs),
                      "checked": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    save_state(state)
    if hits:
        click = hits[0][1]
        body = ("Possible ticket activity:\n" +
                "\n".join(f"- {l}: {', '.join(s)}" for l, u, s in hits) +
                "\nWVU vs Auburn - Players Era 8 - Nov 17, 2026.")
        push("WVU / Players Era tickets may be LIVE", body, click)
    else:
        print(datetime.now().strftime("%Y-%m-%d %H:%M"), "- no new signals.")

if __name__ == "__main__":
    main()
