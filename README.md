# Ring Wraithed Bot

Automated WoW: Forever **draft generator** for X. It does not publish to X. You review and post every draft manually.

## What it does

- Checks Wowhead's WoW: Forever news and Blue Tracker RSS feeds every 30 minutes.
- Creates at most one new qualifying WoW: Forever news draft per run.
- Creates a rotating community-question draft on Monday, Wednesday, and Friday at 17:00 UTC.
- Saves draft text in dated Markdown files in `drafts/`.
- Tracks drafted news items to avoid generating the same news draft repeatedly.
- Prints each new draft in the GitHub Actions run log.
- Does not connect to X, call the X API, or require X API credentials/credits.

News tracking checks Wowhead's dedicated WoW: Forever news feed (editorial news, guides, hotfix coverage, and other Forever articles), the dedicated Forever Blue Tracker RSS feed, and the US and EU Forever Blue Tracker news feeds. Dedicated Forever feeds are trusted even when an individual post title does not repeat the game name. General Blue Tracker feeds remain a secondary source and require explicit WoW: Forever wording to avoid unrelated Retail or other Classic news. The bot still creates at most one new news draft per run.

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
