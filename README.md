# DIY Reminders — Training & Dinner via Telegram

Serverless, free reminders sent to Telegram on a schedule, powered by GitHub
Actions. Two streams:

- **Training** — a deterministic 24-week half-marathon + kettlebell + martial
  arts plan. The system computes which week/day you're on and sends the exact
  session each morning, plus a summary of next week every Sunday.
- **Dinner** — *seed prompts* you paste into Claude to plan meals around your
  leftover ingredients (daily kickoff + a weekly planning kickoff before you
  shop). No finished recipe is pushed; you iterate with Claude.

## Schedule (Australia/Sydney local — DST handled automatically)

| Day      | 05:30                  | 09:00                | 15:00              | 18:00                  |
|----------|------------------------|----------------------|--------------------|------------------------|
| Mon–Fri  | Daily exercise session | —                    | Dinner seed prompt | —                      |
| Saturday | Daily exercise session | Weekly dinner kickoff| Dinner seed prompt | —                      |
| Sunday   | Active-recovery nudge  | —                    | Dinner seed prompt | Next week's training summary |

The workflow fires UTC crons for both the AEST (+10) and AEDT (+11) offsets;
`src/main.py` gates on real Sydney time so only the correct firing sends. No
seasonal edits needed when DST flips on 4 Oct 2026.

## One-time setup

1. **Create a Telegram bot**
   - Message [`@BotFather`](https://t.me/BotFather) → `/newbot` → copy the
     **bot token**.
   - Send your new bot any message, then open
     `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the
     `chat.id` value — that's your **chat ID**.
2. **Add GitHub repo secrets** (Settings → Secrets and variables → Actions):
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ANTHROPIC_API_KEY` (optional — only used to reword the morning training
     message; everything still works without it)
3. **Set up a Claude dinner Project** (recommended): create a Project on
   claude.ai and paste the dinner style/prefs (see `DIET_PREFS` in
   `src/config.py`) as its custom instructions. Then each dinner seed prompt
   stays short and the Project history gives natural repeat-avoidance.

## Test it

- **GitHub UI:** Actions → *Reminders* → *Run workflow* → pick a reminder
  (and tick **dry run** to print without sending).
- **Locally:**
  ```bash
  pip install -r requirements.txt
  FORCE_REMINDER=all DRY_RUN=1 python -m src.main   # print all messages
  python -m pytest                                  # run boundary tests
  ```

## Customising

| Want to change…            | Edit |
|----------------------------|------|
| Training content           | `data/exercise_master_prompt.md` + `src/plan.py` |
| Plan start date            | `PLAN_START` in `src/config.py` |
| Dinner style / preferences | `DIET_PREFS` in `src/config.py` |
| Send times                 | `REMINDERS` in `src/main.py` **and** the crons in `.github/workflows/reminders.yml` |
| Timezone                   | `TIMEZONE` in `src/config.py` (and re-derive the UTC crons) |

## How it stays reliable

- **DST:** real-local-time gate, both offsets scheduled.
- **Claude down / no key:** training falls back to deterministic text; dinner
  seeds need no API.
- **Telegram blips:** send retries with exponential backoff; 4xx fails fast.
- **Phase edges:** weeks 8/9/16/17/23/24 special-cased and unit-tested
  (`tests/test_plan.py`), including the Sunday race day and post-plan rollover.

> **Note:** GitHub disables scheduled workflows after ~60 days of repo
> inactivity. A commit every couple of months keeps them alive.
