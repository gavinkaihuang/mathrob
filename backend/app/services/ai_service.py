import os
import google.generativeai as genai
import PIL.Image
from dotenv import load_dotenv
import json
import re
import glob
from google.api_core import exceptions as google_exceptions

load_dotenv()

from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any, Optional
import traceback
from ..database import SessionLocal
from ..models import SystemLog, APICallLog
from .token_manager import token_manager

class AIAnalysisResponse(BaseModel):
    latex_content: str
    ai_analysis: Dict[str, Any]
    difficulty: int
    knowledge_points: List[str]
    knowledge_path: Optional[str] = None

class AIServiceException(Exception):
    def __init__(self, message: str, error_type: str, retry_seconds: Optional[int] = None):
        super().__init__(message)
        self.error_type = error_type
        self.retry_seconds = retry_seconds

class AIService:
    def __init__(self):
        # Global genai token configure removed. Managed dynamically per-request.
        pass

    def _log_system_error(self, category: str, message: str, details: Any = None):
        try:
            db = SessionLocal()
            log_entry = SystemLog(
                level="ERROR",
                category=category,
                message=message,
                details=details
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as e:
            print(f"Failed to write to system_logs: {e}")

    def _log_api_call(self, category: str, action_type: str, model_used: str, token_name: str, target_id: int = None):
        """Records a successful AI model call."""
        try:
            db = SessionLocal()
            log_entry = APICallLog(
                category=category.upper(),
                action_type=action_type,
                target_id=target_id,
                model_used=model_used,
                token_name=token_name
            )
            db.add(log_entry)
            db.commit()
            db.close()
            print(f"[LOG] Recorded {action_type} for model {model_used} using {token_name}")
        except Exception as e:
            print(f"Failed to write to api_call_logs: {e}")

    async def call_gemini_with_fallback(self, category: str, prompt: str, image_path: str = None) -> tuple[str, str]:
        """
        Routes request to the appropriate model based on configuration in the DB.
        Categories: 'vision', 'teaching', 'utility'
        Returns: (response_text, used_model_name)
        """
        from .model_manager import model_manager
        
        last_error = None
        max_token_retries = 3 
        token_retry_count = 0
        model_name = "unknown"
        
        while token_retry_count < max_token_retries:
            db_session = SessionLocal()
            try:
                # Resolve active model from DB cache
                model_name = model_manager.get_model_name(db_session, category)
                
                # Retrieve active API Token
                current_token_record = token_manager.get_available_token(db_session)
                current_token = current_token_record.api_key
                token_id = current_token_record.id
                token_name = current_token_record.name
                
                # Configure module for this API call
                genai.configure(api_key=current_token)
                
                print(f"[{category.upper()}] Calling model: {model_name} with Token {token_name} (Attempt {token_retry_count + 1})")
                model = genai.GenerativeModel(model_name)
                
                generation_config = {"response_mime_type": "application/json"}
                
                content = [prompt]
                if image_path:
                    img = PIL.Image.open(image_path)
                    content.append(img)
                
                # Use async generation
                response = await model.generate_content_async(
                    content,
                    generation_config=generation_config
                )
                
                db_session.close()
                return response.text, model_name, token_name
                
            except google_exceptions.ResourceExhausted as e:
                # 429 - Rate limit / Quota exceeded
                print(f"[WARNING] 触发限频或配额耗尽 (Token: {token_name}): {e}")
                token_manager.report_token_error(db_session, token_id, token_name, str(e))
                token_retry_count += 1
                db_session.close()
                continue
                
            except (google_exceptions.ServiceUnavailable, google_exceptions.InternalServerError, google_exceptions.DeadlineExceeded) as e:
                # 5xx or transient timeout - Cooldown and retry
                print(f"[WARNING] 服务暂时不可用 (Token: {token_name}): {e}")
                token_manager.report_token_error(db_session, token_id, token_name, str(e))
                token_retry_count += 1
                db_session.close()
                continue
                
            except (google_exceptions.NotFound, google_exceptions.InvalidArgument) as e:
                # 404 or 400 - Model name typo or invalid param
                # CRITICAL: Do NOT put token in cooldown, stop retrying immediately.
                print(f"[CRITICAL] 模型配置错误！请检查 ModelConfig 表中的 model_name. Error: {e}")
                db_session.close()
                raise AIServiceException(f"模型配置错误，请检查模型名称: {str(e)}", "config_error")
                
            except (google_exceptions.Unauthenticated, google_exceptions.PermissionDenied) as e:
                # 401 or 403 - Auth issues
                print(f"[CRITICAL] API 认证失败 (Token: {token_name}): {e}")
                db_session.close()
                raise AIServiceException(f"API 密钥无效或无权访问模型: {str(e)}", "auth_error")

            except Exception as e:
                # Unknown error
                print(f"[ERROR] 模型 {model_name} 调用发生未知错误: {e}")
                db_session.close()
                last_error = e
                break

        # If we got here, all attempts failed
        error_msg = f"Model generation failed for {category}. Last error: {str(last_error)}"
        
        # Parse specific errors for the user UI
        last_error_str = str(last_error).lower()
        retry_seconds = None
        
        # Try to parse 'retry_delay { seconds: X }'
        retry_match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)\s*\}', str(last_error))
        if retry_match:
            retry_seconds = int(retry_match.group(1))

        if isinstance(last_error, google_exceptions.ResourceExhausted):
            self._log_system_error(category, f"Rate Limit Exceeded (429): {str(last_error)}", {"primary": model_name, "fallback": None, "traceback": traceback.format_exc() if last_error else None})
            raise AIServiceException("AI Model Rate Limit Exceeded", "rate_limit", retry_seconds)
            
        elif isinstance(last_error, (google_exceptions.Unauthenticated, google_exceptions.PermissionDenied)):
            self._log_system_error(category, f"Authentication Error: {str(last_error)}", {"primary": model_name, "fallback": None, "traceback": traceback.format_exc() if last_error else None})
            raise AIServiceException("AI Model Authentication Failed", "auth_error")
            
        elif isinstance(last_error, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded, google_exceptions.InternalServerError)):
            self._log_system_error(category, f"Service Unavailable: {str(last_error)}", {"primary": model_name, "fallback": None, "traceback": traceback.format_exc() if last_error else None})
            raise AIServiceException("AI Model Service Unavailable", "service_error")
            
        self._log_system_error(category, error_msg, {"primary": model_name, "fallback": None, "traceback": traceback.format_exc() if last_error else None})
        raise last_error or Exception(error_msg)


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
            text, used_model, used_token = await self.call_gemini_with_fallback('vision', prompt, image_path)
            
            # Clean up markdown
            text = re.sub(r'```json\n|\n```', '', text).strip()
            print(f"DEBUG: AI Raw Text: {text[:500]}...")

            # Parse JSON - Use a more robust approach
            try:
                data = json.loads(text)
                
                # Log success
                self._log_api_call("VISION", "PARSE_PROBLEM", used_model, used_token)
            except json.JSONDecodeError as je:
                print(f"Standard JSON parse failed, trying robust mode: {je}")
                # Try to handle common LaTeX backslash issues by allowing control characters
                # and potentially raw backslashes if the model sent them.
                try:
                    data = json.loads(text, strict=False)
                except Exception as e2:
                    # Final attempt: global escape backslashes that are not already escaped
                    # This is tricky without a proper parser, but a common fix for LaTeX JSON:
                    # Note: We only do this if everything else fails.
                    escaped_text = text.replace('\\', '\\\\')
                    escaped_text = escaped_text.replace('\\\\"', '\\"')
                    escaped_text = escaped_text.replace('\\\\n', '\\n')
                    escaped_text = escaped_text.replace('\\\\t', '\\t')
                    data = json.loads(escaped_text, strict=False)
            
            # Validate with Pydantic
            validated_data = AIAnalysisResponse(**data)
            
            # Robustly fix LaTeX delimiters
            validated_data.latex_content = self._fix_latex(validated_data.latex_content)
            
            result = validated_data.dict()
            result["ai_model"] = used_model
            return result

        except AIServiceException as e:
            raise e
        except Exception as e:
            print(f"Analysis failed: {e}")
            self._log_system_error("vision", f"Vision Analysis Failed: {str(e)}", {"traceback": traceback.format_exc()})
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

    async def generate_similar_problems(self, original_latex: str, knowledge_points: List[str] = [], difficulty: int = 1, knowledge_path_name: str = "相关知识点", target_id: int = None) -> Dict[str, Any]:
        """
        Generates 2 similar practice problems with rich context and rigorous prompt.
        """
        kp_str = ", ".join(knowledge_points) if knowledge_points else knowledge_path_name
        
        prompt = f"""
        # Role
        You are an expert Math Teacher specialized in the Shanghai High School Mathematics curriculum.
        
        # Task
        Based on the following ORIGINAL problem, create 2 NEW variations for student practice.
        
        # Context
        - Original Problem (LaTeX): {original_latex}
        - Primary Knowledge Point: {knowledge_path_name}
        - Additional Points: {kp_str}
        - Target Difficulty: {difficulty} (Scale 1-5)
        
        # Generation Guidelines (STRICT)
        1. **Consistency**: The new problems MUST test the same core mathematical concepts and stay within the High School curriculum scope.
        2. **Variation**: CHANGE the scenario, variables, or numeric data. Avoid simple duplication.
        3. **Rigorous Design**: 
           - Ensure the problem is mathematically sound and has a unique, solvable answer.
           - Avoid "degenerate cases" or "excessive computation".
           - Maintain the target difficulty level.
        4. **Language**: Use Simplified Chinese.
        
        # Format Requirements
        - Use standard LaTeX for formulas, enclosed in single dollar signs $.
        - Double-escape backslashes in JSON strings (e.g., "\\\\frac").
        - Output strictly valid JSON.
        
        # Output Schema
        {{
            "problems": [
                {{
                    "latex": "Problem LaTeX string",
                    "thinking_process": "Brief hint/breakthrough point",
                    "solution": "Step-by-step detailed solution",
                    "answer": "Final concise answer"
                }}
            ]
        }}
        """
        
        try:
            # Route to UTILITY/REASONING models
            text, used_model, used_token = await self.call_gemini_with_fallback('utility', prompt)
            
            # Clean and parse
            text = re.sub(r'```json\n|\n```', '', text).strip()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError as je:
                print(f"Standard JSON parse failed, trying robust mode: {je}")
                try:
                    data = json.loads(text, strict=False)
                except Exception as e2:
                    escaped_text = text.replace('\\', '\\\\')
                    escaped_text = escaped_text.replace('\\\\"', '\\"')
                    escaped_text = escaped_text.replace('\\\\n', '\\n')
                    escaped_text = escaped_text.replace('\\\\t', '\\t')
                    data = json.loads(escaped_text, strict=False)
            
            problems = data.get("problems", [])
            
            # Post-processing
            for item in problems:
                if 'latex' in item:
                    item['latex'] = self._fix_latex(item['latex'])
            
            # Log success
            self._log_api_call("UTILITY", "GENERATE_SIMILAR", used_model, used_token, target_id=target_id)
            
            return {
                "problems": problems,
                "ai_model": used_model
            }
            
        except AIServiceException as e:
            raise e
        except Exception as e:
            print(f"Error generating similar problems: {e}")
            self._log_system_error("utility", f"Practice Generation Failed: {str(e)}", {"traceback": traceback.format_exc()})
            return {"problems": [], "error": str(e)}

    async def generate_variation(self, original_latex: str, knowledge_tag: str, quantity: int, difficulty: int = 1) -> Dict[str, Any]:
        """
        [NEW] Mutates an existing problem to dynamically generate practice variations, focusing heavily on a specific `knowledge_tag` deficit.
        """
        prompt = f"""
        # Role
        你是一个资深的数学教研专家。学生目前在【{knowledge_tag}】上存在薄弱环节。

        # Task
        请根据以下他曾经做错的原题，生成 {quantity} 道难度相当、考察重点相似的“变式训练题”。

        # Context
        - Original Problem (LaTeX): {original_latex}
        - Target Knowledge Tag: {knowledge_tag}
        - Difficulty: {difficulty} (1-5)

        # Generation Guidelines (STRICT)
        1. 这 {quantity} 道题目必须紧紧围绕【{knowledge_tag}】这个薄弱点来进行定点攻克。
        2. 不要只是简单地改数字，可以适度变化考察的具体形态或切入角度。
        3. 必须保证数学推导的绝对严谨，且存在唯一解。
        4. 语言使用简体中文。
        
        # Format Requirements
        - 使用标准的 LaTeX 语法编写数学公式！务必将所有的公式包裹在【单美元符号 `$`】之中。
        - 确保 JSON 中的斜杠正确转义 (如 `\\\\frac`)。
        - 请务必返回合法的 JSON 结构，严格遵从下方示例。
        
        # Output Schema
        {{
            "problems": [
                {{
                    "question": "题干的 LaTeX",
                    "hint": "思路提示的简短文本",
                    "solution": "详细的标准解答（LaTeX格式）",
                    "knowledge_points": ["核心考点1", "核心考点2"]
                }}
            ]
        }}
        """

        try:
            # Reusing UTILITY/REASONING logic since we are generating varied practice problems
            text, used_model, used_token = await self.call_gemini_with_fallback('utility', prompt)
            
            text = re.sub(r'```json\n|\n```', '', text).strip()
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError as je:
                print(f"generate_variation JSON parse failed: {je}")
                try:
                    data = json.loads(text, strict=False)
                except Exception as e2:
                    escaped_text = text.replace('\\', '\\\\')
                    escaped_text = escaped_text.replace('\\\\"', '\\"')
                    escaped_text = escaped_text.replace('\\\\n', '\\n')
                    escaped_text = escaped_text.replace('\\\\t', '\\t')
                    data = json.loads(escaped_text, strict=False)
            
            problems = data.get("problems", [])
            for item in problems:
                if 'question' in item:
                    item['question'] = self._fix_latex(item['question'])
                if 'solution' in item:
                    item['solution'] = self._fix_latex(item['solution'])
            
            self._log_api_call("UTILITY", "GENERATE_VARIATION", used_model, used_token)
            
            return {
                "problems": problems,
                "ai_model": used_model
            }
        except Exception as e:
            print(f"Error generating variation: {e}")
            self._log_system_error("utility", f"generate_variation Failed: {str(e)}", {"traceback": traceback.format_exc()})
            return {"problems": [], "error": str(e)}

    async def analyze_solution(self, problem_latex: str, standard_solution: str, solution_image_path: str, target_id: int = None):
        """
        Analyzes a student's handwritten solution against the problem and standard solution.
        Uses TEACHING models (high reasoning capability).
        """
        prompt = f"""
        # Role
        你是一位资深的高中数学阅卷专家。请根据提供的标准答案，对学生上传的解答截图进行严格批改。

        # Context
        - Problem (LaTeX): {problem_latex}
        - Standard Solution (Reference): {standard_solution}
        
        # Grading Instructions (STRICT)
        在输出 JSON 格式的反馈时，除了检查数学逻辑和计算结果外，必须包含：
        1. 数学逻辑与计算结果分析。
        2. 卷面与规范诊断（`formatting_feedback`）：指出步骤缺失或卷面涂改等扣分风险。
        3. **知识点诊断（`knowledge_analysis`）**：列出该题涉及的核心知识点标签，并根据学生的作答情况，为每个知识点打出一个客观掌握分（1-10分）。

        # Output Format
        Return strictly valid JSON with the following fields:
        - score: int (0-100)
        - logic_gaps: list of strings (Issues with mathematical logic)
        - calculation_errors: list of strings (Arithmetic or algebraic errors)
        - formatting_feedback: string (Assessment of handwriting, neatness, and formal presentation)
        - suggestions: markdown string (General advice for improvement)
        - knowledge_analysis: array of objects [{{"tag": string, "score": int, "reason": string}}]

        {{
            "score": int,
            "logic_gaps": ["gap1", "gap2"],
            "calculation_errors": ["error1"],
            "formatting_feedback": "对卷面整洁度和规范性的详细点评",
            "suggestions": "Markdown string with feedback",
            "knowledge_analysis": [{{"tag": "对数运算", "score": 4, "reason": "底数变换公式运用错误"}}]
        }}
        """
        
        try:
            # Route to TEACHING models
            text, used_model, used_token = await self.call_gemini_with_fallback('teaching', prompt, solution_image_path)
            
            text = re.sub(r'```json\n|\n```', '', text).strip()
            data = json.loads(text)
            
            # Post-process to ensure formatting_feedback exists
            if "formatting_feedback" not in data:
                data["formatting_feedback"] = "未检测到明显的卷面规范问题。"
            
            # Log success
            self._log_api_call("TEACHING", "GRADE_SOLUTION", used_model, used_token, target_id=target_id)
                
            return {
                "feedback_json": data,
                "ai_model": used_model
            }
            
        except AIServiceException as e:
            raise e
        except Exception as e:
            print(f"Error analyzing solution: {e}")
            self._log_system_error("teaching", f"Solution Analysis Failed: {str(e)}", {"traceback": traceback.format_exc()})
            return {
                "score": 0,
                "logic_gaps": [],
                "calculation_errors": ["Error processing solution analysis"],
                "suggestions": f"Analysis failed: {str(e)}"
            }

    async def generate_diagnostic_report(self, learned_topics: List[str], assessment_results: List[Dict[str, Any]]) -> str:
        """
        [NEW] Generates a comprehensive markdown diagnostic report after an Assessment Session.
        """
        
        topics_str = ", ".join(learned_topics) if learned_topics else "全部已学知识点"
        results_json_str = json.dumps(assessment_results, ensure_ascii=False, indent=2)
        
        prompt = f"""
        # Role
        你是一位资深教研专家。学生刚刚完成了一次摸底测验。你需要根据他的测验表现，生成一份专业的学情诊断报告。

        # Context
        - 测试范围 (Learned Topics): {topics_str}
        - 测验表现与具体反馈 (Results JSON): 
        {results_json_str}

        # Reporting Guidelines (STRICT)
        1. 严禁对未包含在“测试范围”内的知识点进行评价。
        2. 基于本次摸底测验的真实得分、逻辑漏洞 (logic_gaps) 和计算错误 (calculation_errors)，给出针对性的知识点攻克优先级。
        3. 综合评估其卷面规范程度 (综合 formatting_feedback)。
        4. 使用极具亲和力但专业的口吻。
        5. 必须输出一份排版清晰、带有数学 LaTeX 公式的 Markdown 文档（公式需使用 `$` 包裹）。
        
        # Output Format
        直接返回纯 Markdown 文本，无需任何额外的代码块包装（如 ````markdown`）。包含以下模块：
        - 🌟 **总体评价** (Overall Assessment)
        - 📊 **核心表现诊断** (Performance Breakdown)
        - ⚠️ **重灾区预警** (Priority Weaknesses)
        - 📝 **卷面与考学习惯** (Presentation & Habits)
        - 🚀 **下一步突击计划** (Actionable Next Steps)
        """
        
        try:
            # Report generation requires strong reasoning, route to TEACHING model
            text, used_model, used_token = await self.call_gemini_with_fallback('teaching', prompt)
            
            # Clean possible markdown wrap
            text = text.removeprefix("```markdown\n").removesuffix("\n```").strip()
            
            self._log_api_call("TEACHING", "GENERATE_DIAGNOSTIC_REPORT", used_model, used_token)
            return text
            
        except Exception as e:
            print(f"Error generating diagnostic report: {e}")
            self._log_system_error("teaching", f"generate_diagnostic_report Failed: {str(e)}", {"traceback": traceback.format_exc()})
            return f"生成诊断报告失败: {str(e)}"
