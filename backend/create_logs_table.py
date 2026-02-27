from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

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
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) DEFAULT 'ERROR',
    category VARCHAR(50), 
    message TEXT,
    details JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
);
"""

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    print("Creating system_logs table...")
    conn.execute(text(create_table_sql))
    print("Table created (if not exists).")
