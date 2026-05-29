-- 鱿郁仔仔 授权系统 D1 Schema

CREATE TABLE IF NOT EXISTS activation_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    batch_id    TEXT,
    valid_days  INTEGER NOT NULL DEFAULT 365,
    max_devices INTEGER NOT NULL DEFAULT 2,
    is_used     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    used_at     TEXT
);

CREATE TABLE IF NOT EXISTS licenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key     TEXT NOT NULL UNIQUE,
    code_id         INTEGER NOT NULL REFERENCES activation_codes(id),
    device_id       TEXT NOT NULL,
    device_type     TEXT NOT NULL DEFAULT 'pc',
    activated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL,
    last_heartbeat  TEXT,
    is_revoked      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(code_id, device_id)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_super      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    detail     TEXT,
    ip         TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_codes_code ON activation_codes(code);
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_device ON licenses(device_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
