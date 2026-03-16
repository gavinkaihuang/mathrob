import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import User
from app.services.auth_service import auth_service
from datetime import timedelta
import requests

db = SessionLocal()
user = db.query(User).first()
if user:
    token = auth_service.create_access_token(data={"sub": user.username}, expires_delta=timedelta(days=1))
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post("http://localhost:8000/api/assessment/generate_test", headers=headers)
    print(res.status_code)
    print(res.text)
