from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import bcrypt

# Load env variables
if os.path.exists("backend/.env"):
    load_dotenv("backend/.env")
else:
    load_dotenv()
    
db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"Connecting to database...")
engine = create_engine(db_url)

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    
    # 1. Add columns if not exist
    print("Checking headers...")
    columns = [
        ("username", "VARCHAR UNIQUE"),
        ("hashed_password", "VARCHAR"),
    ]
    
    for col, type_def in columns:
        try:
            check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='{col}'")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                print(f"Adding column {col}...")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {type_def}"))
            else:
                print(f"Column {col} already exists.")
        except Exception as e:
            print(f"Error checking/adding {col}: {e}")

    # 2. Create Default User
    username = "developer"
    password = "developer"
    hashed = get_password_hash(password)
    
    # Check if user exists
    check_user = text(f"SELECT id FROM users WHERE username = :username")
    result = conn.execute(check_user, {"username": username}).fetchone()
    
    if not result:
        print(f"Creating default user '{username}'...")
        insert_sql = text("INSERT INTO users (username, hashed_password, name, created_at) VALUES (:u, :p, :n, now())")
        conn.execute(insert_sql, {"u": username, "p": hashed, "n": "Developer"})
        print("User created.")
    else:
        print(f"User '{username}' already exists. Updating password...")
        update_sql = text("UPDATE users SET hashed_password = :p WHERE username = :u")
        conn.execute(update_sql, {"p": hashed, "u": username})
        print("User updated.")

print("Migration complete.")
