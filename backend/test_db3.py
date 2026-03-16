import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import User, UserProgress, Problem

db = SessionLocal()
u = db.query(User).first()
if u:
    learned = db.query(UserProgress).filter(UserProgress.user_id == u.id, UserProgress.is_learned == True).all()
    print("User learned paths:")
    for p in learned:
        print(f" - {p.knowledge_id} / {p.knowledge_name} / {p.knowledge_path}")

    probs = db.query(Problem).limit(5).all()
    print("\nSample Problems in DB:")
    for p in probs:
        print(f" - {p.knowledge_node_name} / {p.knowledge_path}")

