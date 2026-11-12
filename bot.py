import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BOT_NAME = "Ring_Wraithed"
# Dedicated WoW: Forever Blue Tracker news feeds are authoritative: every item
# in these feeds belongs to Forever, even if its title omits the game name.
# Keep the general Blue Tracker feeds as a secondary source for forum topics;
# those entries must still pass the Forever keyword filter.
FEEDS = [
    ("https://www.wowhead.com/forever/blue-tracker?rss=", True),
    ("https://www.wowhead.com/forever/blue-tracker/news/us?rss=", True),
    ("https://www.wowhead.com/forever/blue-tracker/news/eu?rss=", True),
    ("https://www.wowhead.com/blue-tracker?rss=", False),
    ("https://www.wowhead.com/blue-tracker/news?rss=", False),
]
STATE_FILE = Path("state.json")
DRAFT_DIR = Path("drafts")
MAX_HISTORY = 1000
MAX_POST_LENGTH = 280
FOREVER_TERMS = (
    "wow: forever", "wow forever",
    "world of warcraft: forever", "world of warcraft forever",
)
QUESTIONS = [
    "Which WoW: Forever class would you recommend to a brand-new player?",
    "What's the most underrated class in WoW: Forever?",
    "Alliance or Horde: which side are you choosing?",
    "What's your favorite leveling zone, and why?",
    "Which dungeon do you never get tired of running?",
    "What's the toughest boss you've faced?",
    "Which class deserves more attention?",
    "What's your favorite WoW: Forever memory?",
    "If you could change one thing, what would it be?",
    "What's your favorite race and class combination?",
    "Do you prefer solo play or grouping up?",
    "What's your favorite profession?",
    "Which dungeon should every player experience?",
    "What's your best leveling tip?",
    "What feature would you most like to see added?",
    "What's the most satisfying class to play?",
    "Do you prefer PvE or PvP?",
    "What's your best advice for a new player?",
    "What makes WoW: Forever special to you?",
    "Which zone brings back the most nostalgia?",
    "What's your favorite questline?",
    "Which class would you never abandon?",
    "What keeps you coming back to Azeroth?",
    "What's your most memorable in-game moment?",
    "What's your favorite dungeon group composition?",
    "Which profession do you enjoy most?",
    "What's one thing every new player should know?",
    "What's your personal goal in WoW: Forever?",
    "What's the best item you've ever looted?",
    "What's one community moment you'll always remember?",
]

def load_state():
    if not STATE_FILE.exists():
        return {"drafted_news": [], "question_index": 0}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot safely read {STATE_FILE}: {exc}") from exc
    # Preserve the old bot's seen list: those items were already drafted before,
    # even though they were never confirmed as published.
    drafted = state.get("drafted_news", state.get("seen", []))
    state["drafted_news"] = drafted[-MAX_HISTORY:]
    state.setdefault("question_index", 0)
    return state

def save_state(state):
    temp_file = STATE_FILE.with_suffix(".json.tmp")
    temp_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temp_file.replace(STATE_FILE)

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<(script|style).*?>.*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def get_entries(feed_url, forever_scoped=False):
    request = urllib.request.Request(feed_url, headers={"User-Agent": "RingWraithedNewsBot/2.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())
    entries = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        description = clean_text(item.findtext("description"))
        pub_date = item.findtext("pubDate") or ""
        if title and link.startswith(("https://", "http://")):
            entries.append({"title": title, "link": link, "id": guid or link,
                            "description": description, "date": pub_date,
                            "forever_scoped": forever_scoped})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//a:entry", ns):
        title = clean_text(item.findtext("a:title", namespaces=ns))
        link_node = item.find("a:link", ns)
        link = link_node.get("href", "") if link_node is not None else ""
        guid = item.findtext("a:id", namespaces=ns) or link
        description = clean_text(item.findtext("a:summary", namespaces=ns))
        pub_date = (item.findtext("a:published", namespaces=ns)
                    or item.findtext("a:updated", namespaces=ns) or "")
        if title and link.startswith(("https://", "http://")):
            entries.append({"title": title, "link": link, "id": guid or link,
                            "description": description, "date": pub_date,
                            "forever_scoped": forever_scoped})
    return entries

def is_forever_story(entry):
    text = (entry.get("title", "") + " " + entry.get("description", "")).lower()
    return any(term in text for term in FOREVER_TERMS)

def make_news_post(entry):
    title = entry["title"].strip()
    lower = title.lower()
    if "hotfix" in lower:
        headline = "🚨 WoW: Forever hotfix"
    elif "class" in lower or "tuning" in lower:
        headline = "⚔️ WoW: Forever class update"
    elif "dungeon" in lower or "loot" in lower:
        headline = "🔥 WoW: Forever update"
    else:
        headline = "🔵 Blizzard Blue post for WoW: Forever"
    suffix = f"\n\n{entry['link']}\n#WoWForever"
    prefix = f"{headline}\n\n"
    available = MAX_POST_LENGTH - len(prefix) - len(suffix)
    if available < 20:
        raise ValueError("Source URL leaves too little room for a readable post.")
    if len(title) > available:
        title = title[:max(0, available - 1)].rstrip() + "…"
    post = prefix + title + suffix
    if len(post) > MAX_POST_LENGTH:
        raise ValueError(f"Generated post is too long ({len(post)} characters).")
    return post

def save_draft(post, mode, source=None):
    now = datetime.now(timezone.utc)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    filename = DRAFT_DIR / f"{now.date()}.md"
    with filename.open("a", encoding="utf-8") as file:
        file.write(f"\n\n---\n\n## {now.strftime('%H:%M UTC')} — {mode} draft\n\n")
        if source:
            file.write(f"Source: {source}\n\n")
        file.write(f"```text\n{post}\n```\n")
    print(f"Saved {mode} draft to {filename}")
    print("----- DRAFT PREVIEW -----")
    print(post)
    print("-------------------------")

def make_question(state):
    index = int(state.get("question_index", 0))
    question = QUESTIONS[index % len(QUESTIONS)]
    return ("⚔️ WoW: Forever community question\n\n"
            f"{question}\n\nShare your answer below! #WoWForever")

def run_news(state):
    drafted = set(state["drafted_news"])
    entries = []
    successful_feeds = 0
    for feed, forever_scoped in FEEDS:
        try:
            feed_entries = get_entries(feed, forever_scoped=forever_scoped)
            entries.extend(feed_entries)
            successful_feeds += 1
            print(f"Feed OK: {feed} ({len(feed_entries)} entries)")
        except Exception as exc:
            print(f"Feed unavailable: {feed}: {exc}")
    if successful_feeds == 0:
        raise RuntimeError("All RSS feeds failed; refusing to treat this as an empty news day.")
    unique = {}
    for entry in entries:
        # Dedicated Forever feeds are already scoped to the correct game.
        # General feeds require an explicit Forever match to avoid Retail/Classic noise.
        if (entry.get("forever_scoped") or is_forever_story(entry)) and entry["id"] not in drafted:
            unique.setdefault(entry["id"], entry)
    candidates = sorted(unique.values(), key=lambda item: item.get("date", ""), reverse=True)
    if not candidates:
        print("No new qualifying WoW: Forever Blue posts to draft.")
        return False
    entry = candidates[0]
    post = make_news_post(entry)
    save_draft(post, "news", entry["link"])
    state["drafted_news"] = (state["drafted_news"] + [entry["id"]])[-MAX_HISTORY:]
    save_state(state)
    return True

def run_community(state):
    post = make_question(state)
    save_draft(post, "community")
    state["question_index"] = int(state.get("question_index", 0)) + 1
    save_state(state)
    return True

def main():
    parser = argparse.ArgumentParser(description="WoW: Forever draft generator (no automatic X posting)")
    parser.add_argument("--mode", choices=("news", "community"), default="news")
    args = parser.parse_args()
    print(f"{BOT_NAME}: creating {args.mode} draft")
    state = load_state()
    if args.mode == "news":
        run_news(state)
    else:
        run_community(state)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
