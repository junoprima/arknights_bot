-- Database Schema for miHoYo Bot
-- Replaces Firebase Firestore with traditional SQL database

-- Guilds table - stores Discord server information
CREATE TABLE guilds (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    webhook_url TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Users table - stores Discord user information
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    discriminator VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guild members - relationship between guilds and users
CREATE TABLE guild_members (
    guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

-- Games table - stores supported games configuration
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    act_id VARCHAR(100) NOT NULL,
    sign_game_header VARCHAR(50) NOT NULL,
    success_message TEXT NOT NULL,
    signed_message TEXT NOT NULL,
    game_id INTEGER NOT NULL,
    author_name VARCHAR(100) NOT NULL,
    icon_url TEXT NOT NULL,
    info_url TEXT NOT NULL,
    home_url TEXT NOT NULL,
    sign_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Accounts table - stores user game accounts and cookies
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    cookie TEXT NOT NULL,
    uid VARCHAR(50),
    nickname VARCHAR(255),
    rank INTEGER,
    region VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(guild_id, user_id, game_id, name)
);

-- Check-in logs - stores daily check-in results
CREATE TABLE checkin_logs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    checkin_date DATE NOT NULL,
    success BOOLEAN NOT NULL,
    reward_name VARCHAR(255),
    reward_count INTEGER,
    reward_icon TEXT,
    total_checkins INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, checkin_date)
);

-- Guild settings - stores per-guild configuration
CREATE TABLE guild_settings (
    guild_id BIGINT REFERENCES guilds(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, setting_key)
);

-- Indexes for better performance
CREATE INDEX idx_accounts_guild_user ON accounts(guild_id, user_id);
CREATE INDEX idx_accounts_game ON accounts(game_id);
CREATE INDEX idx_checkin_logs_date ON checkin_logs(checkin_date);
CREATE INDEX idx_checkin_logs_account ON checkin_logs(account_id);
CREATE INDEX idx_guild_settings_key ON guild_settings(setting_key);

-- Insert default games data
INSERT INTO games (name, display_name, act_id, sign_game_header, success_message, signed_message, game_id, author_name, icon_url, info_url, home_url, sign_url) VALUES
('genshin', 'Genshin Impact', 'e202102251931481', 'hk4e', 'Congratulations, Traveler! You have successfully checked in today~', 'Traveler, you''ve already checked in today~', 2, 'Paimon', 'https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/b700cce2ac4c68a520b15cafa86a03f0_2812765778371293568.png', 'https://sg-hk4e-api.hoyolab.com/event/sol/info', 'https://sg-hk4e-api.hoyolab.com/event/sol/home', 'https://sg-hk4e-api.hoyolab.com/event/sol/sign'),

('honkai', 'Honkai Impact 3rd', 'e202110291205111', 'honkai', 'You have successfully checked in today, Captain~', 'You''ve already checked in today, Captain~', 1, 'Kiana', 'https://fastcdn.hoyoverse.com/static-resource-v2/2024/02/29/3d96534fd7a35a725f7884e6137346d1_3942255444511793944.png', 'https://sg-public-api.hoyolab.com/event/mani/info', 'https://sg-public-api.hoyolab.com/event/mani/home', 'https://sg-public-api.hoyolab.com/event/mani/sign'),

('zenless', 'Zenless Zone Zero', 'e202406031448091', 'zzz', 'Congratulations Proxy! You have successfully checked in today!~', 'You have already checked in today, Proxy!~', 8, 'Eous', 'https://hyl-static-res-prod.hoyolab.com/communityweb/business/nap.png', 'https://sg-public-api.hoyolab.com/event/luna/zzz/os/info', 'https://sg-public-api.hoyolab.com/event/luna/zzz/os/home', 'https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign'),

('starrail', 'Honkai: Star Rail', 'e202303301540311', 'hkrpg', 'You have successfully checked in today, Trailblazer~', 'You''ve already checked in today, Trailblazer~', 6, 'PomPom', 'https://fastcdn.hoyoverse.com/static-resource-v2/2024/04/12/74330de1ee71ada37bbba7b72775c9d3_1883015313866544428.png', 'https://sg-public-api.hoyolab.com/event/luna/os/info', 'https://sg-public-api.hoyolab.com/event/luna/os/home', 'https://sg-public-api.hoyolab.com/event/luna/os/sign');