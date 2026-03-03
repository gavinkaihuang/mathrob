
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Go up one level to find the .env in the root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print(f"Error: DATABASE_URL not found at {env_path}")
    exit(1)

def create_table():
    print(f"Connecting to database at {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            print("Creating 'api_call_logs' table...")
            sql = """
            CREATE TABLE IF NOT EXISTS api_call_logs (
                id SERIAL PRIMARY KEY,
                category VARCHAR(50) NOT NULL,
                action_type VARCHAR(50) NOT NULL,
                target_id INTEGER,
                model_used VARCHAR(100) NOT NULL,
                token_name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_api_call_logs_created_at ON api_call_logs(created_at DESC);
            """
            conn.execute(text(sql))
            conn.commit()
            print("Successfully created 'api_call_logs' table.")
        except Exception as e:
            print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()
