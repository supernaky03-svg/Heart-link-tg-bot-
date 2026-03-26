# Telegram Match Bot Full Source

## `.env.example`

```dotenv
BOT_TOKEN=1234567890:replace_me
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
ADMIN_IDS=123456789,987654321
BOT_USERNAME=my_match_bot
PORT=10000
HOST=0.0.0.0
USE_WEBHOOK=false
WEBHOOK_BASE_URL=https://your-app.onrender.com
WEBHOOK_PATH=/webhook
DEFAULT_LANGUAGE=en
LOG_LEVEL=INFO
MAX_BIO_LENGTH=280
MAX_NICKNAME_LENGTH=32
MAX_INTERESTS_LENGTH=120
```

## `.python-version`

```
3.11.11
```

## `Procfile`

```bash
web: python main.py
```

## `README.md`

```markdown
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
```

## `render.yaml`

```yaml
services:
  - type: web
    name: telegram-match-bot
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.11
      - key: BOT_TOKEN
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: ADMIN_IDS
        sync: false
      - key: BOT_USERNAME
        sync: false
      - key: PORT
        value: "10000"
      - key: HOST
        value: 0.0.0.0
      - key: USE_WEBHOOK
        value: "false"
      - key: WEBHOOK_BASE_URL
        sync: false
      - key: WEBHOOK_PATH
        value: /webhook
      - key: DEFAULT_LANGUAGE
        value: en
      - key: LOG_LEVEL
        value: INFO
```

## `requirements.txt`

```
aiogram==3.26.0
aiohttp==3.12.14
asyncpg==0.30.0
python-dotenv==1.1.1
```

## `main.py`

```python
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import load_settings
from app.db.database import Database
from app.handlers import include_routers
from app.middlewares.user_context import UserContextMiddleware
from app.repositories.likes import LikeRepository
from app.repositories.reports import ReportRepository
from app.repositories.settings import SettingsRepository
from app.repositories.users import UserRepository
from app.services.app_context import AppContext
from app.services.i18n import I18n
from app.services.rate_limit import SlidingWindowRateLimiter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("main")


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_http_app(app: web.Application, host: str, port: int) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info("HTTP server started on %s:%s", host, port)
    return runner


async def build_app() -> tuple[Bot, Dispatcher, AppContext, Database]:
    settings = load_settings()
    db = Database(settings)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    app_context = AppContext(
        bot=bot,
        settings=settings,
        db=db,
        users=UserRepository(db),
        likes=LikeRepository(db),
        reports=ReportRepository(db),
        app_settings=SettingsRepository(db),
        i18n=I18n(settings.default_language),
        rate_limiter=SlidingWindowRateLimiter(),
    )

    dp = Dispatcher()
    dp["app"] = app_context
    user_context = UserContextMiddleware()
    dp.message.middleware(user_context)
    dp.callback_query.middleware(user_context)
    include_routers(dp)
    return bot, dp, app_context, db


async def run_polling(bot: Bot, dp: Dispatcher, app_context: AppContext) -> None:
    await bot.delete_webhook(drop_pending_updates=False)
    health_app = web.Application()
    health_app.router.add_get("/health", health)
    runner = await start_http_app(health_app, app_context.settings.host, app_context.settings.port)
    try:
        logger.info("Starting long polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()


async def run_webhook(bot: Bot, dp: Dispatcher, app_context: AppContext) -> None:
    if not app_context.settings.webhook_url:
        raise RuntimeError("WEBHOOK_BASE_URL must be set when USE_WEBHOOK=true")

    web_app = web.Application()
    web_app.router.add_get("/health", health)
    request_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    request_handler.register(web_app, path=app_context.settings.webhook_path)
    setup_application(web_app, dp, bot=bot)

    await bot.set_webhook(url=app_context.settings.webhook_url)
    runner = await start_http_app(web_app, app_context.settings.host, app_context.settings.port)
    try:
        logger.info("Webhook mode started at %s", app_context.settings.webhook_url)
        stop_event = asyncio.Event()
        await stop_event.wait()
    finally:
        with suppress(Exception):
            await bot.delete_webhook(drop_pending_updates=False)
        await runner.cleanup()


async def main() -> None:
    bot, dp, app_context, db = await build_app()
    try:
        if app_context.settings.use_webhook:
            await run_webhook(bot, dp, app_context)
        else:
            await run_polling(bot, dp, app_context)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
```

## `app/__init__.py`

```python

```

## `app/config.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet

from dotenv import load_dotenv


load_dotenv()


TRUE_VALUES = {"1", "true", "yes", "on"}


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


@dataclass(slots=True, frozen=True)
class Settings:
    bot_token: str
    database_url: str
    admin_ids: FrozenSet[int]
    bot_username: str
    port: int
    host: str
    use_webhook: bool
    webhook_base_url: str
    webhook_path: str
    default_language: str
    log_level: str
    max_bio_length: int
    max_nickname_length: int
    max_interests_length: int

    @property
    def webhook_url(self) -> str:
        base = self.webhook_base_url.rstrip("/")
        if not base:
            return ""
        return f"{base}{self.webhook_path}"



def load_settings() -> Settings:
    admin_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = frozenset(
        int(chunk.strip())
        for chunk in admin_raw.split(",")
        if chunk.strip().isdigit()
    )

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        admin_ids=admin_ids,
        bot_username=os.getenv("BOT_USERNAME", "").strip(),
        port=int(os.getenv("PORT", "10000")),
        host=os.getenv("HOST", "0.0.0.0"),
        use_webhook=_to_bool(os.getenv("USE_WEBHOOK"), False),
        webhook_base_url=os.getenv("WEBHOOK_BASE_URL", "").strip(),
        webhook_path=os.getenv("WEBHOOK_PATH", "/webhook").strip() or "/webhook",
        default_language=os.getenv("DEFAULT_LANGUAGE", "en").strip() or "en",
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_bio_length=int(os.getenv("MAX_BIO_LENGTH", "280")),
        max_nickname_length=int(os.getenv("MAX_NICKNAME_LENGTH", "32")),
        max_interests_length=int(os.getenv("MAX_INTERESTS_LENGTH", "120")),
    )
```

## `app/config/__init__.py`

```python

```

## `app/db/__init__.py`

```python

```

## `app/db/database.py`

```python
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import asyncpg

from app.config import Settings


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool: asyncpg.Pool | None = None

    async def connect(self, retries: int = 8, base_delay: float = 1.5) -> None:
        attempt = 0
        last_error: Exception | None = None
        while attempt < retries:
            attempt += 1
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.settings.database_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    server_settings={"application_name": "telegram_match_bot"},
                )
                await self._init_schema()
                logger.info("Database connection established")
                return
            except Exception as exc:  # pragma: no cover - startup resilience
                last_error = exc
                logger.exception("Database connection failed on attempt %s/%s", attempt, retries)
                await asyncio.sleep(base_delay * attempt)
        raise RuntimeError("Could not connect to the database") from last_error

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        sql = schema_path.read_text(encoding="utf-8")
        async with self.pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(sql)

    def _require_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self.pool

    async def execute(self, query: str, *args: Any) -> str:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        pool = self._require_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def acquire(self) -> asyncpg.Connection:
        pool = self._require_pool()
        return await pool.acquire()

    async def release(self, conn: asyncpg.Connection) -> None:
        pool = self._require_pool()
        await pool.release(conn)
```

## `app/db/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    language_chosen BOOLEAN NOT NULL DEFAULT FALSE,
    nickname TEXT,
    age INT,
    gender TEXT,
    interested_in TEXT,
    region TEXT,
    bio TEXT,
    interests JSONB NOT NULL DEFAULT '[]'::jsonb,
    profile_photo_file_id TEXT,
    is_profile_complete BOOLEAN NOT NULL DEFAULT FALSE,
    is_banned BOOLEAN NOT NULL DEFAULT FALSE,
    is_suspended BOOLEAN NOT NULL DEFAULT FALSE,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    notification_matches BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_language CHECK (language IN ('en', 'my')),
    CONSTRAINT chk_users_age CHECK (age IS NULL OR age BETWEEN 18 AND 80),
    CONSTRAINT chk_users_gender CHECK (gender IS NULL OR gender IN ('male', 'female', 'non_binary', 'other')),
    CONSTRAINT chk_users_interested_in CHECK (interested_in IS NULL OR interested_in IN ('male', 'female', 'non_binary', 'other', 'any'))
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS language_chosen BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_matches BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_photo_file_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS interests JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS likes (
    id BIGSERIAL PRIMARY KEY,
    from_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_like_pair UNIQUE (from_user_id, to_user_id),
    CONSTRAINT chk_like_self CHECK (from_user_id <> to_user_id),
    CONSTRAINT chk_like_status CHECK (status IN ('pending', 'matched', 'ignored'))
);

CREATE TABLE IF NOT EXISTS skips (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skipped_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_skip_self CHECK (user_id <> skipped_user_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id BIGSERIAL PRIMARY KEY,
    user1_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_match_pair UNIQUE (user1_id, user2_id),
    CONSTRAINT chk_match_order CHECK (user1_id < user2_id),
    CONSTRAINT chk_match_status CHECK (status IN ('active', 'hidden', 'blocked'))
);

CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    reporter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    CONSTRAINT chk_report_status CHECK (status IN ('open', 'reviewed', 'dismissed', 'actioned'))
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    target_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_action_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_users_profile_complete ON users (is_profile_complete, is_banned, is_suspended, is_hidden);
CREATE INDEX IF NOT EXISTS idx_users_last_seen_at ON users (last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_likes_from_user ON likes (from_user_id);
CREATE INDEX IF NOT EXISTS idx_likes_to_user ON likes (to_user_id);
CREATE INDEX IF NOT EXISTS idx_likes_status ON likes (status);

CREATE INDEX IF NOT EXISTS idx_skips_user_target ON skips (user_id, skipped_user_id);
CREATE INDEX IF NOT EXISTS idx_matches_pair ON matches (user1_id, user2_id);
CREATE INDEX IF NOT EXISTS idx_reports_status_created ON reports (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_type_created ON user_action_logs (user_id, action_type, created_at DESC);

INSERT INTO app_settings(key, value)
VALUES ('maintenance_mode', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;
```

## `app/filters/__init__.py`

```python

```

## `app/filters/admin.py`

```python
from __future__ import annotations

from typing import Any

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.app_context import AppContext


class AdminFilter(Filter):
    async def __call__(self, event: TelegramObject, app: AppContext, **kwargs: Any) -> bool:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return False
        user = await app.users.get_by_telegram_id(from_user.id)
        return bool(user and user.get("is_admin"))
```

## `app/handlers/__init__.py`

```python
from aiogram import Dispatcher

from app.handlers.admin.panel import router as admin_router
from app.handlers.errors import router as errors_router
from app.handlers.user.browse import router as browse_router
from app.handlers.user.matches import router as matches_router
from app.handlers.user.menu import router as menu_router
from app.handlers.user.profile import router as profile_router
from app.handlers.user.settings import router as settings_router
from app.handlers.user.start import router as start_router


def include_routers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(settings_router)
    dp.include_router(browse_router)
    dp.include_router(matches_router)
    dp.include_router(admin_router)
    dp.include_router(menu_router)
    dp.include_router(errors_router)
```

## `app/handlers/admin/__init__.py`

```python

```

## `app/handlers/admin/panel.py`

```python
from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.filters.admin import AdminFilter
from app.keyboards.inline import admin_panel_keyboard, admin_user_actions_keyboard, report_review_keyboard
from app.services.admin import collect_stats
from app.services.app_context import AppContext
from app.utils.formatters import admin_user_card, report_card
from app.utils.states import AdminBroadcastFlow, AdminSearchFlow


router = Router(name="admin_panel")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def command_admin(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    maintenance_enabled = await app.app_settings.is_maintenance_mode()
    await message.answer(
        app.i18n.t(db_user.get("language"), "admin_panel"),
        reply_markup=admin_panel_keyboard(app.i18n, db_user.get("language"), maintenance_enabled),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    stats = await collect_stats(app)
    recent_signups = await app.users.list_recent_signups(limit=5)
    recent_active = await app.users.list_recently_active(limit=5)
    text = app.i18n.t(db_user.get("language"), "admin_stats_text", **stats)
    if recent_signups:
        text += "\n\n<b>Recent signups</b>\n" + "\n".join(
            f"• {user.get('nickname') or user.get('first_name') or 'Unknown'} (@{user.get('username') or '-'})"
            for user in recent_signups
        )
    if recent_active:
        text += "\n\n<b>Recently active</b>\n" + "\n".join(
            f"• {user.get('nickname') or user.get('first_name') or 'Unknown'} (@{user.get('username') or '-'})"
            for user in recent_active
        )
    await callback.message.answer(text)


@router.callback_query(F.data == "admin:search")
async def admin_search(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminSearchFlow.waiting_query)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "admin_user_prompt"))


@router.message(AdminSearchFlow.waiting_query)
async def admin_search_input(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    query = (message.text or "").strip()
    user = None
    if query.isdigit():
        user = await app.users.search_by_telegram_id(int(query))
    else:
        user = await app.users.search_by_username(query)
    await state.clear()
    if not user:
        await message.answer(app.i18n.t(db_user.get("language"), "admin_user_not_found"))
        return
    await message.answer(
        admin_user_card(user),
        reply_markup=admin_user_actions_keyboard(app.i18n, db_user.get("language"), user),
    )


@router.callback_query(F.data.startswith("admin_user:"))
async def admin_user_action(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    _, action, target_id_str = callback.data.split(":", 2)
    target_id = int(target_id_str)
    target = await app.users.get_by_id(target_id)
    if not target:
        await callback.answer(app.i18n.t(db_user.get("language"), "admin_user_not_found"), show_alert=True)
        return

    if action == "ban_toggle":
        await app.users.set_ban(target_id, not bool(target.get("is_banned")))
        await app.users.log_admin_action(db_user["id"], target_id, "ban_toggle")
    elif action == "suspend_toggle":
        await app.users.set_suspend(target_id, not bool(target.get("is_suspended")))
        await app.users.log_admin_action(db_user["id"], target_id, "suspend_toggle")
    elif action == "hide_toggle":
        await app.users.set_hidden(target_id, not bool(target.get("is_hidden")))
        await app.users.log_admin_action(db_user["id"], target_id, "hide_toggle")
    updated = await app.users.get_by_id(target_id)
    await callback.answer(app.i18n.t(db_user.get("language"), "admin_action_done"))
    if updated:
        await callback.message.answer(
            admin_user_card(updated),
            reply_markup=admin_user_actions_keyboard(app.i18n, db_user.get("language"), updated),
        )


@router.callback_query(F.data == "admin:reports")
async def admin_reports(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    reports = await app.reports.list_open_reports(limit=10)
    if not reports:
        await callback.message.answer(app.i18n.t(db_user.get("language"), "no_open_reports"))
        return
    await callback.message.answer(app.i18n.t(db_user.get("language"), "recent_reports"))
    for report in reports:
        await callback.message.answer(report_card(report), reply_markup=report_review_keyboard(report["id"]))


@router.callback_query(F.data.startswith("admin_report:"))
async def admin_report_action(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    _, action, report_id_str = callback.data.split(":", 2)
    report_id = int(report_id_str)
    report = await app.reports.get_report(report_id)
    if not report:
        await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
        return
    status = "reviewed" if action == "review" else "dismissed"
    await app.reports.review_report(report_id, db_user["id"], status)
    await app.users.log_admin_action(db_user["id"], report["target_user_id"], f"report_{status}")
    await callback.answer(app.i18n.t(db_user.get("language"), "admin_action_done"))


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminBroadcastFlow.waiting_message)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "admin_broadcast_prompt"))


@router.message(AdminBroadcastFlow.waiting_message)
async def admin_broadcast_message(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    text = (message.text or "").strip()
    await state.clear()
    sent = 0
    failed = 0
    for user in await app.users.iterate_broadcast_targets():
        if user.get("is_suspended"):
            continue
        try:
            await app.bot.send_message(user["telegram_id"], text)  # type: ignore[attr-defined]
            sent += 1
        except Exception:
            failed += 1
    await app.users.log_admin_action(db_user["id"], None, "broadcast", metadata={"sent": sent, "failed": failed})
    await message.answer(app.i18n.t(db_user.get("language"), "admin_broadcast_done", sent=sent, failed=failed))


@router.callback_query(F.data == "admin:maintenance_toggle")
async def admin_toggle_maintenance(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    current = await app.app_settings.is_maintenance_mode()
    new_value = not current
    await app.app_settings.set_maintenance_mode(new_value)
    await app.users.log_admin_action(db_user["id"], None, "maintenance_toggle", metadata={"enabled": new_value})
    await callback.answer(app.i18n.t(db_user.get("language"), "maintenance_enabled" if new_value else "maintenance_disabled"))
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "admin_panel"),
        reply_markup=admin_panel_keyboard(app.i18n, db_user.get("language"), new_value),
    )
```

## `app/handlers/common.py`

```python
from __future__ import annotations

from typing import Any

from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import username_recheck_keyboard
from app.keyboards.reply import main_menu_keyboard
from app.services.app_context import AppContext
from app.services.guards import can_use_bot, has_username


async def send_main_menu(message: Message, app: AppContext, user: dict[str, Any]) -> None:
    language = user.get("language", app.settings.default_language)
    await message.answer(
        app.i18n.t(language, "main_menu_hint"),
        reply_markup=main_menu_keyboard(app.i18n, language),
    )


async def ensure_allowed_message(message: Message, app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> bool:
    allowed, reason_key = await can_use_bot(app, user, admin_bypass=admin_bypass)
    if not allowed and reason_key:
        await message.answer(app.i18n.t(user.get("language"), reason_key))
        return False
    return True


async def ensure_allowed_callback(callback: CallbackQuery, app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> bool:
    allowed, reason_key = await can_use_bot(app, user, admin_bypass=admin_bypass)
    if not allowed and reason_key:
        await callback.answer(app.i18n.t(user.get("language"), reason_key), show_alert=True)
        return False
    return True


async def ensure_username_or_prompt(message: Message, app: AppContext, user: dict[str, Any]) -> bool:
    language = user.get("language")
    if has_username(user):
        return True
    await message.answer(
        app.i18n.t(language, "username_required"),
        reply_markup=username_recheck_keyboard(app.i18n, language),
    )
    return False
```

## `app/handlers/errors.py`

```python
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent


logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled update error", exc_info=event.exception)
    return True
```

## `app/handlers/user/__init__.py`

```python

```

## `app/handlers/user/browse.py`

```python
from __future__ import annotations

from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.exceptions import TelegramBadRequest

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import browse_keyboard, report_reason_keyboard
from app.services.app_context import AppContext
from app.services.discovery import next_candidate
from app.utils.formatters import profile_card
from app.utils.states import ReportFlow


router = Router(name="user_browse")


async def send_candidate(message: Message, app: AppContext, user: dict[str, Any]) -> None:
    candidate = await next_candidate(app, user["id"])
    language = user.get("language")
    if not candidate:
        await message.answer(app.i18n.t(language, "no_profiles_found"))
        return
    text = f"{app.i18n.t(language, 'browse_intro')}\n\n{profile_card(candidate)}"
    keyboard = browse_keyboard(app.i18n, language, candidate["id"])
    if candidate.get("profile_photo_file_id"):
        await message.answer_photo(candidate["profile_photo_file_id"], caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


def match_keyboard(language: str, app: AppContext, username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=app.i18n.t(language, "open_telegram"), url=f"https://t.me/{username}")]
        ]
    )


async def notify_match(app: AppContext, liker: dict[str, Any], other: dict[str, Any]) -> None:
    for receiver, counterpart in ((liker, other), (other, liker)):
        if not receiver.get("notification_matches", True):
            continue
        language = receiver.get("language")
        username = counterpart.get("username")
        nickname = counterpart.get("nickname") or counterpart.get("first_name") or "Match"
        if not username:
            await app.db.execute(
                "INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason) VALUES (NULL, $1, 'match_username_missing', $2)",
                counterpart["id"],
                f"Counterpart username missing for matched user {receiver['id']}",
            )
            continue
        try:
            await app.bot.send_message(  # type: ignore[attr-defined]
                receiver["telegram_id"],
                app.i18n.t(language, "match_card", nickname=escape(nickname), username=f"@{username}"),
                reply_markup=match_keyboard(language, app, username),
            )
        except Exception:
            # Best effort notification; user can still see it in My Matches.
            pass


@router.message(Command("browse"))
async def command_browse(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not await ensure_username_or_prompt(message, app, db_user):
        return
    if not db_user.get("is_profile_complete"):
        await message.answer(app.i18n.t(db_user.get("language"), "profile_incomplete"))
        return
    ok, _ = app.rate_limiter.hit(db_user["id"], "browse_open", 8, 10)
    if not ok:
        await message.answer(app.i18n.t(db_user.get("language"), "rate_limited"))
        return
    await send_candidate(message, app, db_user)


@router.callback_query(F.data == "browse:back")
async def browse_back(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    await callback.answer()
    await send_main_menu(callback.message, app, db_user)


@router.callback_query(F.data.startswith("browse:skip:"))
async def browse_skip(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "skip", 30, 60)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await app.likes.create_skip(db_user["id"], target_id)
    await app.likes.log_action(db_user["id"], "skip")
    await callback.answer()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_candidate(callback.message, app, db_user)


@router.callback_query(F.data.startswith("browse:like:"))
async def browse_like(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "like", 20, 60)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await app.likes.log_action(db_user["id"], "like")
    recent_like_count = await app.likes.count_recent_actions(db_user["id"], "like", 3600)
    if recent_like_count > 80:
        await app.users.set_suspend(db_user["id"], True)
        await callback.answer(app.i18n.t(db_user.get("language"), "suspicious_activity_suspended"), show_alert=True)
        return

    result = await app.likes.process_like(db_user["id"], target_id)
    target = await app.users.get_by_id(target_id)
    await callback.answer()

    if result["result"] in {"pending", "already_liked"}:
        await callback.message.answer(
            app.i18n.t(db_user.get("language"), "liked_successfully" if result["result"] == "pending" else "already_liked")
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await send_candidate(callback.message, app, db_user)
        return

    if result["result"] in {"matched", "already_matched"}:
        if target and target.get("username"):
            text_key = "mutual_match_found" if result["result"] == "matched" else "already_matched"
            if text_key == "mutual_match_found":
                await callback.message.answer(
                    app.i18n.t(db_user.get("language"), text_key, username=f"@{target['username']}"),
                    reply_markup=match_keyboard(db_user.get("language"), app, target["username"]),
                )
            else:
                await callback.message.answer(app.i18n.t(db_user.get("language"), text_key))
        elif target:
            await callback.message.answer(app.i18n.t(db_user.get("language"), "username_revealed_missing"))
        if result["result"] == "matched" and target:
            await notify_match(app, db_user, target)
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await send_candidate(callback.message, app, db_user)
        return

    await callback.message.answer(app.i18n.t(db_user.get("language"), "callback_expired"))


@router.callback_query(F.data.startswith("browse:report:"))
async def browse_report(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    allowed, _ = app.rate_limiter.hit(db_user["id"], "report", 5, 300)
    if not allowed:
        await callback.answer(app.i18n.t(db_user.get("language"), "report_rate_limited"), show_alert=True)
        return
    target_id = int(callback.data.rsplit(":", 1)[1])
    await state.set_state(ReportFlow.waiting_reason_text)
    await state.update_data(report_target_id=target_id)
    await callback.answer()
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "report_select_reason"),
        reply_markup=report_reason_keyboard(app.i18n, db_user.get("language"), target_id),
    )


@router.callback_query(F.data.startswith("report_reason:"))
async def report_reason(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    _, target_id_str, reason = callback.data.split(":", 2)
    target_id = int(target_id_str)
    await callback.answer()
    if reason == "other":
        await state.set_state(ReportFlow.waiting_reason_text)
        await state.update_data(report_target_id=target_id)
        await callback.message.answer(app.i18n.t(db_user.get("language"), "report_other_reason"))
        return
    await app.reports.create_report(db_user["id"], target_id, reason)
    await state.clear()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "report_success"))


@router.message(ReportFlow.waiting_reason_text)
async def report_free_text(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    target_id = data.get("report_target_id")
    if not target_id:
        await state.clear()
        await message.answer(app.i18n.t(db_user.get("language"), "callback_expired"))
        return
    details = (message.text or "").strip()[:300]
    await app.reports.create_report(db_user["id"], int(target_id), "other", details)
    await state.clear()
    await message.answer(app.i18n.t(db_user.get("language"), "report_success"))
```

## `app/handlers/user/matches.py`

```python
from __future__ import annotations

from html import escape
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.common import ensure_allowed_message
from app.services.app_context import AppContext


router = Router(name="user_matches")


@router.message(Command("matches"))
async def command_matches(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    matches = await app.likes.list_matches_for_user(db_user["id"])
    if not matches:
        await message.answer(app.i18n.t(db_user.get("language"), "matches_empty"))
        return
    lines = [f"<b>{app.i18n.t(db_user.get('language'), 'matches_title')}</b>"]
    for match in matches[:20]:
        username = match.get("username")
        nickname = match.get("nickname") or "Match"
        tg = f"@{escape(username)}" if username else "-"
        lines.append(f"• <b>{escape(nickname)}</b> — {tg} — {escape(str(match.get('match_created_at'))[:16])}")
    await message.answer("\n".join(lines))
```

## `app/handlers/user/menu.py`

```python
from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.handlers.common import ensure_allowed_message
from app.filters.admin import AdminFilter
from app.handlers.user.browse import command_browse
from app.handlers.user.matches import command_matches
from app.handlers.user.profile import command_profile
from app.handlers.user.settings import command_settings
from app.handlers.user.start import command_help
from app.services.app_context import AppContext


router = Router(name="user_menu")


@router.message(Command("admin"), ~AdminFilter())
async def admin_denied(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if db_user.get("is_admin"):
        return
    await message.answer(app.i18n.t(db_user.get("language"), "admin_only"))


@router.message()
async def menu_router(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    text = (message.text or "").strip()
    labels = app.i18n.localized_menu_labels()
    if text in labels["browse_profiles"]:
        await command_browse(message, app, db_user)
        return
    if text in labels["my_profile"]:
        await command_profile(message, app, db_user)
        return
    if text in labels["my_matches"]:
        await command_matches(message, app, db_user)
        return
    if text in labels["settings"]:
        await command_settings(message, app, db_user)
        return
    if text in labels["help"]:
        await command_help(message, app, db_user)
        return
    await message.answer(app.i18n.t(db_user.get("language"), "unsupported_message"))


@router.callback_query()
async def fallback_callback(callback, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
```

## `app/handlers/user/profile.py`

```python
from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import (
    photo_skip_keyboard,
    profile_confirm_keyboard,
    profile_gender_keyboard,
    profile_interest_keyboard,
)
from app.services.app_context import AppContext
from app.utils.formatters import profile_card
from app.utils.states import ProfileSetup
from app.utils.validators import parse_interests, validate_age, validate_bio, validate_nickname, validate_region


router = Router(name="user_profile")


async def begin_profile_setup(message: Message, app: AppContext, user: dict[str, Any], state: FSMContext, restart: bool = False) -> None:
    if restart:
        await state.clear()
    await state.set_state(ProfileSetup.nickname)
    await message.answer(app.i18n.t(user.get("language"), "ask_nickname"))


@router.message(Command("profile"))
async def command_profile(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not db_user.get("is_profile_complete"):
        await message.answer(app.i18n.t(db_user.get("language"), "profile_incomplete"))
        return
    await message.answer(profile_card(db_user))


@router.message(Command("editprofile"))
async def command_edit_profile(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    if not await ensure_username_or_prompt(message, app, db_user):
        return
    await begin_profile_setup(message, app, db_user, state, restart=True)


@router.message(ProfileSetup.nickname)
async def profile_nickname(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    nickname = (message.text or "").strip()
    if not validate_nickname(nickname, max_len=app.settings.max_nickname_length):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_nickname"))
        return
    await state.update_data(nickname=nickname)
    await state.set_state(ProfileSetup.age)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_age"))


@router.message(ProfileSetup.age)
async def profile_age(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    age = validate_age(message.text or "")
    if age is None:
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_age"))
        return
    await state.update_data(age=age)
    await state.set_state(ProfileSetup.gender)
    await message.answer(
        app.i18n.t(db_user.get("language"), "ask_gender"),
        reply_markup=profile_gender_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.gender, F.data.startswith("profile_gender:"))
async def profile_gender(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    await state.set_state(ProfileSetup.interested_in)
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "ask_interested_in"),
        reply_markup=profile_interest_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.interested_in, F.data.startswith("profile_interest:"))
async def profile_interest(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    interested_in = callback.data.split(":", 1)[1]
    await state.update_data(interested_in=interested_in)
    await state.set_state(ProfileSetup.region)
    await callback.message.answer(app.i18n.t(db_user.get("language"), "ask_region"))


@router.message(ProfileSetup.region)
async def profile_region(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    region = (message.text or "").strip()
    if not validate_region(region):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_region"))
        return
    await state.update_data(region=region)
    await state.set_state(ProfileSetup.bio)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_bio"))


@router.message(ProfileSetup.bio)
async def profile_bio(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    bio = (message.text or "").strip()
    if not validate_bio(bio, max_len=app.settings.max_bio_length):
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_bio"))
        return
    await state.update_data(bio=bio)
    await state.set_state(ProfileSetup.interests)
    await message.answer(app.i18n.t(db_user.get("language"), "ask_interests"))


@router.message(ProfileSetup.interests)
async def profile_interests(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    interests = parse_interests(message.text or "")
    if not interests:
        await message.answer(app.i18n.t(db_user.get("language"), "invalid_interests"))
        return
    await state.update_data(interests=interests)
    await state.set_state(ProfileSetup.photo)
    await message.answer(
        app.i18n.t(db_user.get("language"), "ask_photo"),
        reply_markup=photo_skip_keyboard(app.i18n, db_user.get("language")),
    )


@router.message(ProfileSetup.photo, F.photo)
async def profile_photo(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    photo = message.photo[-1]
    await state.update_data(profile_photo_file_id=photo.file_id)
    await show_profile_confirmation(message, app, db_user, state)


@router.callback_query(ProfileSetup.photo, F.data == "profile_skip_photo")
async def profile_skip_photo(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(profile_photo_file_id=None)
    await show_profile_confirmation(callback.message, app, db_user, state)


async def show_profile_confirmation(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    preview = {
        **db_user,
        **data,
    }
    await state.set_state(ProfileSetup.confirm)
    await message.answer(app.i18n.t(db_user.get("language"), "confirm_profile_text"))
    await message.answer(
        profile_card(preview),
        reply_markup=profile_confirm_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(ProfileSetup.confirm, F.data == "profile_confirm")
async def profile_confirm(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    data = await state.get_data()
    saved = await app.users.set_profile(
        callback.from_user.id,
        nickname=data["nickname"],
        age=int(data["age"]),
        gender=data["gender"],
        interested_in=data["interested_in"],
        region=data["region"],
        bio=data["bio"],
        interests=data["interests"],
        profile_photo_file_id=data.get("profile_photo_file_id"),
    )
    await state.clear()
    await callback.answer()
    if saved:
        await callback.message.answer(app.i18n.t(saved.get("language"), "profile_saved"))
        await send_main_menu(callback.message, app, saved)


@router.callback_query(F.data == "profile_restart")
async def profile_restart(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await begin_profile_setup(callback.message, app, db_user, state, restart=True)


@router.callback_query(F.data == "profile_cancel")
async def profile_cancel(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "profile_edit_cancelled"))
    await send_main_menu(callback.message, app, db_user)
```

## `app/handlers/user/settings.py`

```python
from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt
from app.handlers.user.profile import begin_profile_setup
from app.keyboards.inline import language_keyboard, settings_keyboard, username_recheck_keyboard
from app.services.app_context import AppContext


router = Router(name="user_settings")


@router.message(Command("settings"))
async def command_settings(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    await message.answer(
        app.i18n.t(db_user.get("language"), "settings_title"),
        reply_markup=settings_keyboard(app.i18n, db_user.get("language")),
    )


@router.callback_query(F.data == "settings:language")
async def settings_language(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    await callback.answer()
    await callback.message.answer(app.i18n.t(db_user.get("language"), "choose_language"), reply_markup=language_keyboard(app.i18n))


@router.callback_query(F.data == "settings:edit_profile")
async def settings_edit_profile(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    if not await ensure_allowed_callback(callback, app, db_user):
        return
    if not await ensure_username_or_prompt(callback.message, app, db_user):
        return
    await callback.answer()
    await begin_profile_setup(callback.message, app, db_user, state, restart=True)


@router.callback_query(F.data == "settings:recheck_username")
async def settings_recheck_username(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    refreshed = await app.users.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language=db_user.get("language", app.settings.default_language),
        is_admin=callback.from_user.id in app.settings.admin_ids,
    )
    await callback.answer()
    if refreshed.get("username"):
        await callback.message.answer(app.i18n.t(refreshed.get("language"), "welcome"))
        return
    await callback.message.answer(
        app.i18n.t(refreshed.get("language"), "username_required"),
        reply_markup=username_recheck_keyboard(app.i18n, refreshed.get("language")),
    )


@router.callback_query(F.data == "settings:toggle_notifications")
async def settings_toggle_notifications(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any]) -> None:
    await callback.answer()
    enabled = not bool(db_user.get("notification_matches"))
    await app.users.set_notification_matches(callback.from_user.id, enabled)
    await callback.message.answer(
        app.i18n.t(db_user.get("language"), "notifications_on" if enabled else "notifications_off")
    )
```

## `app/handlers/user/start.py`

```python
from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.handlers.common import ensure_allowed_callback, ensure_allowed_message, ensure_username_or_prompt, send_main_menu
from app.keyboards.inline import language_keyboard, username_recheck_keyboard
from app.services.app_context import AppContext
from app.handlers.user.profile import begin_profile_setup


router = Router(name="user_start")


@router.message(CommandStart())
async def command_start(message: Message, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    user = db_user
    if not user.get("language_chosen"):
        await message.answer(app.i18n.t("en", "choose_language"), reply_markup=language_keyboard(app.i18n))
        return

    await message.answer(app.i18n.t(user["language"], "welcome"))
    if not await ensure_allowed_message(message, app, user):
        return
    if not await ensure_username_or_prompt(message, app, user):
        return
    if not user.get("is_profile_complete"):
        await message.answer(app.i18n.t(user["language"], "start_profile"))
        await begin_profile_setup(message, app, user, state, restart=True)
        return
    await send_main_menu(message, app, user)


@router.message(Command("language"))
async def command_language(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    await message.answer(app.i18n.t(db_user.get("language"), "choose_language"), reply_markup=language_keyboard(app.i18n))


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in {"en", "my"}:
        await callback.answer(app.i18n.t(db_user.get("language"), "callback_expired"), show_alert=True)
        return
    await app.users.update_language(callback.from_user.id, language)
    user = await app.users.get_by_telegram_id(callback.from_user.id)
    await callback.answer(app.i18n.t(language, "language_updated"))
    if user is None:
        return
    if not await ensure_allowed_callback(callback, app, user):
        return
    await callback.message.answer(app.i18n.t(language, "welcome"))
    if not await ensure_username_or_prompt(callback.message, app, user):
        return
    if not user.get("is_profile_complete"):
        await callback.message.answer(app.i18n.t(language, "start_profile"))
        await begin_profile_setup(callback.message, app, user, state, restart=True)
        return
    await send_main_menu(callback.message, app, user)


@router.callback_query(F.data == "recheck_username")
async def recheck_username(callback: CallbackQuery, app: AppContext, db_user: dict[str, Any], state: FSMContext) -> None:
    user = await app.users.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language=db_user.get("language", app.settings.default_language),
        is_admin=callback.from_user.id in app.settings.admin_ids,
    )
    language = user.get("language")
    if not user.get("username"):
        await callback.answer(app.i18n.t(language, "username_still_missing"), show_alert=True)
        return
    await callback.answer()
    if not user.get("is_profile_complete"):
        await callback.message.answer(app.i18n.t(language, "start_profile"))
        await begin_profile_setup(callback.message, app, user, state, restart=True)
        return
    await send_main_menu(callback.message, app, user)


@router.message(Command("help"))
async def command_help(message: Message, app: AppContext, db_user: dict[str, Any]) -> None:
    if not await ensure_allowed_message(message, app, db_user):
        return
    await message.answer(app.i18n.t(db_user.get("language"), "help_text"))
```

## `app/keyboards/__init__.py`

```python

```

## `app/keyboards/inline.py`

```python
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import I18n


def language_keyboard(i18n: I18n) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
            for code, name in i18n.available_languages()
        ]
    )


def username_recheck_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "username_recheck"), callback_data="recheck_username")]
        ]
    )


def browse_keyboard(i18n: I18n, language: str, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "like"), callback_data=f"browse:like:{target_user_id}"),
                InlineKeyboardButton(text=i18n.t(language, "next"), callback_data=f"browse:skip:{target_user_id}"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "report"), callback_data=f"browse:report:{target_user_id}")],
            [InlineKeyboardButton(text=i18n.t(language, "back_to_menu"), callback_data="browse:back")],
        ]
    )


def profile_gender_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_male"), callback_data="profile_gender:male"),
                InlineKeyboardButton(text=i18n.t(language, "gender_female"), callback_data="profile_gender:female"),
            ],
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_non_binary"), callback_data="profile_gender:non_binary"),
                InlineKeyboardButton(text=i18n.t(language, "gender_other"), callback_data="profile_gender:other"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def profile_interest_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_male"), callback_data="profile_interest:male"),
                InlineKeyboardButton(text=i18n.t(language, "gender_female"), callback_data="profile_interest:female"),
            ],
            [
                InlineKeyboardButton(text=i18n.t(language, "gender_non_binary"), callback_data="profile_interest:non_binary"),
                InlineKeyboardButton(text=i18n.t(language, "gender_other"), callback_data="profile_interest:other"),
            ],
            [InlineKeyboardButton(text=i18n.t(language, "interested_any"), callback_data="profile_interest:any")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def photo_skip_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "skip_photo"), callback_data="profile_skip_photo")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def profile_confirm_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "profile_confirm"), callback_data="profile_confirm")],
            [InlineKeyboardButton(text=i18n.t(language, "profile_restart"), callback_data="profile_restart")],
            [InlineKeyboardButton(text=i18n.t(language, "cancel"), callback_data="profile_cancel")],
        ]
    )


def settings_keyboard(i18n: I18n, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "change_language"), callback_data="settings:language")],
            [InlineKeyboardButton(text=i18n.t(language, "edit_profile"), callback_data="settings:edit_profile")],
            [InlineKeyboardButton(text=i18n.t(language, "recheck_username"), callback_data="settings:recheck_username")],
            [InlineKeyboardButton(text=i18n.t(language, "toggle_match_notifications"), callback_data="settings:toggle_notifications")],
        ]
    )


def report_reason_keyboard(i18n: I18n, language: str, target_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_spam"), callback_data=f"report_reason:{target_user_id}:spam")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_fake"), callback_data=f"report_reason:{target_user_id}:fake_profile")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_harassment"), callback_data=f"report_reason:{target_user_id}:harassment")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_inappropriate"), callback_data=f"report_reason:{target_user_id}:inappropriate_content")],
            [InlineKeyboardButton(text=i18n.t(language, "report_reason_other"), callback_data=f"report_reason:{target_user_id}:other")],
        ]
    )


def admin_panel_keyboard(i18n: I18n, language: str, maintenance_enabled: bool) -> InlineKeyboardMarkup:
    maintenance_text = (
        i18n.t(language, "admin_maintenance_off") if maintenance_enabled else i18n.t(language, "admin_maintenance_on")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(language, "admin_stats"), callback_data="admin:stats")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_search"), callback_data="admin:search")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_reports"), callback_data="admin:reports")],
            [InlineKeyboardButton(text=i18n.t(language, "admin_broadcast"), callback_data="admin:broadcast")],
            [InlineKeyboardButton(text=maintenance_text, callback_data="admin:maintenance_toggle")],
        ]
    )


def admin_user_actions_keyboard(i18n: I18n, language: str, user: dict) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=i18n.t(language, "unban_user") if user.get("is_banned") else i18n.t(language, "ban_user"),
                callback_data=f"admin_user:ban_toggle:{user['id']}",
            ),
            InlineKeyboardButton(
                text=i18n.t(language, "unsuspend_user") if user.get("is_suspended") else i18n.t(language, "suspend_user"),
                callback_data=f"admin_user:suspend_toggle:{user['id']}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=i18n.t(language, "unhide_profile") if user.get("is_hidden") else i18n.t(language, "hide_profile"),
                callback_data=f"admin_user:hide_toggle:{user['id']}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_review_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Review", callback_data=f"admin_report:review:{report_id}"),
                InlineKeyboardButton(text="❌ Dismiss", callback_data=f"admin_report:dismiss:{report_id}"),
            ]
        ]
    )
```

## `app/keyboards/reply.py`

```python
from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.services.i18n import I18n


def main_menu_keyboard(i18n: I18n, language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.t(language, "browse_profiles"))],
            [
                KeyboardButton(text=i18n.t(language, "my_profile")),
                KeyboardButton(text=i18n.t(language, "my_matches")),
            ],
            [
                KeyboardButton(text=i18n.t(language, "settings")),
                KeyboardButton(text=i18n.t(language, "help")),
            ],
        ],
        resize_keyboard=True,
    )
```

## `app/locales/__init__.py`

```python

```

## `app/locales/en.py`

```python
MESSAGES = {
    "lang_name": "English",
    "choose_language": "Choose your language:",
    "language_updated": "Language updated.",
    "welcome": "Welcome to Match Bot — discover people, like profiles, and match only with mutual consent.",
    "username_required": "You need a Telegram username before using matchmaking. Open Telegram Settings → My Profile → Username, set one, then tap the button below.",
    "username_recheck": "I've set my username",
    "username_still_missing": "A username is still missing. Please set it in Telegram and try again.",
    "start_profile": "Let's build your profile.",
    "profile_saved": "Your profile is saved.",
    "profile_incomplete": "Please complete your profile before browsing profiles.",
    "profile_title": "Your profile",
    "browse_profiles": "Browse Profiles",
    "my_profile": "My Profile",
    "my_matches": "My Matches",
    "settings": "Settings",
    "help": "Help",
    "back_to_menu": "Back to Menu",
    "main_menu_hint": "Use the menu below or commands like /browse, /profile, /matches.",
    "no_profiles_found": "No profiles available right now. Please try again later.",
    "browse_intro": "Here is someone you may like:",
    "like": "Like ❤️",
    "next": "Next ➡️",
    "report": "Report 🚩",
    "back": "Back",
    "liked_successfully": "Liked! We'll let you know if they like you back.",
    "already_liked": "You already liked this profile. We'll notify you if they like you back.",
    "waiting_for_like_back": "Your like is saved and waiting for a mutual like.",
    "mutual_match_found": "It's a match! You can now contact them on Telegram: {username}",
    "match_card": "🎉 Match with <b>{nickname}</b>\nTelegram: {username}\nYou can now chat directly on Telegram.",
    "matches_empty": "You have no matches yet.",
    "matches_title": "Your matches",
    "report_select_reason": "Why are you reporting this profile?",
    "report_other_reason": "Please send a short reason for your report.",
    "report_success": "Thanks. Your report has been submitted.",
    "report_rate_limited": "You're reporting too fast. Please slow down and try again later.",
    "banned_notice": "Your account has been banned from using this bot.",
    "suspended_notice": "Your account is temporarily suspended. Please contact support or try again later.",
    "maintenance_mode": "The bot is currently in maintenance mode. Please try again later.",
    "admin_only": "This section is for admins only.",
    "help_text": "Commands:\n/start — start the bot\n/profile — view your profile\n/editprofile — edit your profile\n/browse — browse profiles\n/matches — view matches\n/settings — settings\n/language — change language\n/help — show help",
    "settings_title": "Settings",
    "change_language": "Change Language",
    "edit_profile": "Edit Profile",
    "recheck_username": "Recheck Username",
    "toggle_match_notifications": "Toggle Match Notifications",
    "notifications_on": "Match notifications are now ON.",
    "notifications_off": "Match notifications are now OFF.",
    "cancel": "Cancel",
    "skip_photo": "Skip Photo",
    "profile_confirm": "Confirm Profile",
    "profile_restart": "Restart",
    "ask_nickname": "Enter your nickname or display name.",
    "ask_age": "Enter your age (18-80).",
    "ask_gender": "Choose your gender.",
    "ask_interested_in": "Who are you interested in?",
    "ask_region": "Enter your region or country.",
    "ask_bio": "Write a short bio about yourself.",
    "ask_interests": "Enter a few interests separated by commas. Example: music, travel, gaming",
    "ask_photo": "Send an optional profile photo, or tap Skip Photo.",
    "invalid_age": "Please enter a valid age between 18 and 80.",
    "invalid_nickname": "Nickname must be between 2 and 32 characters.",
    "invalid_region": "Region must be between 2 and 40 characters.",
    "invalid_bio": "Bio must be between 10 and 280 characters.",
    "invalid_interests": "Please add 1 to 8 interests. Keep it short and comma-separated.",
    "gender_male": "Male",
    "gender_female": "Female",
    "gender_non_binary": "Non-binary",
    "gender_other": "Other",
    "interested_any": "Anyone",
    "confirm_profile_text": "Please review your profile before saving:",
    "profile_edit_cancelled": "Profile editing cancelled.",
    "callback_expired": "That action expired. Please try again.",
    "rate_limited": "You're doing that too fast. Please slow down.",
    "open_telegram": "Open Telegram",
    "report_reason_spam": "Spam",
    "report_reason_fake": "Fake profile",
    "report_reason_harassment": "Harassment",
    "report_reason_inappropriate": "Inappropriate content",
    "report_reason_other": "Other",
    "admin_panel": "Admin Panel",
    "admin_stats": "Stats",
    "admin_search": "Search User",
    "admin_reports": "Reports",
    "admin_broadcast": "Broadcast",
    "admin_maintenance_on": "Enable Maintenance",
    "admin_maintenance_off": "Disable Maintenance",
    "admin_user_prompt": "Send a Telegram ID or username (with or without @).",
    "admin_user_not_found": "User not found.",
    "admin_action_done": "Admin action completed.",
    "admin_broadcast_prompt": "Send the broadcast message. It will be delivered to all non-banned users.",
    "admin_broadcast_done": "Broadcast finished. Sent: {sent}, failed: {failed}",
    "admin_stats_text": "<b>Bot stats</b>\nUsers: {total_users}\nComplete profiles: {complete_profiles}\nLikes: {total_likes}\nPending likes: {pending_likes}\nMutual matches: {total_matches}\nReports: {total_reports}\nOpen reports: {open_reports}\nBanned: {banned_users}\nSuspended: {suspended_users}\nActive 24h: {active_users_24h}",
    "maintenance_enabled": "Maintenance mode enabled.",
    "maintenance_disabled": "Maintenance mode disabled.",
    "user_profile_hidden": "The profile was hidden from discovery.",
    "user_profile_unhidden": "The profile is visible in discovery again.",
    "search_result_title": "User details",
    "ban_user": "Ban",
    "unban_user": "Unban",
    "suspend_user": "Suspend",
    "unsuspend_user": "Unsuspend",
    "hide_profile": "Hide Profile",
    "unhide_profile": "Unhide Profile",
    "dismiss_report": "Dismiss Report",
    "mark_report_reviewed": "Mark Reviewed",
    "recent_reports": "Recent open reports",
    "no_open_reports": "There are no open reports.",
    "already_matched": "You're already matched with this person.",
    "unsupported_message": "Please use the buttons or commands so I can help you correctly.",
    "username_revealed_missing": "You matched, but the other user's username is unavailable right now.",
    "report_details_prefix": "Report reason",
    "suspicious_activity_suspended": "Your account has been temporarily suspended due to suspicious activity.",
}
```

## `app/locales/my.py`

```python
MESSAGES = {
    "lang_name": "မြန်မာ",
    "choose_language": "ဘာသာစကားရွေးပါ။",
    "language_updated": "ဘာသာစကား ပြောင်းပြီးပါပြီ။",
    "welcome": "Match Bot မှ ကြိုဆိုပါတယ်။ Profile တွေကြည့်ပြီး Like လုပ်နိုင်ပြီး နှစ်ဖက်လုံး Like လုပ်မှ Match ဖြစ်မယ်။",
    "username_required": "Matchmaking သုံးဖို့ Telegram username လိုအပ်ပါတယ်။ Telegram Settings → My Profile → Username ထဲမှာ username သတ်မှတ်ပြီး အောက်ကခလုတ်ကိုနှိပ်ပါ။",
    "username_recheck": "Username သတ်မှတ်ပြီးပြီ",
    "username_still_missing": "Username မတွေ့သေးပါ။ Telegram ထဲမှာ သတ်မှတ်ပြီး ပြန်စမ်းပါ။",
    "start_profile": "အရင်ဆုံး သင့် profile ကိုဖန်တီးကြရအောင်။",
    "profile_saved": "သင့် profile ကို သိမ်းပြီးပါပြီ။",
    "profile_incomplete": "Profile မပြည့်စုံသေးပါ။ Browse မလုပ်ခင် profile ဖြည့်ပါ။",
    "profile_title": "သင့် profile",
    "browse_profiles": "Profile ရှာမယ်",
    "my_profile": "ကျွန်တော့် Profile",
    "my_matches": "Match တွေ",
    "settings": "Settings",
    "help": "အကူအညီ",
    "back_to_menu": "Menu သို့ပြန်မယ်",
    "main_menu_hint": "အောက်က menu သုံးနိုင်သလို /browse, /profile, /matches လို command တွေလည်း သုံးလို့ရပါတယ်။",
    "no_profiles_found": "လက်ရှိ ပြရန် profile မရှိသေးပါ။ နောက်မှ ပြန်စမ်းပါ။",
    "browse_intro": "ဒီ profile ကိုကြည့်ပါ။",
    "like": "Like ❤️",
    "next": "ကျော်မယ် ➡️",
    "report": "Report 🚩",
    "back": "နောက်သို့",
    "liked_successfully": "Like လုပ်ပြီးပါပြီ။ သူဘက်က ပြန် Like လုပ်ရင် အသိပေးပါမယ်။",
    "already_liked": "ဒီ profile ကို Like လုပ်ပြီးသားပါ။ သူဘက်က ပြန် Like လုပ်ရင် အသိပေးပါမယ်။",
    "waiting_for_like_back": "Like ကို သိမ်းထားပါတယ်။ နှစ်ဖက်လုံး Like ဖြစ်ရင် အသိပေးပါမယ်။",
    "mutual_match_found": "Match ဖြစ်သွားပါပြီ။ Telegram မှာ တိုက်ရိုက်ဆက်သွယ်နိုင်ပါတယ်: {username}",
    "match_card": "🎉 <b>{nickname}</b> နဲ့ Match ဖြစ်သွားပါပြီ။\nTelegram: {username}\nအခု Telegram မှာ တိုက်ရိုက်စကားပြောနိုင်ပါပြီ။",
    "matches_empty": "Match မရှိသေးပါ။",
    "matches_title": "သင့် Match များ",
    "report_select_reason": "ဒီ profile ကို ဘာကြောင့် report လုပ်ချင်တာလဲ။",
    "report_other_reason": "Report အကြောင်းရင်းကို တိုတိုရှင်းရှင်း ရိုက်ပို့ပါ။",
    "report_success": "ကျေးဇူးတင်ပါတယ်။ Report ကို တင်ပြီးပါပြီ။",
    "report_rate_limited": "Report များလွန်းနေပါတယ်။ ခဏနားပြီးမှ ပြန်ကြိုးစားပါ။",
    "banned_notice": "ဒီ bot ကို သုံးခွင့် ပိတ်ထားပါတယ်။",
    "suspended_notice": "သင့် account ကို ယာယီရပ်နားထားပါတယ်။ နောက်မှ ပြန်စမ်းပါ။",
    "maintenance_mode": "Bot ကို ပြင်ဆင်နေပါတယ်။ နောက်မှ ပြန်စမ်းပါ။",
    "admin_only": "ဒီအပိုင်းကို admin များသာ သုံးနိုင်ပါတယ်။",
    "help_text": "Commands:\n/start — bot စမယ်\n/profile — ကိုယ့် profile ကြည့်မယ်\n/editprofile — profile ပြင်မယ်\n/browse — profile ရှာမယ်\n/matches — match တွေကြည့်မယ်\n/settings — settings\n/language — ဘာသာစကားပြောင်းမယ်\n/help — အကူအညီကြည့်မယ်",
    "settings_title": "Settings",
    "change_language": "ဘာသာစကားပြောင်းမယ်",
    "edit_profile": "Profile ပြင်မယ်",
    "recheck_username": "Username ပြန်စစ်မယ်",
    "toggle_match_notifications": "Match အသိပေးချက် ဖွင့်/ပိတ်",
    "notifications_on": "Match အသိပေးချက် ဖွင့်ပြီးပါပြီ။",
    "notifications_off": "Match အသိပေးချက် ပိတ်ပြီးပါပြီ။",
    "cancel": "မလုပ်တော့ဘူး",
    "skip_photo": "ဓာတ်ပုံမထည့်တော့ဘူး",
    "profile_confirm": "အတည်ပြုမယ်",
    "profile_restart": "အစက ပြန်လုပ်မယ်",
    "ask_nickname": "သင့် nickname သို့မဟုတ် display name ကို ရိုက်ပါ။",
    "ask_age": "အသက်ကို ရိုက်ပါ (18-80)။",
    "ask_gender": "ကျား/မ/အခြား ကိုရွေးပါ။",
    "ask_interested_in": "ဘယ်လို profile မျိုးကို စိတ်ဝင်စားသလဲ။",
    "ask_region": "သင့် region သို့မဟုတ် country ကို ရိုက်ပါ။",
    "ask_bio": "ကိုယ့်အကြောင်းတိုတို bio ရေးပါ။",
    "ask_interests": "စိတ်ဝင်စားတာတွေကို comma နဲ့ခွဲပြီးရေးပါ။ ဥပမာ - music, travel, gaming",
    "ask_photo": "Profile photo ပို့ပါ၊ မပို့ချင်ရင် Skip Photo နှိပ်ပါ။",
    "invalid_age": "အသက်ကို 18 မှ 80 အတွင်း မှန်ကန်စွာ ရိုက်ပါ။",
    "invalid_nickname": "Nickname က 2 လုံးမှ 32 လုံးအတွင်း ဖြစ်ရပါမယ်။",
    "invalid_region": "Region က 2 လုံးမှ 40 လုံးအတွင်း ဖြစ်ရပါမယ်။",
    "invalid_bio": "Bio က 10 လုံးမှ 280 လုံးအတွင်း ဖြစ်ရပါမယ်။",
    "invalid_interests": "Interests ကို 1 ခုမှ 8 ခုအတွင်း တိုတိုရေးပါ။",
    "gender_male": "ကျား",
    "gender_female": "မ",
    "gender_non_binary": "Non-binary",
    "gender_other": "အခြား",
    "interested_any": "မည်သူမဆို",
    "confirm_profile_text": "သိမ်းမယ့်အရင် profile ကို စစ်ကြည့်ပါ။",
    "profile_edit_cancelled": "Profile ပြင်ဆင်မှုကို ရပ်လိုက်ပါပြီ။",
    "callback_expired": "ဒီ action က သက်တမ်းကုန်သွားပါပြီ။ ထပ်စမ်းပါ။",
    "rate_limited": "လုပ်ဆောင်မှု မြန်လွန်းနေပါတယ်။ ခဏနားပြီး ပြန်စမ်းပါ။",
    "open_telegram": "Telegram ဖွင့်မယ်",
    "report_reason_spam": "Spam",
    "report_reason_fake": "အတု profile",
    "report_reason_harassment": "အနှောင့်အယှက်",
    "report_reason_inappropriate": "မသင့်တော်သော content",
    "report_reason_other": "အခြား",
    "admin_panel": "Admin Panel",
    "admin_stats": "စာရင်းအင်း",
    "admin_search": "User ရှာမယ်",
    "admin_reports": "Reports",
    "admin_broadcast": "Broadcast",
    "admin_maintenance_on": "Maintenance ဖွင့်မယ်",
    "admin_maintenance_off": "Maintenance ပိတ်မယ်",
    "admin_user_prompt": "Telegram ID သို့မဟုတ် username (@ ပါလည်းရ) ပို့ပါ။",
    "admin_user_not_found": "User မတွေ့ပါ။",
    "admin_action_done": "Admin action ပြီးပါပြီ။",
    "admin_broadcast_prompt": "Broadcast စာကို ပို့ပါ။ Ban မလုပ်ထားတဲ့ user အားလုံးထံ ပို့ပါမယ်။",
    "admin_broadcast_done": "Broadcast ပြီးပါပြီ။ ပို့နိုင်: {sent}, မအောင်မြင်: {failed}",
    "admin_stats_text": "<b>Bot စာရင်းအင်း</b>\nUsers: {total_users}\nComplete profiles: {complete_profiles}\nLikes: {total_likes}\nPending likes: {pending_likes}\nMutual matches: {total_matches}\nReports: {total_reports}\nOpen reports: {open_reports}\nBanned: {banned_users}\nSuspended: {suspended_users}\nActive 24h: {active_users_24h}",
    "maintenance_enabled": "Maintenance mode ဖွင့်ပြီးပါပြီ။",
    "maintenance_disabled": "Maintenance mode ပိတ်ပြီးပါပြီ။",
    "user_profile_hidden": "ဒီ profile ကို discovery ကနေဖျောက်ထားပါတယ်။",
    "user_profile_unhidden": "ဒီ profile ကို discovery မှာ ပြန်မြင်ရပါမယ်။",
    "search_result_title": "User အချက်အလက်",
    "ban_user": "Ban",
    "unban_user": "Unban",
    "suspend_user": "Suspend",
    "unsuspend_user": "Unsuspend",
    "hide_profile": "Profile ဖျောက်မယ်",
    "unhide_profile": "Profile ပြမယ်",
    "dismiss_report": "Report ကိုပယ်မယ်",
    "mark_report_reviewed": "Reviewed လုပ်မယ်",
    "recent_reports": "ဖွင့်ထားဆဲ Reports",
    "no_open_reports": "ဖွင့်ထားဆဲ report မရှိပါ။",
    "already_matched": "ဒီလူနဲ့ Match ဖြစ်ပြီးသားပါ။",
    "unsupported_message": "ကျွန်တော်က မှန်မှန်ကန်ကန်ကူညီနိုင်ဖို့ button ဒါမှမဟုတ် command ကို သုံးပါ။",
    "username_revealed_missing": "Match ဖြစ်သွားပေမယ့် တစ်ဖက်လူရဲ့ username ကို လက်ရှိ မရနိုင်သေးပါ။",
    "report_details_prefix": "Report အကြောင်းရင်း",
    "suspicious_activity_suspended": "သံသယရှိသော activity ကြောင့် သင့် account ကို ယာယီ suspend လုပ်ထားပါတယ်။",
}
```

## `app/middlewares/__init__.py`

```python

```

## `app/middlewares/user_context.py`

```python
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.app_context import AppContext


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        app: AppContext = data["app"]
        from_user = getattr(event, "from_user", None)
        if from_user:
            default_language = app.settings.default_language
            user = await app.users.ensure_user(
                telegram_id=from_user.id,
                username=from_user.username,
                first_name=from_user.first_name,
                language=default_language,
                is_admin=from_user.id in app.settings.admin_ids,
            )
            data["db_user"] = user
        return await handler(event, data)
```

## `app/repositories/__init__.py`

```python

```

## `app/repositories/likes.py`

```python
from __future__ import annotations

from typing import Any

import asyncpg

from app.db.database import Database


class LikeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_likes,
                COUNT(*) FILTER (WHERE status='pending') AS pending_likes,
                COUNT(*) FILTER (WHERE status='matched') AS matched_likes
            FROM likes
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def create_skip(self, user_id: int, skipped_user_id: int) -> None:
        await self.db.execute(
            "INSERT INTO skips (user_id, skipped_user_id) VALUES ($1, $2)",
            user_id,
            skipped_user_id,
        )

    async def log_action(self, user_id: int, action_type: str) -> None:
        await self.db.execute(
            "INSERT INTO user_action_logs (user_id, action_type) VALUES ($1, $2)",
            user_id,
            action_type,
        )

    async def count_recent_actions(self, user_id: int, action_type: str, window_seconds: int) -> int:
        value = await self.db.fetchval(
            """
            SELECT COUNT(*)
            FROM user_action_logs
            WHERE user_id=$1
              AND action_type=$2
              AND created_at >= NOW() - ($3 || ' seconds')::interval
            """,
            user_id,
            action_type,
            window_seconds,
        )
        return int(value or 0)

    async def process_like(self, from_user_id: int, to_user_id: int) -> dict[str, Any]:
        if from_user_id == to_user_id:
            return {"result": "invalid_self"}

        conn = await self.db.acquire()
        try:
            async with conn.transaction():
                # Lock both user rows in a deterministic order to prevent race conditions.
                await conn.fetch(
                    "SELECT id FROM users WHERE id = ANY($1::bigint[]) ORDER BY id FOR UPDATE",
                    [from_user_id, to_user_id],
                )

                current_like = await conn.fetchrow(
                    "SELECT * FROM likes WHERE from_user_id=$1 AND to_user_id=$2 FOR UPDATE",
                    from_user_id,
                    to_user_id,
                )
                reciprocal_like = await conn.fetchrow(
                    "SELECT * FROM likes WHERE from_user_id=$1 AND to_user_id=$2 FOR UPDATE",
                    to_user_id,
                    from_user_id,
                )

                user1_id, user2_id = sorted((from_user_id, to_user_id))
                existing_match = await conn.fetchrow(
                    "SELECT * FROM matches WHERE user1_id=$1 AND user2_id=$2 FOR UPDATE",
                    user1_id,
                    user2_id,
                )

                if existing_match:
                    await conn.execute(
                        """
                        UPDATE likes SET status='matched', updated_at=NOW()
                        WHERE (from_user_id=$1 AND to_user_id=$2) OR (from_user_id=$2 AND to_user_id=$1)
                        """,
                        from_user_id,
                        to_user_id,
                    )
                    return {"result": "already_matched", "match": dict(existing_match)}

                if current_like and not reciprocal_like:
                    return {"result": "already_liked"}

                if not current_like:
                    current_like = await conn.fetchrow(
                        """
                        INSERT INTO likes (from_user_id, to_user_id, status)
                        VALUES ($1, $2, 'pending')
                        RETURNING *
                        """,
                        from_user_id,
                        to_user_id,
                    )

                if reciprocal_like:
                    match_row = await conn.fetchrow(
                        """
                        INSERT INTO matches (user1_id, user2_id, status)
                        VALUES ($1, $2, 'active')
                        ON CONFLICT (user1_id, user2_id) DO UPDATE SET status='active'
                        RETURNING *
                        """,
                        user1_id,
                        user2_id,
                    )
                    await conn.execute(
                        """
                        UPDATE likes SET status='matched', updated_at=NOW()
                        WHERE (from_user_id=$1 AND to_user_id=$2) OR (from_user_id=$2 AND to_user_id=$1)
                        """,
                        from_user_id,
                        to_user_id,
                    )
                    return {
                        "result": "matched",
                        "match": dict(match_row) if match_row else None,
                    }

                return {"result": "pending", "like": dict(current_like)}
        finally:
            await self.db.release(conn)

    async def list_matches_for_user(self, user_id: int) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT
                m.id AS match_id,
                m.created_at AS match_created_at,
                other.id AS other_user_id,
                other.nickname,
                other.username,
                other.region,
                other.age,
                other.gender
            FROM matches m
            JOIN users other
              ON other.id = CASE WHEN m.user1_id=$1 THEN m.user2_id ELSE m.user1_id END
            WHERE (m.user1_id=$1 OR m.user2_id=$1)
              AND m.status='active'
            ORDER BY m.created_at DESC
            """,
            user_id,
        )
        return [dict(row) for row in rows]

    async def discovery_candidate(self, user_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            WITH me AS (
                SELECT * FROM users WHERE id=$1
            )
            SELECT
                u.*,
                (
                    CASE
                        WHEN (SELECT interested_in FROM me) = 'any' THEN 1
                        WHEN u.gender = (SELECT interested_in FROM me) THEN 1
                        ELSE 0
                    END +
                    CASE
                        WHEN u.interested_in = 'any' THEN 1
                        WHEN (SELECT gender FROM me) = u.interested_in THEN 1
                        ELSE 0
                    END +
                    CASE
                        WHEN COALESCE(u.region, '') <> '' AND u.region = (SELECT region FROM me) THEN 1
                        ELSE 0
                    END
                ) AS compatibility_score,
                CASE WHEN s.id IS NULL THEN 0 ELSE 1 END AS skipped_before,
                s.created_at AS last_skipped_at
            FROM users u
            CROSS JOIN me
            LEFT JOIN likes sent_like
                   ON sent_like.from_user_id = (SELECT id FROM me)
                  AND sent_like.to_user_id = u.id
            LEFT JOIN matches m
                   ON (m.user1_id = LEAST((SELECT id FROM me), u.id)
                   AND m.user2_id = GREATEST((SELECT id FROM me), u.id))
            LEFT JOIN LATERAL (
                SELECT id, created_at
                FROM skips
                WHERE user_id=(SELECT id FROM me)
                  AND skipped_user_id=u.id
                ORDER BY created_at DESC
                LIMIT 1
            ) s ON TRUE
            WHERE u.id <> (SELECT id FROM me)
              AND u.is_profile_complete = TRUE
              AND u.is_banned = FALSE
              AND u.is_suspended = FALSE
              AND u.is_hidden = FALSE
              AND sent_like.id IS NULL
              AND m.id IS NULL
            ORDER BY
                compatibility_score DESC,
                skipped_before ASC,
                last_skipped_at ASC NULLS FIRST,
                u.last_seen_at DESC NULLS LAST,
                random()
            LIMIT 1
            """,
            user_id,
        )
        return dict(row) if row else None
```

## `app/repositories/reports.py`

```python
from __future__ import annotations

from typing import Any

from app.db.database import Database


class ReportRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_report(
        self,
        reporter_id: int,
        target_user_id: int,
        reason: str,
        details: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO reports (reporter_id, target_user_id, reason, details)
            VALUES ($1, $2, $3, $4)
            """,
            reporter_id,
            target_user_id,
            reason,
            details,
        )

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_reports,
                COUNT(*) FILTER (WHERE status='open') AS open_reports
            FROM reports
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def list_open_reports(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT
                r.*,
                reporter.username AS reporter_username,
                reporter.nickname AS reporter_nickname,
                target.username AS target_username,
                target.nickname AS target_nickname
            FROM reports r
            JOIN users reporter ON reporter.id = r.reporter_id
            JOIN users target ON target.id = r.target_user_id
            WHERE r.status='open'
            ORDER BY r.created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [dict(row) for row in rows]

    async def get_report(self, report_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            SELECT
                r.*,
                reporter.username AS reporter_username,
                reporter.nickname AS reporter_nickname,
                target.username AS target_username,
                target.nickname AS target_nickname
            FROM reports r
            JOIN users reporter ON reporter.id = r.reporter_id
            JOIN users target ON target.id = r.target_user_id
            WHERE r.id=$1
            """,
            report_id,
        )
        return dict(row) if row else None

    async def review_report(self, report_id: int, admin_id: int, status: str) -> None:
        await self.db.execute(
            """
            UPDATE reports
            SET status=$3, reviewed_by=$2, reviewed_at=NOW()
            WHERE id=$1
            """,
            report_id,
            admin_id,
            status,
        )
```

## `app/repositories/settings.py`

```python
from __future__ import annotations

import json

from typing import Any

from app.db.database import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_json(self, key: str, default: Any = None) -> Any:
        row = await self.db.fetchrow("SELECT value FROM app_settings WHERE key=$1", key)
        if not row:
            return default
        return row["value"]

    async def set_json(self, key: str, value: Any) -> None:
        await self.db.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (key)
            DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
            """,
            key,
            json.dumps(value),
        )

    async def is_maintenance_mode(self) -> bool:
        value = await self.get_json("maintenance_mode", False)
        return bool(value)

    async def set_maintenance_mode(self, enabled: bool) -> None:
        await self.set_json("maintenance_mode", enabled)
```

## `app/repositories/users.py`

```python
from __future__ import annotations

import json

from typing import Any

import asyncpg

from app.db.database import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language: str,
        is_admin: bool,
    ) -> dict[str, Any]:
        row = await self.db.fetchrow(
            """
            INSERT INTO users (telegram_id, username, first_name, language, language_chosen, is_admin, last_seen_at, updated_at)
            VALUES ($1, $2, $3, $4, FALSE, $5, NOW(), NOW())
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                is_admin = users.is_admin OR EXCLUDED.is_admin,
                last_seen_at = NOW(),
                updated_at = NOW()
            RETURNING *
            """,
            telegram_id,
            username,
            first_name,
            language,
            is_admin,
        )
        return dict(row) if row else {}

    async def update_language(self, telegram_id: int, language: str) -> None:
        await self.db.execute(
            "UPDATE users SET language=$2, language_chosen=TRUE, updated_at=NOW() WHERE telegram_id=$1",
            telegram_id,
            language,
        )

    async def get_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow("SELECT * FROM users WHERE telegram_id=$1", telegram_id)
        return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> dict[str, Any] | None:
        row = await self.db.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
        return dict(row) if row else None

    async def search_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        return await self.get_by_telegram_id(telegram_id)

    async def search_by_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.lstrip("@").lower()
        row = await self.db.fetchrow(
            "SELECT * FROM users WHERE LOWER(username)=$1",
            normalized,
        )
        return dict(row) if row else None

    async def set_profile(
        self,
        telegram_id: int,
        *,
        nickname: str,
        age: int,
        gender: str,
        interested_in: str,
        region: str,
        bio: str,
        interests: list[str],
        profile_photo_file_id: str | None,
    ) -> dict[str, Any] | None:
        row = await self.db.fetchrow(
            """
            UPDATE users
            SET nickname=$2,
                age=$3,
                gender=$4,
                interested_in=$5,
                region=$6,
                bio=$7,
                interests=$8::jsonb,
                profile_photo_file_id=$9,
                is_profile_complete=TRUE,
                updated_at=NOW()
            WHERE telegram_id=$1
            RETURNING *
            """,
            telegram_id,
            nickname,
            age,
            gender,
            interested_in,
            region,
            bio,
            json.dumps(interests),
            profile_photo_file_id,
        )
        return dict(row) if row else None

    async def set_hidden(self, target_user_id: int, hidden: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_hidden=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            hidden,
        )

    async def set_ban(self, target_user_id: int, banned: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_banned=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            banned,
        )

    async def set_suspend(self, target_user_id: int, suspended: bool) -> None:
        await self.db.execute(
            "UPDATE users SET is_suspended=$2, updated_at=NOW() WHERE id=$1",
            target_user_id,
            suspended,
        )

    async def set_notification_matches(self, telegram_id: int, enabled: bool) -> None:
        await self.db.execute(
            "UPDATE users SET notification_matches=$2, updated_at=NOW() WHERE telegram_id=$1",
            telegram_id,
            enabled,
        )

    async def list_recent_signups(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]

    async def list_recently_active(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            "SELECT * FROM users ORDER BY last_seen_at DESC LIMIT $1",
            limit,
        )
        return [dict(row) for row in rows]

    async def iterate_broadcast_targets(self) -> list[dict[str, Any]]:
        rows = await self.db.fetch(
            """
            SELECT telegram_id, language, is_banned, is_suspended
            FROM users
            WHERE is_banned=FALSE
            ORDER BY id ASC
            """
        )
        return [dict(row) for row in rows]

    async def complete_profiles_count(self) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_profile_complete=TRUE"
            )
            or 0
        )

    async def counts(self) -> dict[str, int]:
        row = await self.db.fetchrow(
            """
            SELECT
                COUNT(*) AS total_users,
                COUNT(*) FILTER (WHERE is_profile_complete) AS complete_profiles,
                COUNT(*) FILTER (WHERE is_banned) AS banned_users,
                COUNT(*) FILTER (WHERE is_suspended) AS suspended_users,
                COUNT(*) FILTER (WHERE last_seen_at >= NOW() - INTERVAL '24 hours') AS active_users_24h
            FROM users
            """
        )
        return {key: int(value or 0) for key, value in dict(row or {}).items()}

    async def log_admin_action(
        self,
        admin_id: int | None,
        target_user_id: int | None,
        action_type: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        conn: asyncpg.Connection | None = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        if conn:
            await conn.execute(
                """
                INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason, metadata)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                admin_id,
                target_user_id,
                action_type,
                reason,
                payload,
            )
            return
        await self.db.execute(
            """
            INSERT INTO admin_actions (admin_id, target_user_id, action_type, reason, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            admin_id,
            target_user_id,
            action_type,
            reason,
            payload,
        )
```

## `app/services/__init__.py`

```python

```

## `app/services/admin.py`

```python
from __future__ import annotations

from app.services.app_context import AppContext


async def collect_stats(app: AppContext) -> dict[str, int]:
    user_counts = await app.users.counts()
    like_counts = await app.likes.counts()
    report_counts = await app.reports.counts()
    total_matches = int(await app.db.fetchval("SELECT COUNT(*) FROM matches WHERE status='active'") or 0)
    return {
        **user_counts,
        **like_counts,
        **report_counts,
        "total_matches": total_matches,
    }
```

## `app/services/app_context.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram import Bot


from app.config import Settings
from app.db.database import Database
from app.repositories.likes import LikeRepository
from app.repositories.reports import ReportRepository
from app.repositories.settings import SettingsRepository
from app.repositories.users import UserRepository
from app.services.i18n import I18n
from app.services.rate_limit import SlidingWindowRateLimiter


@dataclass(slots=True)
class AppContext:
    bot: Bot | None
    settings: Settings
    db: Database
    users: UserRepository
    likes: LikeRepository
    reports: ReportRepository
    app_settings: SettingsRepository
    i18n: I18n
    rate_limiter: SlidingWindowRateLimiter
```

## `app/services/discovery.py`

```python
from __future__ import annotations

from typing import Any

from app.services.app_context import AppContext


async def next_candidate(app: AppContext, user_id: int) -> dict[str, Any] | None:
    return await app.likes.discovery_candidate(user_id)
```

## `app/services/guards.py`

```python
from __future__ import annotations

from typing import Any

from app.services.app_context import AppContext


async def can_use_bot(app: AppContext, user: dict[str, Any], *, admin_bypass: bool = False) -> tuple[bool, str | None]:
    if not user:
        return False, None
    if user.get("is_banned"):
        return False, "banned_notice"
    if user.get("is_suspended"):
        return False, "suspended_notice"
    if not admin_bypass and await app.app_settings.is_maintenance_mode() and not user.get("is_admin"):
        return False, "maintenance_mode"
    return True, None


def has_username(user: dict[str, Any]) -> bool:
    username = user.get("username")
    return bool(username and str(username).strip())
```

## `app/services/i18n.py`

```python
from __future__ import annotations

from typing import Any

from app.locales.en import MESSAGES as EN_MESSAGES
from app.locales.my import MESSAGES as MY_MESSAGES


SUPPORTED_LANGUAGES = {"en", "my"}
TRANSLATIONS = {
    "en": EN_MESSAGES,
    "my": MY_MESSAGES,
}


class I18n:
    def __init__(self, default_language: str = "en") -> None:
        self.default_language = default_language if default_language in SUPPORTED_LANGUAGES else "en"

    def t(self, language: str | None, key: str, **kwargs: Any) -> str:
        lang = language if language in SUPPORTED_LANGUAGES else self.default_language
        template = TRANSLATIONS.get(lang, TRANSLATIONS[self.default_language]).get(key)
        if template is None:
            template = TRANSLATIONS[self.default_language].get(key, key)
        return template.format(**kwargs)

    def available_languages(self) -> list[tuple[str, str]]:
        return [(code, TRANSLATIONS[code]["lang_name"]) for code in ["en", "my"]]

    def localized_menu_labels(self) -> dict[str, set[str]]:
        keys = ["browse_profiles", "my_profile", "my_matches", "settings", "help"]
        result: dict[str, set[str]] = {key: set() for key in keys}
        for lang_code, messages in TRANSLATIONS.items():
            for key in keys:
                result[key].add(messages[key])
        return result
```

## `app/services/rate_limit.py`

```python
from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    def hit(self, user_id: int, action: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        key = (user_id, action)
        queue = self._events[key]
        threshold = now - window_seconds
        while queue and queue[0] < threshold:
            queue.popleft()
        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])))
            return False, retry_after
        queue.append(now)
        return True, 0

    def suspicious_mass_like(self, user_id: int) -> bool:
        allowed, _ = self.hit(user_id, "suspicious_like_probe", 41, 3600)
        return not allowed
```

## `app/utils/__init__.py`

```python

```

## `app/utils/formatters.py`

```python
from __future__ import annotations

from html import escape
from typing import Any


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def profile_card(user: dict[str, Any]) -> str:
    interests = user.get("interests") or []
    if isinstance(interests, str):
        interests_text = interests
    else:
        interests_text = ", ".join(str(item) for item in interests) if interests else "-"
    username = user.get("username")
    username_line = f"\nTelegram: @{escape(username)}" if username else ""
    return (
        f"<b>{escape(user.get('nickname') or user.get('first_name') or 'Unknown')}</b>, {user.get('age') or '-'}\n"
        f"Gender: {escape(user.get('gender') or '-')}\n"
        f"Interested in: {escape(user.get('interested_in') or '-')}\n"
        f"Region: {escape(user.get('region') or '-')}\n"
        f"Bio: {escape(user.get('bio') or '-')}\n"
        f"Interests: {escape(interests_text)}"
        f"{username_line}"
    )


def admin_user_card(user: dict[str, Any]) -> str:
    return (
        f"<b>{escape(user.get('nickname') or user.get('first_name') or 'Unknown')}</b>\n"
        f"ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{escape(user.get('username') or '-')}\n"
        f"Profile complete: {yes_no(bool(user.get('is_profile_complete')))}\n"
        f"Banned: {yes_no(bool(user.get('is_banned')))}\n"
        f"Suspended: {yes_no(bool(user.get('is_suspended')))}\n"
        f"Hidden: {yes_no(bool(user.get('is_hidden')))}\n"
        f"Language: {escape(user.get('language') or 'en')}\n"
        f"Last seen: {escape(str(user.get('last_seen_at')))}"
    )


def report_card(report: dict[str, Any]) -> str:
    details = report.get("details") or "-"
    return (
        f"<b>Report #{report['id']}</b>\n"
        f"Reporter: @{escape(report.get('reporter_username') or report.get('reporter_nickname') or '-')}\n"
        f"Target: @{escape(report.get('target_username') or report.get('target_nickname') or '-')}\n"
        f"Reason: {escape(report.get('reason') or '-')}\n"
        f"Details: {escape(details)}\n"
        f"Created: {escape(str(report.get('created_at')))}"
    )
```

## `app/utils/states.py`

```python
from aiogram.fsm.state import State, StatesGroup


class ProfileSetup(StatesGroup):
    nickname = State()
    age = State()
    gender = State()
    interested_in = State()
    region = State()
    bio = State()
    interests = State()
    photo = State()
    confirm = State()


class ReportFlow(StatesGroup):
    waiting_reason_text = State()


class AdminSearchFlow(StatesGroup):
    waiting_query = State()


class AdminBroadcastFlow(StatesGroup):
    waiting_message = State()
```

## `app/utils/validators.py`

```python
from __future__ import annotations

import re


def validate_nickname(value: str, min_len: int = 2, max_len: int = 32) -> bool:
    value = value.strip()
    return min_len <= len(value) <= max_len


def validate_age(value: str) -> int | None:
    value = value.strip()
    if not value.isdigit():
        return None
    age = int(value)
    if 18 <= age <= 80:
        return age
    return None


def validate_region(value: str) -> bool:
    value = value.strip()
    return 2 <= len(value) <= 40


def validate_bio(value: str, min_len: int = 10, max_len: int = 280) -> bool:
    value = value.strip()
    return min_len <= len(value) <= max_len


def parse_interests(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,\n]", value) if part.strip()]
    normalized: list[str] = []
    seen: set[str] = set()
    for part in parts:
        clean = re.sub(r"\s+", " ", part)
        lower = clean.casefold()
        if lower in seen:
            continue
        seen.add(lower)
        normalized.append(clean[:24])
    if 1 <= len(normalized) <= 8:
        return normalized
    return []
```

