# Ring Wraithed Bot

Automated WoW: Forever **draft generator** for X. It does not publish to X. You review and post every draft manually.

## What it does

- Checks both content streams shown on Wowhead's WoW: Forever hub every 30 minutes: recent/editorial news and Blizzard Blue Tracker posts.
- Creates at most one new qualifying WoW: Forever news draft per run.
- Creates a rotating community-question draft on Monday, Wednesday, and Friday at 17:00 UTC.
- Saves draft text in dated Markdown files in `drafts/`.
- Tracks drafted news items to avoid generating the same news draft repeatedly.
- Prints each new draft in the GitHub Actions run log.
- Does not connect to X, call the X API, or require X API credentials/credits.

News tracking mirrors the two main content areas on [Wowhead's WoW: Forever hub](https://www.wowhead.com/forever): its dedicated Forever news feed (recent articles, guides, hotfix coverage, and editorial posts) and the dedicated Forever Blue Tracker feeds (Blizzard Blue posts, including US and EU). Dedicated Forever feeds are trusted even when an individual title does not repeat the game name. General Wowhead news and Blue Tracker feeds are secondary fallbacks and require explicit WoW: Forever wording to avoid unrelated Retail or other Classic news. Drafts identify Blue Tracker items as Blizzard Blue posts and regular articles as WoW: Forever news. The bot still creates at most one new news draft per run.

## Where to find drafts

Open the repository's **drafts** folder:
https://github.com/Ringwraithed/ring-wraithed-bot/tree/main/drafts

Each date has a Markdown file containing the draft text and source link. You can copy the text into X, review it, edit it, and post it yourself.

You can also open **Actions → Ring Wraithed WoW Forever Draft Generator**, select **Run workflow**, and choose:
- `news`: check WoWHead feeds and create one new news draft if available.
- `community`: create the next community question draft.

## Schedule

- News draft checks: every 30 minutes.
- Community question drafts: Monday, Wednesday, Friday at 17:00 UTC.

GitHub Actions scheduled workflows use UTC.

## Important

- No X API keys, access tokens, billing, or write permissions are needed.
- The first run preserves the old bot's `seen` list to avoid re-drafting items it had already handled.
- A draft is never posted automatically. You are always in control of what goes on X.
