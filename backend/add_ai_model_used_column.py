
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

def add_column(engine, column_name, column_type):
    with engine.connect() as conn:
        try:
            print(f"Adding {column_name} ({column_type}) to 'solution_attempts'...")
            conn.execute(text(f"ALTER TABLE solution_attempts ADD COLUMN {column_name} {column_type}"))
            conn.commit()
            print(f"Successfully added '{column_name}' column.")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e):
                print(f"Note: '{column_name}' already exists.")
            else:
                print(f"Error adding {column_name}: {e}")

def migrate():
    print(f"Connecting to database at {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    
    add_column(engine, "ai_model_used", "VARCHAR(100)")
    add_column(engine, "ai_score", "DOUBLE PRECISION")
    add_column(engine, "ai_evaluation", "JSON")
    
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
