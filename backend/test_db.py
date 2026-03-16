import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import AssessmentSession, AssessmentProblem

try:
    db = SessionLocal()
    session = db.query(AssessmentSession).order_by(AssessmentSession.id.desc()).first()
    print(f"Session found: {session.id if session else None}")
    if session:
        probs = db.query(AssessmentProblem).filter(AssessmentProblem.session_id == session.id).all()
        print(f"Problems count: {len(probs)}")
        for ap in probs:
            print(f"ap.id={ap.id}, problem_id={ap.problem_id}")
            print(f"problem object: {ap.problem}")
            print(f"problem latex: {ap.problem.latex_content[:20] if ap.problem.latex_content else 'None'}")
        
    print("ALL OK")
except Exception as e:
    import traceback
    traceback.print_exc()
