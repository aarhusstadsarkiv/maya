_create_orders_query = """
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    user_display_name TEXT NOT NULL,
    UNIQUE (user_email, user_id)
) STRICT;

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    order_status INTEGER NOT NULL,
    record_id TEXT NOT NULL,
    expire_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    comment TEXT DEFAULT "",
    message_sent INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (record_id) REFERENCES records(record_id)
) STRICT;

CREATE TABLE records (
    record_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    meta_data TEXT,
    record_and_types TEXT,
    location INTEGER NOT NULL
) STRICT;

CREATE TABLE orders_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    order_id INTEGER NOT NULL,
    updated_location INTEGER,
    updated_order_status INTEGER,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    record_id TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
) STRICT;

-- Indexes for users
CREATE INDEX idx_users_user_display_name ON users(user_display_name);
CREATE INDEX idx_users_user_email ON users(user_email);

-- Indexes for orders
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_record_id ON orders(record_id);
CREATE INDEX idx_orders_order_status ON orders(order_status);
CREATE INDEX idx_orders_log_updated_at ON orders_log(updated_at);
CREATE INDEX idx_orders_updated_at ON orders(updated_at);

-- Indexes for records
CREATE INDEX idx_orders_expire_at ON orders(expire_at);
CREATE INDEX idx_records_location ON records(location);

-- Indexes for orders_log
CREATE INDEX idx_orders_log_order_id ON orders_log(order_id);
CREATE INDEX idx_orders_log_user_id ON orders_log(user_id);
CREATE INDEX idx_orders_log_record_id ON orders_log(record_id);

-- INSERT system user in users table
INSERT INTO users (user_id, user_email, user_display_name) VALUES ('SYSTEM', 'system', 'SYSTEM');

"""

# List of migrations with keys
migrations_orders = {
    "create_orders": _create_orders_query,
}
