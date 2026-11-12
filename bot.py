
import json
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

FEEDS = [
    "https://www.wowhead.com/news/rss/all",
    "https://www.wowhead.com/blue-tracker?rss=",
    "https://www.wowhead.com/blue-tracker/news?rss=",
]

STATE_FILE = Path("state.json")
DRAFT_DIR = Path("drafts")
MAX_SEEN = 500

QUESTIONS = [
    "Which WoW: Forever class would you recommend to a brand-new player?",
    "What's the most underrated class in WoW: Forever?",
    "Alliance or Horde? Which side are you choosing?",
    "What's your favorite leveling zone?",
    "Which dungeon do you never get tired of?",
    "What's the hardest boss you've faced so far?",
    "Which class deserves some love from Blizzard?",
    "What's your favorite WoW: Forever memory?",
    "If you could change one thing, what would it be?",
    "What's your favorite race and class combination?",
    "Are you a solo player or do you prefer grouping?",
    "What's the best profession combination?",
    "Which dungeon should every player experience?",
    "What's your biggest leveling tip?",
    "What's one feature you hope Blizzard adds?",
    "What's your favorite character you've created?",
    "Do you prefer PvE or PvP?",
    "Which class has the most satisfying gameplay?",
    "What's the best piece of advice for new players?",
    "What makes WoW: Forever special to you?",
    "Which zone brings back the most nostalgia?",
    "What's your favorite questline?",
    "Which class would you never abandon?",
    "What's your biggest wish for the future of WoW: Forever?",
    "What keeps you coming back to Azeroth?",
    "What's the most memorable moment you've had in game?",
    "What's your favorite dungeon group composition?",
    "Which profession do you enjoy the most?",
    "What's one thing new players should know?",
    "What's your personal goal in WoW: Forever?",
]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen": [], "question_index": 0}

def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )

def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())

def get_entries(feed_url):
    request = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "RingWraithedNewsBot/1.0"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        data = response.read()

    root = ET.fromstring(data)
    entries = []

    # RSS
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title"))
        link = item.findtext("link") or ""
        guid = item.findtext("guid") or link
        description = clean_text(item.findtext("description"))

        if title and link:
            entries.append({
                "title": title,
                "link": link,
                "id": guid or link,
                "description": description,
            })

    # Atom
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//a:entry", ns):
        title = clean_text(item.findtext("a:title", namespaces=ns))
        link_node = item.find("a:link", ns)
        link = link_node.get("href", "") if link_node is not None else ""
        guid = item.findtext("a:id", namespaces=ns) or link
        description = clean_text(
            item.findtext("a:summary", namespaces=ns)
        )

        if title and link:
            entries.append({
                "title": title,
                "link": link,
                "id": guid or link,
                "description": description,
            })

    return entries

def is_forever_story(entry):
    text = (entry["title"] + " " + entry["description"]).lower()

    terms = [
        "wow: forever",
        "wow forever",
        "world of warcraft: forever",
        "world of warcraft forever",
    ]

    return any(term in text for term in terms)


def make_news_post(entry):
    title = entry["title"].strip()
    description = entry.get("description", "").strip()
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

    # Only use the feed's actual description.
    # Never invent details if it is missing.
    summary = description[:350].strip()

    post = f"{headline}\n\n{title}\n"

    if summary:
        post += f"\n{summary}\n"

    post += (
        f"\n{question}\n\n"
        f"Full details 👇\n{link}\n\n"
        f"#WoWForever"
    )

    return post

        f"⚔️ WoW: Forever COMMUNITY QUESTION\n\n"
        f"{question}\n\n"
        f"Share your answer below!\n\n"
        f"#WoWForever #Warcraft"
    )

def main():
    state = load_state()
    seen = set(state.get("seen", []))

    entries = []

    for feed in FEEDS:
        try:
            entries.extend(get_entries(feed))
            print("Checked:", feed)
        except Exception as error:
            print("Feed unavailable:", feed, error)

    # Only accept clearly identified WoW: Forever stories.
    candidates = [
        entry for entry in entries
        if is_forever_story(entry)
        and entry["id"] not in seen
    ]

    post = None

    if candidates:
        entry = candidates[0]
        post = make_news_post(entry)
        seen.add(entry["id"])
        print("New WoW: Forever article:", entry["title"])
    else:
        # No new confirmed news? Publish an evergreen
        # community question instead of inventing news.
        post = make_question(state)
        print("No new qualifying news. Created community question.")

    now = datetime.now(timezone.utc)
    DRAFT_DIR.mkdir(exist_ok=True)

    filename = DRAFT_DIR / f"{now.date()}.md"

    with filename.open("a", encoding="utf-8") as file:
        file.write(
            f"\n\n---\n\n"
            f"## {now.strftime('%H:%M UTC')}\n\n"
            f"{post}\n"
        )

    state["seen"] = list(seen)[-MAX_SEEN:]
    save_state(state)

    print("Draft saved:", filename)

if __name__ == "__main__":
    main()
