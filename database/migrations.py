from sqlalchemy import text
from database.session import engine

USER_COLUMNS = {
    "email_verified": "BOOLEAN DEFAULT 0",
    "email_verification_code": "VARCHAR",
    "password_reset_code": "VARCHAR",
}

def _column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)

def ensure_sqlite_schema():
    with engine.begin() as conn:
        for column_name, column_type in USER_COLUMNS.items():
            if not _column_exists(conn, "users", column_name):
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS billing_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                plan_id VARCHAR,
                plan_name VARCHAR,
                amount_krw INTEGER DEFAULT 0,
                status VARCHAR DEFAULT 'paid',
                payment_method VARCHAR DEFAULT 'mock_checkout',
                receipt_no VARCHAR UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_billing_history_user_id ON billing_history (user_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_billing_history_receipt_no ON billing_history (receipt_no)"))
