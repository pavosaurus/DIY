# Setup — getting the reminders running

Everything code-side is done and tested. To go live you need to complete the
steps below. They're the only things that require *your* accounts/credentials.

> **Good news:** `claude/pensive-fermat-cn6vg9` is this repo's **default
> branch**, and GitHub runs scheduled workflows from the default branch — so
> there is **no merge/PR step**. Activate the workflow here and the schedule is
> live.

---

## Step 1 — Create the Telegram bot(s)

You need one bot per stream. Do this once per bot (Training, and Dinner).

1. Open Telegram → search **`@BotFather`** → **Start**.
2. Send **`/newbot`**.
3. Give it a **name** (e.g. `My Training Reminders`).
4. Give it a **username** ending in `bot` (e.g. `npavitt_training_bot`).
5. Copy the **token** BotFather returns (`8123456789:AAH...`).
6. Open your new bot, tap **Start**, and send it any message (e.g. `hi`).
   *(Required — a bot cannot message you until you message it first.)*

Repeat for the Dinner bot if you want dinner reminders too.

## Step 2 — Get your chat ID

1. In a browser open: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (paste the bot token in place of `<TOKEN>`).
2. Find `"chat":{"id": 111111111` — that number is your chat ID.
3. If the result is empty, message the bot again and refresh.

You can reuse the same chat ID for both bots (if you DM both from the same
account) or use different ones to route streams to different chats/groups.

## Step 3 — Add the secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**.
Add:

| Secret | Required | Used for |
|--------|----------|----------|
| `EXERCISE_BOT_TOKEN` | yes | daily session + Sunday training summary |
| `EXERCISE_CHAT_ID`   | yes | "" |
| `DINNER_BOT_TOKEN`   | for dinners | daily + weekly dinner seed prompts |
| `DINNER_CHAT_ID`     | for dinners | "" |
| `ANTHROPIC_API_KEY`  | optional | rewords the morning message; works without it |

## Step 4 — Activate the workflow

The automation token that built this branch lacks GitHub's `workflow` scope, so
the workflow file is parked at `ci/reminders.yml`. Move it into place yourself
(this uses *your* permissions, which include the scope):

**Web UI (easiest):**
1. Open `ci/reminders.yml` in the repo → **Copy raw contents**.
2. **Add file → Create new file** → name it `.github/workflows/reminders.yml`.
3. Paste → **Commit** to `claude/pensive-fermat-cn6vg9`.

**Or locally:**
```bash
mkdir -p .github/workflows
git mv ci/reminders.yml .github/workflows/reminders.yml
git commit -m "Activate reminders workflow"
git push
```

Once committed, the **Reminders** workflow appears under the **Actions** tab and
the schedules are registered.

## Step 5 — Verify (don't just wait)

- Actions → **Reminders** → **Run workflow** → pick `exercise`, tick **dry run**
  → Run. Check the log shows the rendered message.
- Then run again with **dry run unticked** → the message should land in Telegram.

> New scheduled workflows sometimes skip their first expected tick, and GitHub
> cron can run a few minutes late — so always confirm with **Run workflow**
> before relying on the clock.

## Step 6 — Done

After Step 4 lands on the default branch and Step 3 secrets exist, it runs
automatically:

| Day      | 05:30 | 09:00 | 15:00 | 18:00 |
|----------|-------|-------|-------|-------|
| Mon–Fri  | exercise | — | dinner | — |
| Saturday | exercise | dinner (weekly) | dinner | — |
| Sunday   | exercise (recovery) | — | dinner | training summary |

(Times are Australia/Sydney; DST is handled automatically.)

---

## Quick local test (optional, no GitHub needed)

```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your token + chat ID into .env
./run_test.sh exercise --dry   # preview
./run_test.sh exercise         # real send
```

## Keeping it alive

GitHub disables scheduled workflows after ~60 days of repo inactivity. A commit
every couple of months keeps them running.
