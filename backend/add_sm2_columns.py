from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

def migrate():
    # Load env from backend/.env if not already loaded (assuming we are running from root)
    if os.path.exists("backend/.env"):
        load_dotenv("backend/.env")
    else:
        load_dotenv()
        
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    print(f"Connecting to database...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Commit manually for DDL
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        columns = [
            ("ease_factor", "FLOAT DEFAULT 2.5"),
            ("interval", "INTEGER DEFAULT 0"),
            ("repetitions", "INTEGER DEFAULT 0")
        ]
        
        for col, type_def in columns:
            try:
                # Check if column exists
                check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='learning_records' AND column_name='{col}'")
                result = conn.execute(check_sql).fetchone()
                
                if not result:
                    print(f"Adding column {col}...")
                    conn.execute(text(f"ALTER TABLE learning_records ADD COLUMN {col} {type_def}"))
                else:
                    print(f"Column {col} already exists, skipping.")
            except Exception as e:
                print(f"Error adding {col}: {e}")
                
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
