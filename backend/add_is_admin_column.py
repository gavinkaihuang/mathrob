from sqlalchemy import create_engine, text
from app.database import Base, engine
import os

def add_is_admin_column():
    print("Adding is_admin column to users table...")
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin'"))
            if result.fetchone():
                print("Column 'is_admin' already exists.")
            else:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                print("Column 'is_admin' added.")
                
            # Set developer as admin
            print("Setting 'developer' user as admin...")
            conn.execute(text("UPDATE users SET is_admin = TRUE WHERE username = 'developer'"))
            conn.commit()
            print("Migration complete.")
            
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_is_admin_column()
