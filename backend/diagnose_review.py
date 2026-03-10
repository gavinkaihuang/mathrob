from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from app.models import LearningRecord, Problem, UserProgress, User
from datetime import datetime
import os
from dotenv import load_dotenv

# Manually load env
load_dotenv(".env")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def check_user(db, user, now):
    print(f"\n--- Analyzing for User: {user.username} (ID: {user.id}) ---")
    
    # 1. Check LearningRecords due by date
    all_due = db.query(LearningRecord).filter(
        LearningRecord.user_id == user.id,
        LearningRecord.review_date <= now
    ).all()
    print(f"Due by date alone (review_date <= now): {len(all_due)}")

    # 2. Check the EXACT query in api.py (get_today_reviews)
    due_records_query = db.query(LearningRecord).join(Problem).filter(
        and_(
            LearningRecord.user_id == user.id,
            LearningRecord.review_date <= now
        )
    )
    due_records = due_records_query.all()
    print(f"Due using api.py query (join Problem): {len(due_records)}")

    # 3. If there is a difference, investigate why join Problem is failing
    if len(all_due) > len(due_records):
        print("DIAGNOSIS: The join with Problem is filtering out some records!")
        due_ids = [r.id for r in due_records]
        for rec in all_due:
            if rec.id not in due_ids:
                print(f" - Record {rec.id} has problem_id {rec.problem_id}")
                prob = db.query(Problem).filter(Problem.id == rec.problem_id).first()
                if not prob:
                    print(f"   Reason: Problem ID {rec.problem_id} DOES NOT EXIST in problems table!")
                else:
                    print(f"   Problem exists (ID: {prob.id}), but join failed? Check user_id mismatch?")
                    print(f"   Problem.user_id: {prob.user_id}, LearningRecord.user_id: {rec.user_id}")

    # 4. Check the home page query (get_daily_review_problems)
    home_query = db.query(LearningRecord).filter(
        LearningRecord.user_id == user.id,
        or_(
            LearningRecord.review_date <= now,
            ((LearningRecord.status != 'correct') & (LearningRecord.review_date == None))
        )
    )
    home_records = home_query.all()
    print(f"Due using home page query: {len(home_records)}")

print(f"Checking DB: {DATABASE_URL}")
now = datetime.utcnow()
print(f"Now (UTC): {now}")

users = db.query(User).all()
for u in users:
    check_user(db, u, now)
