from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load env from backend/.env if not already loaded (assuming we are running from root)
if os.path.exists("backend/.env"):
    load_dotenv("backend/.env")
else:
    load_dotenv()
    
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

print(f"Connecting to database...")
engine = create_engine(db_url)

create_table_sql = """
CREATE TABLE IF NOT EXISTS weekly_reports (
    id SERIAL PRIMARY KEY,
    week_start DATE NOT NULL,
    pdf_path VARCHAR NOT NULL,
    summary_json JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
);
"""

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    print("Creating weekly_reports table...")
    conn.execute(text(create_table_sql))
    print("Table created (if not exists).")
