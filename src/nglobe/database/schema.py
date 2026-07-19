"""SQLite database schema for NetworkGlobe.

Defines table creation, indexes, and schema migrations.
Future-ready fields (blocked, block_reason, rule_id, process_name, tags)
are included in the schema but unused in V1.
"""

SCHEMA_VERSION = 1

CREATE_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    hostname        TEXT    NOT NULL,
    destination_ip  TEXT    NOT NULL,
    port            INTEGER NOT NULL DEFAULT 443,
    protocol        TEXT    NOT NULL DEFAULT 'HTTPS',
    method          TEXT,
    path            TEXT,
    status_code     INTEGER,
    country_code    TEXT,
    country_name    TEXT,
    city            TEXT,
    latitude        REAL,
    longitude       REAL,
    organization    TEXT,
    asn             INTEGER,
    tls_version     TEXT,
    bytes_sent      INTEGER DEFAULT 0,
    bytes_received  INTEGER DEFAULT 0,
    latency_ms      REAL,
    blocked         INTEGER NOT NULL DEFAULT 0,
    block_reason    TEXT,
    rule_id         INTEGER,
    process_name    TEXT,
    tags            TEXT
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_requests_hostname ON requests(hostname);",
    "CREATE INDEX IF NOT EXISTS idx_requests_country ON requests(country_code);",
    "CREATE INDEX IF NOT EXISTS idx_requests_org ON requests(organization);",
    "CREATE INDEX IF NOT EXISTS idx_requests_asn ON requests(asn);",
]

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA temp_store = MEMORY;",
    "PRAGMA cache_size = 10000;",
    "PRAGMA mmap_size = 268435456;",
]
