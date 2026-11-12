import argparse
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import tweepy

BOT_NAME = "Ring_Wraithed"
FEEDS = [
    "https://www.wowhead.com/blue-tracker?rss=",
    "https://www.wowhead.com/blue-tracker/news?rss=",
    "https://www.wowhead.com/news/rss/all",
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
        return {"published_news": [], "published_engagement": [], "question_index": 0}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot safely read {STATE_FILE}: {exc}") from exc
    # The old "seen" list represented drafts, not confirmed publications.
    state.setdefault("published_news", [])
    state.setdefault("published_engagement", [])
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

def get_entries(feed_url):
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
                            "description": description, "date": pub_date})
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
                            "description": description, "date": pub_date})
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
    link = entry["link"]
    suffix = f"\n\n{link}\n#WoWForever"
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

def make_question(state):
    index = int(state.get("question_index", 0))
    question = QUESTIONS[index % len(QUESTIONS)]
    return ("⚔️ WoW: Forever community question\n\n"
            f"{question}\n\nShare your answer below! #WoWForever")

def make_x_client():
    names = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
    values = {name: os.getenv(name) for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing GitHub Actions secrets: " + ", ".join(missing))
    return tweepy.Client(
        consumer_key=values["X_API_KEY"],
        consumer_secret=values["X_API_SECRET"],
        access_token=values["X_ACCESS_TOKEN"],
        access_token_secret=values["X_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )

def publish(client, post):
    response = client.create_tweet(text=post)
    data = getattr(response, "data", None) or {}
    tweet_id = data.get("id")
    if not tweet_id:
        raise RuntimeError(f"X did not return a tweet ID: {response}")
    return str(tweet_id)

def save_published_draft(post, mode, tweet_id):
    now = datetime.now(timezone.utc)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    filename = DRAFT_DIR / f"{now.date()}.md"
    with filename.open("a", encoding="utf-8") as file:
        file.write(f"\n\n---\n\n## {now.strftime('%H:%M UTC')} — {mode}\n\n"
                   f"{post}\n\nPublished: https://x.com/i/web/status/{tweet_id}\n")

def run_news(state, client):
    published = set(state["published_news"])
    entries = []
    successful_feeds = 0
    for feed in FEEDS:
        try:
            feed_entries = get_entries(feed)
            entries.extend(feed_entries)
            successful_feeds += 1
            print(f"Feed OK: {feed} ({len(feed_entries)} entries)")
        except Exception as exc:
            print(f"Feed unavailable: {feed}: {exc}")
    if successful_feeds == 0:
        raise RuntimeError("All RSS feeds failed; refusing to treat this as an empty news day.")
    unique = {}
    for entry in entries:
        if is_forever_story(entry) and entry["id"] not in published:
            unique.setdefault(entry["id"], entry)
    candidates = sorted(unique.values(), key=lambda item: item.get("date", ""), reverse=True)
    if not candidates:
        print("No new qualifying WoW: Forever Blue posts.")
        return False
    entry = candidates[0]
    post = make_news_post(entry)
    tweet_id = publish(client, post)
    # Only advance publication history after X confirms the post.
    state["published_news"] = (state["published_news"] + [entry["id"]])[-MAX_HISTORY:]
    save_state(state)
    save_published_draft(post, "news", tweet_id)
    print(f"Published news tweet {tweet_id}: {entry['title']}")
    return True

def run_community(state, client):
    post = make_question(state)
    tweet_id = publish(client, post)
    state["question_index"] = int(state.get("question_index", 0)) + 1
    state["published_engagement"] = (state["published_engagement"] + [tweet_id])[-MAX_HISTORY:]
    save_state(state)
    save_published_draft(post, "community", tweet_id)
    print(f"Published community tweet {tweet_id}")
    return True

def main():
    parser = argparse.ArgumentParser(description="WoW: Forever X publishing bot")
    parser.add_argument("--mode", choices=("news", "community"), default="news")
    args = parser.parse_args()
    print(f"{BOT_NAME}: starting {args.mode} run")
    state = load_state()
    client = make_x_client()
    if args.mode == "news":
        run_news(state, client)
    else:
        run_community(state, client)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
