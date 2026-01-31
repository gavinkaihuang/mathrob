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

# Define the table SQL manually to avoid full Alembic setup for this simple task
create_table_sql = """
CREATE TABLE IF NOT EXISTS solution_attempts (
    id SERIAL PRIMARY KEY,
    problem_id INTEGER REFERENCES problems(id),
    image_path VARCHAR NOT NULL,
    feedback_json JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
);
"""

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    print("Creating solution_attempts table...")
    conn.execute(text(create_table_sql))
    print("Table created (if not exists).")
