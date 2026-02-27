import os
import google.generativeai as genai
import PIL.Image
from dotenv import load_dotenv
import json
import re
import glob

load_dotenv()

from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional

class AIAnalysisResponse(BaseModel):
    latex_content: str
    ai_analysis: Dict[str, Any]
    difficulty: int
    knowledge_points: List[str]
    knowledge_path: Optional[str] = None

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not set")
        else:
            genai.configure(api_key=api_key)

    async def call_gemini_with_fallback(self, category: str, prompt: str, image_path: str = None) -> str:
        """
        Routes request to PRIMARY model for category, falls back to FALLBACK model on failure.
        Categories: 'vision', 'teaching', 'utility'
        """
        # Resolve model names
        primary_env = f"MODEL_{category.upper()}_PRIMARY"
        fallback_env = f"MODEL_{category.upper()}_FALLBACK"
        
        primary_model = os.getenv(primary_env)
        fallback_model = os.getenv(fallback_env)
        
        # Default safety net
        if not primary_model:
            primary_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
            print(f"Warning: {primary_env} not set. Defaulting to {primary_model}")

        candidates = [(primary_model, "Primary")]
        if fallback_model and fallback_model != primary_model:
            candidates.append((fallback_model, "Fallback"))

        last_error = None
        
        for model_name, role in candidates:
            try:
                print(f"[{category.upper()}] Calling {role} model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                generation_config = {"response_mime_type": "application/json"}
                
                content = [prompt]
                if image_path:
                    # Note: PIL.Image.open is lazy, load() makes it eager.
                    # Opening is fast, processing happens at send.
                    # We open fresh for each attempt to avoid closed file issues if any.
                    img = PIL.Image.open(image_path)
                    content.append(img)
                
                # Use async generation
                response = await model.generate_content_async(
                    content,
                    generation_config=generation_config
                )
                
                return response.text
                
            except Exception as e:
                print(f"[WARNING] 主模型 {model_name} ({role}) 调用失败，正在切换至备选模型 (if available)。Error: {e}")
                last_error = e
                # loop continues to fallback
                
        raise last_error or Exception("All models failed")

    def _load_reference_context(self) -> str:
        """
        Loads text content from backend/reference_docs/ to inject into the prompt.
        """
        context_parts = []
        # Calculate absolute path: current file is in backend/app/services/, so go up 3 levels to backend/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        doc_dir = os.path.join(base_dir, "reference_docs")
        
        if not os.path.exists(doc_dir):
            return ""

        # Read .txt and .md files
        files = []
        for ext in ["*.txt", "*.md"]:
            files.extend(glob.glob(os.path.join(doc_dir, ext)))
            
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    filename = os.path.basename(file_path)
                    content = f.read()
                    context_parts.append(f"--- Document: {filename} ---\n{content}\n")
            except Exception as e:
                print(f"Error reading reference doc {file_path}: {e}")
                
        if not context_parts:
            return ""
            
        return "REFERENCE CONTEXT (Shanghai Local Standards):\n" + "\n".join(context_parts)


    async def analyze_image(self, image_path: str):
        print(f"Analyzing image: {image_path}")
        
        # Load reference context
        reference_context = self._load_reference_context()
        
        knowledge_mapping = {
            "集合与逻辑": "SH_MATH.01",
            "集合的概念与运算": "SH_MATH.01.01",
            "命题、定理与逻辑联结词": "SH_MATH.01.02",
            "充分条件与必要条件": "SH_MATH.01.03",
            "不等式": "SH_MATH.02",
            "不等式的性质与解法": "SH_MATH.02.01",
            "基本不等式及其应用": "SH_MATH.02.02",
            "函数": "SH_MATH.03",
            "函数的概念、定义域与值域": "SH_MATH.03.01",
            "函数的性质": "SH_MATH.03.02",
            "幂、指、对函数": "SH_MATH.03.03",
            "函数的零点与方程的解": "SH_MATH.03.04",
            "三角函数": "SH_MATH.04",
            "三角函数的概念": "SH_MATH.04.01",
            "同角三角函数关系与诱导公式": "SH_MATH.04.02",
            "三角恒等变换": "SH_MATH.04.03",
            "三角函数的图像与性质": "SH_MATH.04.04",
            "解三角形": "SH_MATH.04.05",
            "数列与数学归纳法": "SH_MATH.05",
            "数列的概念与通项公式": "SH_MATH.05.01",
            "等差数列与等比数列": "SH_MATH.05.02",
            "数列的求和方法": "SH_MATH.05.03",
            "数列的极限与数学归纳法": "SH_MATH.05.04",
            "平面向量与复数": "SH_MATH.06",
            "平面向量的线性运算与坐标表示": "SH_MATH.06.01",
            "平面向量的数量积及其应用": "SH_MATH.06.02",
            "复数的概念与代数运算": "SH_MATH.06.03",
            "解析几何": "SH_MATH.07",
            "直线与方程": "SH_MATH.07.01",
            "圆的方程与位置关系": "SH_MATH.07.02",
            "椭圆的方程与性质": "SH_MATH.07.03",
            "双曲线与抛物线的方程与性质": "SH_MATH.07.04",
            "圆锥曲线综合问题": "SH_MATH.07.05",
            "立体几何": "SH_MATH.08",
            "空间几何体的表面积与体积": "SH_MATH.08.01",
            "点、线、面的位置关系": "SH_MATH.08.02",
            "空间向量的应用": "SH_MATH.08.03",
            "概率与统计": "SH_MATH.09",
            "排列、组合与二项式定理": "SH_MATH.09.01",
            "古典概型与条件概率": "SH_MATH.09.02",
            "随机变量及其分布": "SH_MATH.09.03",
            "统计基础与正态分布": "SH_MATH.09.04",
            "导数及其应用": "SH_MATH.10",
            "导数的概念与运算": "SH_MATH.10.01",
            "导数与函数单调性及极值": "SH_MATH.10.02",
            "导数综合问题": "SH_MATH.10.03"
        }
        
        mapping_str = "\n".join([f"- {k}: {v}" for k, v in knowledge_mapping.items()])

        prompt = rf"""
        You are a math expert. Analyze this image.
        
        {reference_context}
        
        SHANGHAI MATH KNOWLEDGE MAPPING:
        {mapping_str}
        
        1. Extract the math problem into LaTeX format.
        2. Provide a brief HINT or breakthrough point (max 2-3 sentences) in `thinking_process` (in Simplified Chinese).
        3. Provide the COMPLETE step-by-step solution in `solution` (in Simplified Chinese).
           - USE "\n" to separate each step clearly.
           - Format: "Step 1: ...\nStep 2: ...\nAnswer: ..."
        4. Identify key knowledge points from the mapping provided above.
        5. Estimate difficulty (1-5).
        6. REQUIRED: Select the most relevant `knowledge_path` from the mapping above. If no exact match, use the closest parent (e.g., 'SH_MATH.03' for a generic function problem).
        
        Return strictly valid JSON matching this schema.
        IMPORTANT: 
        1. For any LaTeX content, you MUST double-escape all backslashes. (e.g. "\\frac" instead of "\frac")
        2. You MUST enclose ALL mathematical expressions and LaTeX commands (including underlines \underline{{}}, spacing \qquad) in single dollar signs $. 
           Example: "The answer is $\\underline{{\\qquad}}$." NOT "The answer is \\underline{{\\qquad}}."

        {{
            "latex_content": "latex_string",
            "difficulty": int,
            "knowledge_points": ["知识点1", "知识点2"],
            "knowledge_path": "SH_MATH.XX.XX",
            "ai_analysis": {{
                "topic": ["主题"],
                "solution": "markdown_string_with_latex (Full Solution)",
                "thinking_process": "string (Hint/Breakthrough Point)"
            }}
        }}
        """

        try:
            # Route to VISION models
            text = await self.call_gemini_with_fallback('vision', prompt, image_path)
            
            # Clean up markdown
            text = re.sub(r'```json\n|\n```', '', text).strip()
            print(f"DEBUG: AI Raw Text: {text[:500]}...")

            # Parse JSON
            data = json.loads(text)
            
            # Validate with Pydantic
            validated_data = AIAnalysisResponse(**data)
            
            # Robustly fix LaTeX delimiters
            validated_data.latex_content = self._fix_latex(validated_data.latex_content)
            
            return validated_data.dict()

        except Exception as e:
            print(f"Analysis failed: {e}")
            return {
                "latex_content": "\\text{Analysis Failed}",
                "difficulty": 1,
                "ai_analysis": {"error": f"Failed: {str(e)}"},
                "knowledge_points": []
            }


    def _fix_latex(self, text: str) -> str:
        """
        Post-procesing to ensure specific LaTeX commands are wrapped in $...$
        """
        if not text:
            return text

        # Specific fix for the user's issue: \underline{\qquad}
        # A specialized regex that looks for \underline{...} NOT preceded by $
        text = re.sub(r'(?<!\$)\\\\underline\\{.*?\\}', r'$\g<0>$', text)
        return text

    async def generate_similar_problems(self, original_latex: str, knowledge_points: List[str] = []) -> List[Dict[str, Any]]:
        """
        Generates 2 similar practice problems based on the original problem.
        Uses UTILITY models.
        """
        kp_str = ", ".join(knowledge_points) if knowledge_points else "General Math"
        
        prompt = f"""
        Role: Math Teacher.
        Task: Create 2 NEW math problems that are similar to the following problem, testing the same knowledge points ({kp_str}) and having the same difficulty level.
        
        Original Problem (LaTeX):
        {original_latex}
        
        Requirements:
        1. CHANGE the numbers and specific context, but keep the core logic/method same.
        2. Output purely as a JSON list.
        3. Double escape backslashes in LaTeX strings (e.g. \\\\frac).
        
        Output Schema (JSON List):
        [
            {{
                "latex": "Problem 1 LaTeX string",
                "answer": "Short answer string",
                "solution": "Step-by-step solution string",
                "id": 1
            }},
            {{
                "latex": "Problem 2 LaTeX string",
                "answer": "Short answer string",
                "solution": "Step-by-step solution string",
                "id": 2
            }}
        ]
        """
        
        try:
            # Route to UTILITY models
            text = await self.call_gemini_with_fallback('utility', prompt)
            
            # Clean and parse
            text = re.sub(r'```json\n|\n```', '', text).strip()
            data = json.loads(text)
            
            if isinstance(data, list):
                # Basic Post-processing to ensure LaTeX is valid
                for item in data:
                    if 'latex' in item:
                        item['latex'] = self._fix_latex(item['latex'])
            return data
            
        except Exception as e:
            print(f"Error generating similar problems: {e}")
            return []

    async def analyze_solution(self, problem_latex: str, standard_solution: str, solution_image_path: str):
        """
        Analyzes a student's handwritten solution against the problem and standard solution.
        Uses TEACHING models (high reasoning capability).
        """
        prompt = f"""
        Role: Expert Math Tutor.
        Task: Check the student's solution image against the problem and standard solution.
        
        Problem (LaTeX):
        {problem_latex}
        
        Standard Solution (Reference):
        {standard_solution}
        
        Requirements:
        1. Identify the student's logical steps.
        2. Detect any calculation or logic errors.
        3. Provide constructive suggestions.
        4. Score the solution (0-100).
        
        Output strictly as JSON:
        {{
            "score": int,
            "logic_gaps": ["gap1", "gap2"],
            "calculation_errors": ["error1"],
            "suggestions": "Markdown string with feedback"
        }}
        """
        
        try:
            # Route to TEACHING models
            text = await self.call_gemini_with_fallback('teaching', prompt, solution_image_path)
            
            text = re.sub(r'```json\n|\n```', '', text).strip()
            data = json.loads(text)
            return data
            
        except Exception as e:
            print(f"Error analyzing solution: {e}")
            return {
                "score": 0,
                "logic_gaps": [],
                "calculation_errors": ["Error processing solution analysis"],
                "suggestions": f"Analysis failed: {str(e)}"
            }
