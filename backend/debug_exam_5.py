#!/usr/bin/env python
import os
import sys
os.chdir('/Users/gminihome/SourceCodes/mathrob/backend')
sys.path.insert(0, '/Users/gminihome/SourceCodes/mathrob/backend')

from app.database import SessionLocal
from app.models import ExamRecord, ExamProblemResult

db = SessionLocal()

exam = db.query(ExamRecord).filter(ExamRecord.id == 5).first()

if exam:
    print(f"试卷ID: {exam.id}")
    print(f"试卷名称: {exam.paper_name}")
    print(f"\n=== 数据库中保存的题目数量 ===")
    
    problems = db.query(ExamProblemResult).filter(
        ExamProblemResult.exam_id == 5
    ).order_by(ExamProblemResult.problem_number).all()
    
    print(f"总共 {len(problems)} 道题目\n")
    
    for p in problems:
        print(f"题号: {p.problem_number:>3s} | 分数: {p.score:>2.0f}/{p.max_score:>2.0f} | 知识点: {p.knowledge_tag}")
    
    print(f"\n=== Gemini 的原始响应（前1000字符） ===")
    print(exam.overall_evaluation[:1500] if exam.overall_evaluation else "无")
else:
    print("试卷不存在")

db.close()
