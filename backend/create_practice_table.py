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
CREATE TABLE IF NOT EXISTS practice_problems (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    source_problem_id INTEGER REFERENCES problems(id),
    latex_content TEXT,
    difficulty INTEGER,
    knowledge_path VARCHAR,
    ai_model VARCHAR,
    ai_analysis JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
);
"""

# Cleanup bad data in the old table
cleanup_sql = """
DELETE FROM problems WHERE image_path = 'generated';
"""

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    print("Creating practice_problems table...")
    conn.execute(text(create_table_sql))
    print("Table created (if not exists).")
    
    print("Cleaning up old generated practice problems from main problems table...")
    conn.execute(text(cleanup_sql))
    print("Cleanup complete.")
