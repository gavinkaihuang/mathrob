
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load env from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

def add_column():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Use text() for raw SQL
            conn.execute(text("ALTER TABLE learning_records ADD COLUMN mastery_level INTEGER"))
            conn.commit()
            print("Successfully added 'mastery_level' column to 'learning_records' table.")
        except Exception as e:
            print(f"Error adding column: {e}")
            print("This might mean the column already exists or there is a connection issue.")

if __name__ == "__main__":
    add_column()
