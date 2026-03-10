from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import APICallLog, User
import os
from dotenv import load_dotenv

load_dotenv(".env")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

logs = db.query(APICallLog, User).join(User).order_by(APICallLog.created_at.desc()).limit(20).all()

print("Recent API Call Logs:")
for log, user in logs:
    print(f"User: {user.username}, Action: {log.action_type}, Category: {log.category}, Model: {log.model_used}, Time: {log.created_at}")
