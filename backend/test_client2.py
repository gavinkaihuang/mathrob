import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User
import app.routers.api as api

client = TestClient(app, raise_server_exceptions=True)

db = SessionLocal()
user = db.query(User).first()

# Override the auth dependency
app.dependency_overrides[api.get_current_user] = lambda: user

try:
    res = client.post("/api/assessment/generate_test")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    import traceback
    traceback.print_exc()
