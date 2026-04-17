# Heart Link Bot

Production-ready Telegram dating / match bot built with **Python**, **aiogram v3**, and a **private Telegram channel as the main persistent database**.

This fixed version is ready for Render with:
- Python pinned to **3.11.9** via `.python-version`
- a `/health` HTTP endpoint for Render/UptimeRobot
- `ADMIN_IDS` parsing that accepts comma-separated or JSON-style values
- a Telethon **user** StringSession for channel replay

## Stack

- Python 3.11+
- aiogram v3 for bot updates and UX
- Telethon for channel-backed storage replay and write access using a user StringSession
- Pydantic / pydantic-settings for schemas and config
- Async architecture
- Render-ready polling deployment

> Why both aiogram and Telethon?
>
> aiogram handles the bot UX and update routing.  
> Telethon is used only for the storage layer so the bot can replay and index private channel history on startup. This keeps the bot UX clean while making the channel-backed storage restart-safe.

---

## Features implemented

- `/start` language selection with **ReplyKeyboard**
- English / Myanmar / Russian localization
- Full onboarding flow:
  - age validation
  - 18+ enforcement
  - gender
  - looking for
  - city
  - required current location
  - name
  - bio
  - up to 3 photos or 1 short video
  - profile preview and edit-before-save
- Discover flow:
  - one profile at a time
  - love / love+message / dislike / pass
  - distance display using haversine
  - candidate ranking with premium + completeness + recency + proximity + fairness
- Mutual match creation and dual notifications
- Premium plans + admin-editable prices
- Complaint / report flow
- My Profile view, edit, pause, soft delete
- Admin commands:
  - `/admin`
  - `/PremiumPrice`
  - `/stats`
  - `/ban <user_id>`
  - `/unban <user_id>`
  - `/user <user_id>`
  - `/setpremium <user_id> <days>`
  - `/delpremium <user_id>`
  - `/broadcast`
  - `/reports`
  - `/config`
- Logging and restart-safe cache rebuild from private DB channel

---

## Project structure

```text
heart_link_bot/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── context.py
│   ├── states.py
│   ├── handlers/
│   │   ├── common.py
│   │   ├── onboarding.py
│   │   ├── discover.py
│   │   ├── profile.py
│   │   ├── premium.py
│   │   ├── complaint.py
│   │   └── admin.py
│   ├── services/
│   │   ├── storage.py
│   │   ├── localization.py
│   │   ├── matchmaking.py
│   │   ├── notifier.py
│   │   └── payments.py
│   ├── keyboards/
│   │   ├── reply.py
│   │   └── inline.py
│   ├── locales/
│   │   └── translations.py
│   ├── models/
│   │   ├── enums.py
│   │   └── records.py
│   ├── middlewares/
│   │   └── throttle.py
│   └── utils/
│       ├── geo.py
│       ├── formatters.py
│       └── text.py
├── .env.example
├── requirements.txt
├── runtime.txt
├── render.yaml
└── README.md
```

---

## Environment variables

Copy `.env.example` to `.env`.

Required:

- `BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `PRIVATE_DB_CHANNEL_ID`
- `STORAGE_SESSION`
- `ADMIN_IDS`

Optional:

- `LOG_CHANNEL_ID`
- `RENDER_EXTERNAL_URL`
- `DEFAULT_LANGUAGE`
- `DEBUG`
- `BOT_USERNAME`
- `DISCOVER_PASS_TTL_HOURS`
- `BROADCAST_DELAY_MS`
- `MAX_BIO_LENGTH`
- `MAX_NAME_LENGTH`

`ADMIN_IDS` accepts either:
- `123456789,987654321`
- `[123456789,987654321]`

---

## Telegram setup

### 1) Create the bot
Create your bot with `@BotFather` and get the bot token.

### 2) Create the private DB channel
Create a **private Telegram channel** and:

- add the bot as **administrator**
- copy the numeric channel ID
- set `PRIVATE_DB_CHANNEL_ID`

### 3) Create Telegram API credentials
For Telethon storage replay, create an API ID / hash from Telegram developer tools and put them in:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

### 4) Generate a Telethon storage session
Because Telegram does **not** allow bots to replay channel history with `GetHistoryRequest`, the storage layer uses a **dedicated Telegram user account**.

Use `tools/generate_storage_session.py` locally, sign in to the storage account once, then put the resulting string into:

- `STORAGE_SESSION`

Add both the **bot** and the **storage user account** to the private DB channel. The storage user must be able to read and write in the channel.

---

## How the private Telegram channel database works

The channel is the **main source of truth**.

Each DB write is appended as a typed channel message in this format:

```text
HLDB|RECORD_TYPE|record_id|version
{"record_type":"USER_PROFILE", ...}
```

Examples of stored record types:

- `USER_PROFILE`
- `USER_SETTINGS`
- `USER_MEDIA`
- `LIKE`
- `DISLIKE`
- `PASS`
- `VIEW`
- `MATCH`
- `PREMIUM`
- `REPORT`
- `CONFIG`
- `ADMIN_LOG`

### Startup replay

On startup, `TelegramChannelStorage.rebuild_cache()`:

1. connects with Telethon using a dedicated user `StringSession`
2. reads the full private channel history
3. parses every `HLDB|...` message
4. keeps the latest version of each record
5. rebuilds in-memory indexes for profiles, likes, reports, matches, config, etc.

### Update strategy

The implementation uses an **append-only event style**:

- every update writes a new versioned record
- latest version is selected in cache
- this keeps writes simple and safe
- restart recovery is deterministic

This is intentionally safer than trying to mutate old messages in place.

---

## How premium config is stored

Global config is stored as a `CONFIG` record with `record_id="global"`.

It includes:

- premium plans
- pass TTL hours

Default plans:

- 2 days • ⭐ 20
- 10 days • ⭐ 150
- 30 days • ⭐ 400
- 90 days • ⭐ 1000

When an admin uses `/PremiumPrice`, the selected plan is updated and a new `CONFIG` record version is appended to the DB channel.

Premium status for users is persisted both as:

- `PREMIUM` record
- `premium_until` inside the user profile snapshot

---

## Discovery and match flow

### Candidate filtering
Discover excludes:

- self
- banned users
- inactive / paused profiles
- already matched users
- disliked users
- recently passed users

### Ranking
Ranking uses:

- compatibility
- profile completeness
- premium boost
- activity recency
- optional distance proximity
- daily fairness rotation

### Reactions
Available actions:

- `❤️ Love`
- `💌 Love and message sent`
- `👎 Dislike`
- `💤 Zzz`

### Mutual match
When A likes B and B already liked A:

1. a `MATCH` record is created
2. both users receive a match notification
3. intro message is delivered if one was saved

---

## Localization organization

All user-facing text is centralized in:

```python
app/locales/translations.py
```

It contains:

- `TRANSLATIONS` dictionary
- language parsing
- gender / looking-for parsing
- report reason helpers

Supported languages:

- English (`en`)
- Myanmar (`my`)
- Russian (`ru`)

---

## Render deployment

This project is configured for **polling** because it is the simplest and most robust starting point on Render.

### Deploy
1. Push the project to GitHub
2. Create a new Render service
3. Use the included `render.yaml` or manually set:
   - Build command:
     ```bash
     pip install -r requirements.txt
     ```
   - Start command:
     ```bash
     python -m app.main
     ```

---

## Local run

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

---

## Important operational notes

- The bot must stay admin in the private DB channel.
- Users must start the bot before they can receive messages from it.
- Broadcast delivery will skip users who blocked the bot.
- Payment integration is intentionally isolated in `app/services/payments.py`.
- This repo starts with polling, but the code layout is clean enough to add webhook bootstrap later.

---

## Production-hardening ideas for next step

- add structured JSON logs
- add moderation queues and admin review actions
- add Telegram Stars invoice implementation
- add richer premium purchase callbacks
- add persistent telemetry dashboard
- add pagination for report review
- add local snapshot fallback / checksum validation
- add unit tests and integration tests

---

## Acceptance checklist mapping

- `/start` asks for language with ReplyKeyboard ✅
- English / Myanmar / Russian work ✅
- Onboarding flow implemented ✅
- City + current location required ✅
- Media upload + confirmation flow implemented ✅
- Discover shows one profile at a time ✅
- Distance shown in meters / km ✅
- Love / Love+Message / Dislike / Zzz implemented ✅
- Mutual match logic implemented ✅
- Premium page exists with plans ✅
- `/PremiumPrice` edits days and stars ✅
- Private Telegram channel used as main DB ✅
- Admin commands included ✅
- Reports / complaints included ✅
- My Profile / Language / Premium / Complain menu items included ✅
- Modular code structure ✅
- Render deployment files included ✅


---

## Render deployment notes

Use this project as a **Web Service**. The app now binds an HTTP server on `PORT` and exposes:

- `/`
- `/health`

That makes Render port detection succeed and also lets you ping the service from UptimeRobot.

Recommended Render settings:

- Root Directory: leave blank if the repo root contains `app/`, `requirements.txt`, and `render.yaml`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m app.main`
- Python version: `3.11.9`

Required Render environment variables:

```env
BOT_TOKEN=...
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=...
STORAGE_SESSION=...
PRIVATE_DB_CHANNEL_ID=-1001234567890
ADMIN_IDS=123456789,987654321
DEFAULT_LANGUAGE=en
DEBUG=false
```
