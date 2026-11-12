# Ring Wraithed Bot

Automated WoW: Forever news and community posts for X.

## What it does

- Checks the WoWHead Blue Tracker RSS feeds every 30 minutes.
- Publishes at most one new qualifying WoW: Forever-related item per run.
- Publishes a rotating community question on Monday, Wednesday, and Friday at 17:00 UTC.
- Stores successful publication history in \`state.json\`.
- Saves the published text and its X URL in \`drafts/\`.
- Does not mark a news item as published until X returns a tweet ID.
- Prevents overlapping scheduled runs with a GitHub Actions concurrency group.

The news filter intentionally requires a WoW: Forever phrase in the feed title or description to avoid unrelated World of Warcraft news.

## Required X API credentials

Create an X Developer App with write access and generate user access tokens. In GitHub, open:

**Settings → Secrets and variables → Actions → New repository secret**

Add these four secrets (never commit their values):

- \`X_API_KEY\`
- \`X_API_SECRET\`
- \`X_ACCESS_TOKEN\`
- \`X_ACCESS_TOKEN_SECRET\`

The workflow safely skips publishing while any credential is missing. Once all four are configured, scheduled runs publish automatically.

## Run manually

Open **Actions → Ring Wraithed automatic X publishing → Run workflow** and choose:

- \`news\`: check feeds and publish one new qualifying item, if available.
- \`community\`: publish the next community question.

## Schedule

- News checks: every 30 minutes.
- Community questions: Monday, Wednesday, Friday at 17:00 UTC.

GitHub Actions scheduled workflows use UTC. Adjust the cron schedule in \`.github/workflows/auto-publish.yml\` if needed.

## Important notes

- The first news run can publish an older qualifying item that the previous draft-only bot had already marked as seen. The old \`seen\` list is deliberately not treated as proof of publication because drafts were never confirmed as posted.
- X API access and write permissions are required. X may impose API plan limits or reject posts; failed API calls stop the run without advancing published-news history.
- GitHub Actions must have permission to write repository contents so it can commit state and published drafts.
