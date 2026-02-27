from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading
import os
from .database import engine, Base
from .services.file_watcher import FileWatcher
from .services.ai_service import AIService

# Initialize AI Service
ai_service = AIService()

# Ensure uploads dir exists
UPLOAD_DIR = os.path.join(os.getcwd(), "backend/uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Callback for new files
def on_new_scan(file_path):
    print(f"Processing new file: {file_path}")
    # In a real app, this would trigger an async task to call AI service and save to DB
    # asyncio.run(process_scan(file_path)) 

# Initialize File Watcher
watcher = FileWatcher(UPLOAD_DIR, on_new_scan)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    watcher_thread = threading.Thread(target=watcher.start)
    watcher_thread.daemon = True
    watcher_thread.start()
    yield
    # Shutdown
    watcher.stop()

app = FastAPI(title="MathRob API", version="0.1.0", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Allow Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")


from .routers import api, upload, auth, users, settings
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(api.router, prefix="/api")
app.include_router(upload.router, prefix="/api") # or just /upload if preferred, keeping consistency
app.include_router(settings.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to MathRob AI Learning System"}

