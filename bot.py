
import json
import re
import html
import urllib.request
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ==========================================
# RING_WRAITHED - WOW: FOREVER NEWS BOT
# ==========================================

BOT_NAME = "Ring_Wraithed"

FEEDS = [
    "https://www.wowhead.com/news/rss/all",
    "https://www.wowhead.com/blue-tracker?rss=",
    "https://www.wowhead.com/blue-tracker/news?rss=",
]

STATE_FILE = Path("state.json")
DRAFT_DIR = Path("drafts")

MAX_SEEN = 500
POSTS_PER_RUN = 1

FOREVER_TERMS = [
    "wow: forever",
    "wow forever",
    "world of warcraft: forever",
    "world of warcraft forever",
]

QUESTIONS = [
    "Which WoW: Forever class would you recommend to a new player?",
    "What's the most underrated class in WoW: Forever?",
    "Alliance or Horde? Which side are you choosing?",
    "What's your favorite leveling zone?",
    "Which dungeon do you never get tired of?",
    "What's the hardest boss you've faced?",
    "Which class deserves more attention from Blizzard?",
    "What's your favorite WoW: Forever memory?",
    "If you could change one thing, what would it be?",
    "What's your favorite race and class combination?",
    "Are you a solo player or do you prefer grouping?",
    "What's your favorite profession?",
    "Which dungeon should every player experience?",
    "What's your biggest leveling tip?",
    "What's one feature you hope Blizzard adds?",
    "What's your favorite character you've created?",
    "Do you prefer PvE or PvP?",
    "Which class has the most satisfying gameplay?",
    "What's your best advice for new players?",
    "What makes WoW: Forever special to you?",
    "Which zone brings back the most nostalgia?",
    "What's your favorite questline?",
    "Which class would you never abandon?",
    "What's your biggest wish for WoW: Forever?",
    "What keeps you coming back to Azeroth?",
    "What's your most memorable in-game moment?",
    "What's your favorite dungeon group composition?",
    "Which profession do you enjoy most?",
    "What's one thing new players should know?",
    "What's your personal goal in WoW: Forever?",
]


# ==========================================
# STATE MANAGEMENT
# ==========================================

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(
                STATE_FILE.read_text(encoding="utf-8")
            )
        except Exception:
            print("Could not read state file. Starting fresh.")

    return {
        "seen": [],
        "question_index": 0
    }


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )


# ==========================================
# TEXT CLEANING
# ==========================================

def clean_text(value):
    value = html.unescape(value or "")

    value = re.sub(
        r"<(script|style).*?>.*?</\1>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ==========================================
# RSS NEWS DISCOVERY
# ==========================================

def get_entries(feed_url):
    request = urllib.request.Request(
        feed_url,
        headers={
            "User-Agent": "RingWraithedNewsBot/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=25
    ) as response:
        data = response.read()

    root = ET.fromstring(data)

    entries = []

    # Standard RSS feeds
    for item in root.findall(".//item"):
        title = clean_text(
            item.findtext("title")
        )

        link = (
            item.findtext("link") or ""
        ).strip()

        guid = (
            item.findtext("guid") or link
        ).strip()

        description = clean_text(
            item.findtext("description")
        )

        pub_date = item.findtext("pubDate") or ""

        if title and link:
            entries.append({
                "title": title,
                "link": link,
                "id": guid or link,
                "description": description,
                "date": pub_date,
            })

    # Atom feeds
    ns = {
        "a": "http://www.w3.org/2005/Atom"
    }

    for item in root.findall(".//a:entry", ns):
        title = clean_text(
            item.findtext(
                "a:title",
                namespaces=ns
            )
        )

        link_node = item.find(
            "a:link",
            ns
        )

        link = (
            link_node.get("href", "")
            if link_node is not None
            else ""
        )

        guid = (
            item.findtext(
                "a:id",
                namespaces=ns
            ) or link
        )

        description = clean_text(
            item.findtext(
                "a:summary",
                namespaces=ns
            )
        )

        pub_date = item.findtext(
            "a:published",
            namespaces=ns
        ) or ""

        if title and link:
            entries.append({
                "title": title,
                "link": link,
                "id": guid or link,
                "description": description,
                "date": pub_date,
            })

    return entries


# ==========================================
# WOW: FOREVER FILTER
# ==========================================

def is_forever_story(entry):
    title = entry["title"].lower()

    description = entry.get(
        "description", ""
    ).lower()

    text = title + " " + description

    return any(
        term in text
        for term in FOREVER_TERMS
    )


# ==========================================
# NEWS POST WRITER
# ==========================================

def make_news_post(entry):
    title = entry["title"].strip()

    description = entry.get(
        "description", ""
    ).strip()

    link = entry["link"]

    lower = title.lower()

    if "hotfix" in lower:
        headline = "🚨 WOW: FOREVER HOTFIX ALERT!"
        question = "What do you think of these changes?"

    elif "class" in lower or "tuning" in lower:
        headline = "⚔️ CLASS UPDATE!"
        question = "Is your class getting the changes it needs?"

    elif "secret" in lower or "discovered" in lower:
        headline = "🔎 NEW DISCOVERY IN WOW: FOREVER!"
        question = "Have you discovered anything interesting?"

    elif "dungeon" in lower or "loot" in lower:
        headline = "🔥 WOW: FOREVER DUNGEON UPDATE!"
        question = "Have you explored this content yet?"

    elif "blue post" in lower:
        headline = "🔵 BLIZZARD BLUE POST!"
        question = "What are your thoughts?"

    else:
        headline = "📰 WOW: FOREVER NEWS!"
        question = "What do you think about this?"

    # Use only information actually supplied
    # by the RSS feed. Never invent details.

    summary = description[:250].strip()

    post = (
        f"{headline}\n\n"
        f"{title}\n"
    )

    if summary:
        post += f"\n{summary}\n"

    post += (
        f"\n{question}\n\n"
        f"Full details 👇\n"
        f"{link}\n\n"
        f"#WoWForever"
    )

    return post


# ==========================================
# COMMUNITY QUESTION WRITER
# ==========================================

def make_question(state):
    index = state.get(
        "question_index", 0
    )

    question = QUESTIONS[
        index % len(QUESTIONS)
    ]

    state["question_index"] = index + 1

    return (
        "⚔️ WOW: FOREVER COMMUNITY QUESTION\n\n"
        f"{question}\n\n"
        "Share your answer below!\n\n"
        "#WoWForever"
    )


# ==========================================
# DAILY DRAFT CREATION
# ==========================================

def main():
    print("=" * 45)
    print("RING_WRAITHED WOW: FOREVER NEWS BOT")
    print("=" * 45)

    state = load_state()

    seen = set(
        state.get("seen", [])
    )

    entries = []

    # Check every feed independently.
    for feed in FEEDS:
        try:
            new_entries = get_entries(feed)

            entries.extend(new_entries)

            print(
                f"Feed checked successfully: {feed}"
            )

            print(
                f"Articles discovered: {len(new_entries)}"
            )

        except Exception as error:
            print(
                f"Feed unavailable: {feed}"
            )

            print(error)

    # Keep only verified Forever-related
    # stories which haven't been used before.

    candidates = [
        entry for entry in entries
        if is_forever_story(entry)
        and entry["id"] not in seen
    ]

    # Prefer articles with a publication date.
    candidates.sort(
        key=lambda item: item.get("date", ""),
        reverse=True
    )

    posts = []

    for entry in candidates[:POSTS_PER_RUN]:
        posts.append(
            make_news_post(entry)
        )

        seen.add(entry["id"])

        print(
            "New story selected:",
            entry["title"]
        )

    # If there is no qualifying news,
    # create an evergreen community question.

    if not posts:
        posts.append(
            make_question(state)
        )

        print(
            "No new qualifying news. "
            "Created community question."
        )

    # Save drafts using UTC date and time.

    now = datetime.now(timezone.utc)

    DRAFT_DIR.mkdir(
        exist_ok=True
    )

    filename = DRAFT_DIR / (
        f"{now.date()}.md"
    )

    with filename.open(
        "a",
        encoding="utf-8"
    ) as file:

        for post in posts:
            file.write(
                "\n\n---\n\n"
                f"## {now.strftime('%H:%M UTC')}\n\n"
                f"{post}\n"
            )

    # Save duplicate protection.

    state["seen"] = list(seen)[-MAX_SEEN:]

    save_state(state)

    print("=" * 45)
    print("SUCCESS!")
    print("Draft saved:", filename)
    print("Posts created:", len(posts))
    print("=" * 45)


if __name__ == "__main__":
    main()
