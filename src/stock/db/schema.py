import sqlite3


SCHEMA_VERSION = 1


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS symbols (
            code TEXT PRIMARY KEY,
            market TEXT,
            currency TEXT,
            name TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_time TEXT NOT NULL,
            code TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL,
            fee REAL NOT NULL DEFAULT 0,
            fx_rate REAL,
            broker TEXT,
            note TEXT,
            import_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_transactions_code_time
        ON transactions(code, trade_time)
        """
    )

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_import_id
        ON transactions(import_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prices_eod (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            close REAL NOT NULL,
            currency TEXT NOT NULL,
            source TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code, date, currency)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fx_rates (
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            date TEXT NOT NULL,
            rate REAL NOT NULL,
            source TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (from_currency, to_currency, date)
        )
        """
    )

    conn.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()
