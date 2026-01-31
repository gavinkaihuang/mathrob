from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from app.models import LearningRecord, Problem
from datetime import datetime
import os
from dotenv import load_dotenv

# Manually load env
load_dotenv(".env")
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print(f"Checking DB: {DATABASE_URL}")

now = datetime.utcnow()
print(f"Now (UTC): {now}")

# Check total records
total_records = db.query(LearningRecord).count()
print(f"Total LearningRecords: {total_records}")

# Check query logic
records = db.query(LearningRecord).filter(
    or_(
        LearningRecord.review_date <= now,
        ((LearningRecord.status != 'correct') & (LearningRecord.review_date == None))
    )
).all()

print(f"Found {len(records)} due records:")
for r in records:
    print(f" - Record {r.id}: Problem {r.problem_id}, Status={r.status}, ReviewDate={r.review_date}, Mastery={r.mastery_level}")

if len(records) > 0:
    ids = [r.problem_id for r in records]
    problems = db.query(Problem).filter(Problem.id.in_(ids)).all()
    print(f"Fetched {len(problems)} corresponding problems.")
else:
    print("No due records found. The 'Today's Tasks' list will show 'All caught up'.")
    
    # Check if we have ANY pending records (ignoring correct)
    pending = db.query(LearningRecord).filter(LearningRecord.status != 'correct').all()
    print(f"Total Non-Correct records: {len(pending)}")
    for p in pending:
        print(f"   - Pending Record {p.id}: ReviewDate={p.review_date} (Is None? {p.review_date is None})")
