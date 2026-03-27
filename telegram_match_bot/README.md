# Telegram Match Bot

A production-ready Telegram Bot API matchmaking bot built with **Python 3.11**, **aiogram 3.x**, **asyncpg**, **Neon PostgreSQL**, and **Render** deployment support.

## Features

- Tinder-style profile browsing: one profile at a time
- Async like system with **mutual-like-only** matching
- Username reveal only after a successful mutual match
- English + Burmese (Myanmar) localization
- Profile creation and editing flow with validation
- ReplyKeyboard main menu + InlineKeyboard browsing actions
- Admin panel with stats, search, moderation, reports, broadcast, and maintenance mode
- Health endpoint for Render health checks and uptime monitoring
- Concurrency-safe match creation using PostgreSQL transactions and deterministic row locking
- Anti-spam rate limiting and suspicious mass-like suspension

## Project Structure

```text
telegram_match_bot/
├── app/
│   ├── config.py
│   ├── db/
│   │   ├── database.py
│   │   └── schema.sql
│   ├── filters/
│   │   └── admin.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── errors.py
│   │   ├── admin/
│   │   │   └── panel.py
│   │   └── user/
│   │       ├── browse.py
│   │       ├── matches.py
│   │       ├── menu.py
│   │       ├── profile.py
│   │       ├── settings.py
│   │       └── start.py
│   ├── keyboards/
│   │   ├── inline.py
│   │   └── reply.py
│   ├── locales/
│   │   ├── en.py
│   │   └── my.py
│   ├── middlewares/
│   │   └── user_context.py
│   ├── repositories/
│   │   ├── likes.py
│   │   ├── reports.py
│   │   ├── settings.py
│   │   └── users.py
│   ├── services/
│   │   ├── admin.py
│   │   ├── app_context.py
│   │   ├── discovery.py
│   │   ├── guards.py
│   │   ├── i18n.py
│   │   └── rate_limit.py
│   └── utils/
│       ├── formatters.py
│       ├── states.py
│       └── validators.py
├── .env.example
├── .python-version
├── Procfile
├── README.md
├── render.yaml
├── requirements.txt
└── main.py
```

## Local Development

### 1) Create a bot
- Create your bot with **@BotFather**
- Copy the token into `.env`
- Set a public username for the bot itself

### 2) Create Neon database
- Create a Neon project
- Copy the `DATABASE_URL`
- Make sure the URL includes `sslmode=require`

### 3) Configure environment

```bash
cp .env.example .env
```

Then edit `.env`.

### 4) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 5) Run locally

```bash
python main.py
```

The bot will:
- connect to Neon
- initialize schema automatically
- start the HTTP health endpoint at `http://localhost:10000/health`
- start polling by default

## Render Deployment

### Recommended mode
Use a **Render Web Service** for this project.

Why:
- Render health checks only apply to web services
- this bot exposes `/health`
- polling can still run safely inside the same process while the web service exposes health checks

### Deploy steps
1. Push this project to GitHub.
2. Create a new Render Web Service.
3. Use the included `render.yaml`, or configure manually.
4. Set environment variables:
   - `BOT_TOKEN`
   - `DATABASE_URL`
   - `ADMIN_IDS`
   - `BOT_USERNAME`
   - `USE_WEBHOOK=false`
5. Deploy.

### Polling vs webhook on Render

#### Polling (default)
- easiest setup
- no webhook registration complexity
- works well for a single-instance Render deployment
- health endpoint still available for Render checks

#### Webhook (optional)
Set:
- `USE_WEBHOOK=true`
- `WEBHOOK_BASE_URL=https://your-app.onrender.com`

Then the app will:
- register Telegram webhook
- serve updates on `WEBHOOK_PATH`
- still serve `/health`

## Database Notes

Schema is in `app/db/schema.sql` and is auto-initialized on startup.

### Main tables
- `users`
- `likes`
- `skips`
- `matches`
- `reports`
- `admin_actions`
- `app_settings`
- `user_action_logs`

## Mutual-Like Integrity Logic

When user A likes user B:
1. The bot starts a DB transaction.
2. It locks both user rows in a deterministic order (`ORDER BY id FOR UPDATE`).
3. It reads existing `A -> B`, `B -> A`, and `matches` rows.
4. It inserts `A -> B` if needed.
5. If `B -> A` already exists, it inserts the match pair exactly once.
6. It updates both like rows to `matched`.

This protects against:
- duplicate callback taps
- Telegram retries
- concurrent likes arriving almost simultaneously
- restarts after partial handler execution

Data integrity is enforced by:
- unique constraint on `(from_user_id, to_user_id)` in `likes`
- unique constraint on `(user1_id, user2_id)` in `matches`
- sorted match pair storage (`user1_id < user2_id`)
- transaction boundaries
- row locks

## Discovery Logic

A candidate profile query:
- excludes self
- excludes banned/suspended/hidden profiles
- excludes already matched users
- excludes profiles the current user already liked
- penalizes previously skipped profiles
- prefers compatibility score
- prefers recently active users

Compatibility score currently considers:
- `interested_in` vs target `gender`
- target `interested_in` vs current `gender`
- same region bonus

## Localization System

Localization lives in:
- `app/locales/en.py`
- `app/locales/my.py`

The `I18n` service resolves keys like:
- `welcome`
- `choose_language`
- `liked_successfully`
- `mutual_match_found`
- `banned_notice`
- `maintenance_mode`

All source code and comments stay in English. User-facing text is English/Burmese only.

## Admin System

Admins come from `ADMIN_IDS`.

Admin features:
- `/admin`
- bot stats
- recent signups
- recently active users
- search by Telegram ID or username
- ban/unban
- suspend/unsuspend
- hide/unhide discovery profile
- review/dismiss reports
- broadcast message
- maintenance mode toggle

## Health Endpoint

- `GET /health`
- returns JSON: `{"status": "ok"}`

This is useful for:
- Render health checks
- uptime monitors
- zero-downtime deploy validation

## Sample User Flow (English)

1. `/start`
2. Choose language
3. If username missing, bot blocks matchmaking until it exists
4. Complete profile
5. Open `Browse Profiles`
6. Press `Like` or `Next`
7. If another user later likes back, both receive a match notification
8. Bot reveals `@username`
9. Users chat directly on Telegram

## Sample User Flow (Burmese)

1. `/start`
2. ဘာသာစကားရွေး
3. Username မရှိရင် bot က matchmaking ကိုမပေးသေးဘူး
4. Profile ဖြည့်
5. `Profile ရှာမယ်` ကိုနှိပ်
6. `Like` သို့ `ကျော်မယ်` ကိုရွေး
7. နောက်မှ တစ်ဖက်လူက ပြန် Like လုပ်ရင် match notification ရမယ်
8. `@username` ကို ပြမယ်
9. Telegram ထဲမှာ တိုက်ရိုက် စကားပြောမယ်

## Sample Admin Flow

1. Admin sends `/admin`
2. Opens stats
3. Searches user by ID or username
4. Reviews user state
5. Ban / suspend / hide profile if needed
6. Reviews open reports
7. Sends broadcast when necessary
8. Toggles maintenance mode during updates

## Production Notes

- This project is designed for a **single-instance deployment**.
- For horizontal scaling, move the rate limiter and FSM storage to Redis.
- If you want stronger moderation, add:
  - blocked users list
  - age range preferences
  - region filters
  - profanity filtering
  - admin reason capture UI
  - export jobs
