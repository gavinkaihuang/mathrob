from sqlalchemy import create_engine, text
from app.database import Base, engine, SessionLocal
from app.models import User
import os

def migrate_user_data():
    print("Migrating data to developer user...")
    db = SessionLocal()
    try:
        # 1. Get Developer User
        developer = db.query(User).filter(User.username == 'developer').first()
        if not developer:
            print("Error: Developer user not found!")
            return
        
        dev_id = developer.id
        print(f"Developer ID: {dev_id}")

        with engine.connect() as conn:
            # 2. Add columns if not exist and update data
            tables = ['problems', 'learning_records', 'solution_attempts', 'weekly_reports']
            
            for table in tables:
                print(f"Processing table: {table}")
                try:
                    # Check column
                    result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='user_id'"))
                    if not result.fetchone():
                        print(f"Adding user_id column to {table}...")
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    else:
                        print(f"Column user_id already exists in {table}")
                    
                    # Update data
                    print(f"Assigning existing records in {table} to developer...")
                    conn.execute(text(f"UPDATE {table} SET user_id = {dev_id} WHERE user_id IS NULL"))
                    
                    # Optional: Make persistent not nullable? For now keep nullable to avoid issues if errors, 
                    # but logic should assume it's there.
                    
                    # Commit per table changes
                    conn.commit()
                    
                except Exception as e:
                    print(f"Error processing {table}: {e}")
                    conn.rollback()

        print("Migration complete.")

    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_user_data()
