import os
import sys
from sqlalchemy import create_engine, text
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Get URL but replace dbname with 'postgres' to connect to default db
original_url = os.getenv("DATABASE_URL")
if not original_url:
    print("DATABASE_URL not found")
    sys.exit(1)

# Hacky parsing to switch dbname
# Assumes format: postgresql://user:pass@host:port/dbname?params
base_url = original_url.split('/mathrob')[0]
params = original_url.split('?')[-1] if '?' in original_url else ""
postgres_url = f"{base_url}/postgres"
if params:
    postgres_url += f"?{params}"

print(f"Connecting to default DB: {postgres_url}")

def create_database():
    try:
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as connection:
            # Check if db exists
            result = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = 'mathrob'"))
            if result.scalar():
                print("Database 'mathrob' already exists.")
            else:
                print("Creating database 'mathrob'...")
                connection.execute(text("CREATE DATABASE mathrob"))
                print("Database 'mathrob' created successfully!")
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
