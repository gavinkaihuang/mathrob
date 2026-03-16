import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import User, UserProgress, Problem

db = SessionLocal()
u = db.query(User).first()
if u:
    learned = db.query(UserProgress).filter(UserProgress.user_id == u.id, UserProgress.is_learned == True).all()
    print("Learned paths:", [p.knowledge_path for p in learned])
    for p in learned:
        probs = db.query(Problem).filter(Problem.knowledge_path.ilike(f"%{p.knowledge_path}%")).all()
        print(f"Path '{p.knowledge_path}' has {len(probs)} matching problems.")
        if len(probs) > 0:
            print(probs[0].problem_text)
