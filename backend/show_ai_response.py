#!/usr/bin/env python
import os
import sys
import json
os.chdir('/Users/gminihome/SourceCodes/mathrob/backend')
sys.path.insert(0, '/Users/gminihome/SourceCodes/mathrob/backend')

from app.database import SessionLocal
from app.models import SystemLog

db = SessionLocal()

# 找到最近的试卷处理日志
log = db.query(SystemLog).filter(
    SystemLog.category == 'teaching',
    SystemLog.message == 'Raw AI response for exam'
).order_by(SystemLog.created_at.desc()).first()

if log and log.details:
    text_preview = log.details.get('text_preview', '')
    print("=== Gemini 原始响应开头 ===\n")
    print(text_preview[:3000])
else:
    print("未找到日志")

db.close()
