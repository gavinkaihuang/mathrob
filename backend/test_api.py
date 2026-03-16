import sys
import os
import requests
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models import User
from app.routers.auth import create_access_token
from datetime import timedelta

db = SessionLocal()
user = db.query(User).first()
if user:
    token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(days=1))
    
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("http://localhost:8000/api/assessment/1", headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
else:
    print("NO USER FOUND")
