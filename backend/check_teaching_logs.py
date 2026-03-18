#!/usr/bin/env python
import os
import sys
os.chdir('/Users/gminihome/SourceCodes/mathrob/backend')
sys.path.insert(0, '/Users/gminihome/SourceCodes/mathrob/backend')

from app.database import SessionLocal
from app.models import SystemLog

db = SessionLocal()

logs = db.query(SystemLog).filter(
    SystemLog.category == 'teaching'
).order_by(SystemLog.created_at.desc()).limit(10).all()

print("=== 最近的 teaching 类日志 ===\n")
for log in logs:
    print(f"时间: {log.created_at}")
    print(f"级别: {log.level}")
    print(f"消息: {log.message}")
    if log.details:
        details_str = str(log.details)[:300]
        print(f"详情: {details_str}")
    print("---\n")

db.close()
