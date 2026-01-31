# MathRob: AI Learning System

## Project Overview
An AI-powered learning system for students, featuring OCR scan processing, AI analysis (Gemini Pro), and spaced repetition reviews.

## Architecture
- **Backend**: Python FastAPI, SQLAlchemy, PostgreSQL.
- **Frontend**: Next.js, Tailwind CSS.
- **Database**: PostgreSQL (External via NAS).

## Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (configured in `.env`)

## Quick Start

### 1. Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Ensure .env is configured
python create_db.py  # Create DB if needed
alembic upgrade head # Run migrations
```

### 2. Start Backend
```bash
# From root directory
source backend/venv/bin/activate
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Server running at: http://localhost:8000

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend running at: http://localhost:3000

## Features
- **Auto-Scan**: Drops images into `scan_data/` to automatically process them.
- **AI Analysis**: Extracts LaTeX and difficulty from images.
- **Review**: Auto-generated daily review sets.
