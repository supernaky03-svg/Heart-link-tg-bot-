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

ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_gender;
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_interested_in;

ALTER TABLE users
    ADD CONSTRAINT chk_users_gender
    CHECK (gender IS NULL OR gender IN ('male', 'female'));

ALTER TABLE users
    ADD CONSTRAINT chk_users_interested_in
    CHECK (interested_in IS NULL OR interested_in IN ('male', 'female'));

CREATE INDEX IF NOT EXISTS idx_users_lat_lng ON users (latitude, longitude);

UPDATE users
SET is_profile_complete = FALSE,
    updated_at = NOW()
WHERE profile_photo_file_id IS NULL
   OR latitude IS NULL
   OR longitude IS NULL
   OR gender NOT IN ('male', 'female')
   OR interested_in NOT IN ('male', 'female');

INSERT INTO app_settings(key, value)
VALUES ('maintenance_mode', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;
