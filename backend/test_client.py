from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User
import backend.app.routers.api as api

client = TestClient(app)

db = SessionLocal()
user = db.query(User).first()

# Override the auth dependency
app.dependency_overrides[api.get_current_user] = lambda: user

res = client.get("/api/assessment/1")
print(f"Status: {res.status_code}")
print(f"Response: {res.text}")

