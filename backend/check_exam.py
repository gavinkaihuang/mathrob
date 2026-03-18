import os
os.environ['PYTHONPATH'] = '/Users/gminihome/SourceCodes/mathrob/backend'

from app.database import SessionLocal
from app.models import ExamRecord, ExamProblemResult
import json

db = SessionLocal()

# Find exam by paper name
exams = db.query(ExamRecord).filter(
    ExamRecord.paper_name.ilike('%同济大学%')
).all()

if not exams:
    print("未找到与'同济大学'相关的试卷")
    # Try to show all exams
    all_exams = db.query(ExamRecord).order_by(ExamRecord.created_at.desc()).limit(10).all()
    print("\n最近的试卷列表:")
    for exam in all_exams:
        problem_count = db.query(ExamProblemResult).filter(
            ExamProblemResult.exam_id == exam.id
        ).count()
        print(f"  ID: {exam.id}, 名称: {exam.paper_name}, 题目数: {problem_count}")
else:
    for exam in exams:
        problem_count = db.query(ExamProblemResult).filter(
            ExamProblemResult.exam_id == exam.id
        ).count()
        print(f"试卷ID: {exam.id}")
        print(f"试卷名称: {exam.paper_name}")
        print(f"状态: {exam.status}")
        print(f"创建时间: {exam.created_at}")
        print(f"数据库中的题目数: {problem_count}")
        print(f"总分: {exam.total_score}")
        
        # Get details of problems
        problems = db.query(ExamProblemResult).filter(
            ExamProblemResult.exam_id == exam.id
        ).order_by(ExamProblemResult.problem_number.asc()).all()
        
        print(f"\n题目详情:")
        for p in problems[:5]:  # Show first 5
            print(f"  题号: {p.problem_number}, 分数: {p.score}/{p.max_score}, 知识点: {p.knowledge_tag}")
        
        if len(problems) > 5:
            print(f"  ... 还有 {len(problems) - 5} 道题目")
        
        print("---")

db.close()
