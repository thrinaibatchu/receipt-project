import sqlite3
from pathlib import Path


DB_PATH = Path("data/receipts.db")


def create_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            store_name TEXT NOT NULL,
            purchase_date TEXT,

            subtotal REAL,
            tax REAL,
            total REAL NOT NULL,

            transaction_id TEXT,

            source_file TEXT NOT NULL,
            source_hash TEXT NOT NULL UNIQUE,
            receipt_fingerprint TEXT UNIQUE,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            category TEXT
        );

        CREATE TABLE IF NOT EXISTS receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER NOT NULL,
            product_id INTEGER,

            store_item_code TEXT,
            raw_description TEXT NOT NULL,

            quantity REAL NOT NULL DEFAULT 1,
            unit_price REAL,
            total_price REAL NOT NULL,

            FOREIGN KEY (receipt_id) REFERENCES receipts(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS receipt_discounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER NOT NULL,
            raw_description TEXT NOT NULL,
            amount REAL NOT NULL,
            related_item_code TEXT,

            FOREIGN KEY (receipt_id) REFERENCES receipts(id)
        );
        """
    )

    connection.commit()
    connection.close()

    print(f"Database created at: {DB_PATH}")


if __name__ == "__main__":
    create_database()