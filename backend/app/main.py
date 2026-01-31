from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from .database import engine, Base
from .services.file_watcher import FileWatcher
from .services.ai_service import AIService

# Initialize AI Service
ai_service = AIService()

# Callback for new files
def on_new_scan(file_path):
    print(f"Processing new file: {file_path}")
    # In a real app, this would trigger an async task to call AI service and save to DB
    # asyncio.run(process_scan(file_path)) 

# Initialize File Watcher
watcher = FileWatcher("./scan_data", on_new_scan)

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

from .routers import api
app.include_router(api.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to MathRob AI Learning System"}

