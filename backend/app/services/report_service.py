import os
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Problem, LearningRecord, WeeklyReport, ProblemStatus
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json

class ReportService:
    def __init__(self, db: Session):
        self.db = db
        # Register Font (Using a built-in or assuming a font exists - in prod, bundle a Chinese font)
        # For this environment, we might need a Chinese font. 
        # I'll check if I can use a system font or just standard English for now, 
        # but user likely wants Chinese. I'll stick to basic English/standard for structure 
        # and try to handle font gracefully or tell user to install one.
        # UPDATE: I'll use standard Helvetica for now to avoid crashes, but adding Chinese support is a common requirement.
        # ReportLab doesn't support Chinese out of the box without a font registration.
        # I'll try to use a registered font if available, else fall back.
        pass

    def register_chinese_font(self):
        # Placeholder for font registration logic
        try:
             # Try to find a common font on Mac
            font_path = "/System/Library/Fonts/PingFang.ttc"
            if os.path.exists(font_path):
                # ReportLab might struggle with TTC. 
                # Let's try to stick to English for labels or use a very basic setup.
                # Actually, I'll attempt using 'Arial Unicode' or similar if possible.
                # Just proceeding with standard generic setup for MVP.
                pass
        except:
            pass

    def generate_weekly_report(self, user_id: int, week_start: date = None) -> WeeklyReport:
        if not week_start:
            today = date.today()
            week_start = today - timedelta(days=today.weekday()) # Monday

        end_date = week_start + timedelta(days=6)
        
        # 1. Aggregate Stats
        # Problems Created
        problems_count = self.db.query(Problem).filter(
            Problem.user_id == user_id,
            Problem.created_at >= week_start, 
            Problem.created_at <= end_date + timedelta(days=1)
        ).count()
        
        # Learning Records interactions (Need to join with Problem or have user_id on Record)
        # We added user_id to LearningRecord, so we can use it directly.
        records = self.db.query(LearningRecord).filter(
            LearningRecord.user_id == user_id,
            LearningRecord.created_at >= week_start,
            LearningRecord.created_at <= end_date + timedelta(days=1)
        ).all()
        
        reviews_count = len(records)
        
        # Mastery Distribution
        mastery_counts = {1: 0, 2: 0, 3: 0, "No Data": 0}
        all_records = self.db.query(LearningRecord).filter(LearningRecord.user_id == user_id).all() # User snapshot
        for r in all_records:
            if r.mastery_level:
                mastery_counts[r.mastery_level] = mastery_counts.get(r.mastery_level, 0) + 1
            else:
                mastery_counts["No Data"] += 1
                
        # Weak Knowledge Points (Level 1 or 2)
        # This requires KnowledgePoints linked to Problems
        # For now, I'll just count how many problems in Level 1/2
        weak_problem_ids = [r.problem_id for r in all_records if r.mastery_level in [1, 2]]
        
        # Pick 3 review problems from weak list
        review_problems = []
        if weak_problem_ids:
            import random
            selected_ids = random.sample(weak_problem_ids, min(3, len(weak_problem_ids)))
            review_problems = self.db.query(Problem).filter(Problem.id.in_(selected_ids)).all()
            
        # 2. Generate PDF
        # Ensure user-specific filename to avoid collision? 
        # Or just timestamp. User ID in filename is safer.
        filename = f"weekly_report_user{user_id}_{week_start.isoformat()}.pdf"
        output_dir = "backend/uploads/reports"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        file_path = os.path.join(output_dir, filename)
        
        self._create_pdf(file_path, week_start, end_date, problems_count, reviews_count, mastery_counts, review_problems)
        
        # 3. Save to DB
        summary = {
            "uploaded": problems_count,
            "reviews": reviews_count,
            "mastery": mastery_counts
        }
        
        report = WeeklyReport(
            user_id=user_id,
            week_start=week_start,
            pdf_path=f"reports/{filename}",
            summary_json=summary
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def _create_pdf(self, path, start, end, uploaded, reviews, mastery, problems):
        doc = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Header
        elements.append(Paragraph(f"Weekly Learning Report", styles['Title']))
        elements.append(Paragraph(f"{start} to {end}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Stats Table
        data = [
            ["Metric", "Count"],
            ["Problems Uploaded", str(uploaded)],
            ["Reviews Completed", str(reviews)],
            ["Mastered (Level 3)", str(mastery.get(3, 0))],
            ["In Progress (Level 2)", str(mastery.get(2, 0))],
            ["Needs Work (Level 1)", str(mastery.get(1, 0))],
        ]
        
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 40))
        
        # Review Problems
        if problems:
            elements.append(Paragraph("Recommended Review Problems", styles['Heading2']))
            for p in problems:
                elements.append(Paragraph(f"Problem #{p.id} (Difficulty: {p.difficulty or '?'})", styles['Heading3']))
                # If image exists, add it
                if p.image_path:
                    # p.image_path is likely just filename or relative path
                    img_path = os.path.join("backend/uploads", p.image_path.split('/')[-1]) 
                    
                    if not os.path.exists(img_path) and "backend" not in p.image_path:
                         img_path = os.path.join("backend/uploads", p.image_path)
                        
                    if os.path.exists(img_path):
                        try:
                            # Constrain width
                            im = Image(img_path, width=200, height=150) # Approx aspect ratio
                            im.hAlign = 'LEFT'
                            elements.append(im)
                        except:
                            elements.append(Paragraph("[Image processing failed]", styles['Normal']))
                
                elements.append(Spacer(1, 10))
                if p.latex_content:
                    # ReportLab doesn't render Latex natively nicely without plugins
                    # converting latex to text/image is hard here.
                    # Just dumping text for now.
                    elements.append(Paragraph(f"LaTeX: {p.latex_content[:200]}...", styles['Normal']))
                
                elements.append(Spacer(1, 20))
        
        doc.build(elements)
