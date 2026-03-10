from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker
from app.models import User, LearningRecord, Problem
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

now = datetime.utcnow()
users = db.query(User).all()

print(f"Server Time: {now}")
print("User List and Review Counts:")
for u in users:
    count = db.query(LearningRecord).filter(
        LearningRecord.user_id == u.id,
        or_(
            LearningRecord.review_date <= now,
            ((LearningRecord.status != 'correct') & (LearningRecord.review_date == None))
        )
    ).count()
    print(f"ID: {u.id}, Username: {u.username}, Due Items: {count}")
