create_booksmarks_query = """
CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY,
    bookmark TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
) STRICT;
"""

create_booksmarks_index_query = """
CREATE INDEX idx_bookmarks_user_id ON bookmarks (user_id);
"""

create_searches_query = """
CREATE TABLE searches (
    id INTEGER PRIMARY KEY,
    search TEXT NOT NULL,
    title TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
) STRICT;
"""

create_searches_index_query = """
CREATE INDEX idx_searches_user_id ON searches (user_id);
"""

create_cache_query = """
CREATE TABLE cache (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    unix_timestamp INTEGER NOT NULL DEFAULT 0
) STRICT;
"""

create_cache_index_query = """
CREATE INDEX idx_cache_unix_timestamp ON cache (unix_timestamp);
"""

create_error_logs = """
CREATE TABLE error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT,
    name TEXT,
    level TEXT,
    message TEXT,
    exception TEXT,
    url TEXT,
    error_code INTEGER,
    resolved INTEGER DEFAULT 0,
    UNIQUE(url, message)
) STRICT;
"""

create_error_logs_index = """
CREATE INDEX idx_time ON error_logs (time);
"""

# alter bookmarks table bookmark column name to record_id
alter_bookmarks_table = """
ALTER TABLE bookmarks RENAME COLUMN bookmark TO record_id;
"""

rebuild_cache_table_with_unique_key = """
DROP INDEX IF EXISTS idx_cache_key;
DROP INDEX IF EXISTS idx_cache_unix_timestamp;
ALTER TABLE cache RENAME TO cache_old;
CREATE TABLE cache (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    unix_timestamp INTEGER NOT NULL DEFAULT 0
) STRICT;
INSERT INTO cache (key, value, unix_timestamp)
SELECT cache_old.key, cache_old.value, cache_old.unix_timestamp
FROM cache_old
WHERE cache_old.id = (
    SELECT cache_old_inner.id
    FROM cache_old AS cache_old_inner
    WHERE cache_old_inner.key = cache_old.key
    ORDER BY cache_old_inner.unix_timestamp DESC, cache_old_inner.id DESC
    LIMIT 1
);
CREATE INDEX idx_cache_unix_timestamp ON cache (unix_timestamp);
DROP TABLE cache_old;
"""

drop_error_logs = """
DROP TABLE IF EXISTS error_logs;
"""

# List of migrations with keys
migrations_default = {
    "create_bookmarks": create_booksmarks_query,
    "create_bookmarks_index": create_booksmarks_index_query,
    "create_searches": create_searches_query,
    "create_searches_index": create_searches_index_query,
    "create_cache": create_cache_query,
    "create_cache_index": create_cache_index_query,
    "create_error_logs": create_error_logs,
    "create_error_logs_index": create_error_logs_index,
    "alter_bookmarks_table": alter_bookmarks_table,
    "rebuild_cache_table_with_unique_key": rebuild_cache_table_with_unique_key,
    "drop_error_logs": drop_error_logs,
}
