#!/usr/bin/env python3
import sys
import os
import asyncio

# Ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Ensure backend package is importable (add backend/ as package root)
backend_path = os.path.join(ROOT, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models import ExamRecord
from app.routers.api import process_full_exam

async def main(exam_id: int):
    db = SessionLocal()
    try:
        exam = db.query(ExamRecord).filter(ExamRecord.id == exam_id).first()
        if not exam:
            print(f"Exam {exam_id} not found")
            return 1
        print(f"Found exam {exam_id}: user_id={exam.user_id}, status={exam.status}")
        image_paths = exam.image_paths or []
        image_urls = exam.image_urls or []
        print(f"image_paths={image_paths}")
        print(f"image_urls={image_urls}")
        await process_full_exam(task_id=exam_id, user_id=exam.user_id, image_paths=image_paths, image_urls=image_urls)
        print("process_full_exam completed")
        return 0
    except Exception as e:
        print(f"Error running process_full_exam: {e}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: rerun_exam.py <exam_id>")
        sys.exit(2)
    exam_id = int(sys.argv[1])
    asyncio.run(main(exam_id))
