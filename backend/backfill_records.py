from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import LearningRecord, Problem, User
from datetime import datetime
import os
from dotenv import load_dotenv

# Manually load env
load_dotenv(".env")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def backfill():
    print(f"Connecting to: {DATABASE_URL}")
    
    # 1. Find all problems that DON'T have a LearningRecord
    problems_without_records = db.query(Problem).outerjoin(LearningRecord).filter(
        LearningRecord.id == None
    ).all()
    
    print(f"Found {len(problems_without_records)} problems without learning records.")
    
    count = 0
    for prob in problems_without_records:
        if prob.user_id:
            new_record = LearningRecord(
                user_id=prob.user_id,
                problem_id=prob.id,
                status="pending",
                review_date=datetime.utcnow() # Due now
            )
            db.add(new_record)
            count += 1
            print(f" - Created record for Problem {prob.id} (User {prob.user_id})")
        else:
            print(f" - Skipping Problem {prob.id}: No user_id assigned.")
            
    db.commit()
    print(f"\nSuccessfully created {count} new LearningRecords.")

if __name__ == "__main__":
    backfill()
