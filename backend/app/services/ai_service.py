import os
import google.generativeai as genai
import PIL.Image
from dotenv import load_dotenv
import json
import re

load_dotenv()

from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any

class AIAnalysisResponse(BaseModel):
    latex_content: str
    ai_analysis: Dict[str, Any]
    difficulty: int
    knowledge_points: List[str]

class AIService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not set")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
            print(f"Using Gemini Model: {model_name}")
            self.model = genai.GenerativeModel(model_name)

    async def analyze_image(self, image_path: str, retries: int = 3):
        print(f"Analyzing image: {image_path}")
        
        if not self.model:
             return {
                "latex_content": "\\text{AI Key Missing}",
                "difficulty": 1,
                "ai_analysis": {"error": "Please set GEMINI_API_KEY in .env"},
                "knowledge_points": []
            }
        
        prompt = r"""
        You are a math expert. Analyze this image.
        1. Extract the math problem into LaTeX format.
        2. Provide a brief HINT or breakthrough point (max 2-3 sentences) in `thinking_process` (in Simplified Chinese).
        3. Provide the COMPLETE step-by-step solution in `solution` (in Simplified Chinese).
           - USE "\n" to separate each step clearly.
           - Format: "Step 1: ...\nStep 2: ...\nAnswer: ..."
        4. Identify key knowledge points.
        5. Estimate difficulty (1-5).
        
        Return strictly valid JSON matching this schema.
        IMPORTANT: 
        1. For any LaTeX content, you MUST double-escape all backslashes. (e.g. "\\frac" instead of "\frac")
        2. You MUST enclose ALL mathematical expressions and LaTeX commands (including underlines \underline{}, spacing \qquad) in single dollar signs $. 
           Example: "The answer is $\\underline{\\qquad}$." NOT "The answer is \\underline{\\qquad}."

        {
            "latex_content": "latex_string",
            "difficulty": int,
            "knowledge_points": ["知识点1", "知识点2"],
            "ai_analysis": {
                "topic": ["主题"],
                "solution": "markdown_string_with_latex (Full Solution)",
                "thinking_process": "string (Hint/Breakthrough Point)"
            }
        }
        """

        import time

        for attempt in range(retries):
            try:
                img = PIL.Image.open(image_path)
                
                # Use JSON mode for robustness
                generation_config = {"response_mime_type": "application/json"}
                
                response = self.model.generate_content(
                    [prompt, img], 
                    generation_config=generation_config
                )
                text = response.text
                
                # Clean up markdown
                text = re.sub(r'```json\n|\n```', '', text).strip()
                
                print(f"DEBUG: AI Raw Text: {text[:500]}...") # Print first 500 chars

                # Parse JSON
                data = json.loads(text)
                print(f"DEBUG: Parsed JSON keys: {data.keys()}")
                if "ai_analysis" in data:
                    print(f"DEBUG: ai_analysis keys: {data['ai_analysis'].keys()}")
                
                # Validate with Pydantic
                validated_data = AIAnalysisResponse(**data)
                
                # Robustly fix LaTeX delimiters
                validated_data.latex_content = self._fix_latex(validated_data.latex_content)
                
                return validated_data.dict()

            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Attempt {attempt + 1} failed (Parse/Validaton): {e}")
                if attempt == retries - 1:
                    return {
                        "latex_content": "\\text{Analysis Failed}",
                        "difficulty": 1,
                        "ai_analysis": {"error": f"Failed after {retries} attempts: {str(e)}"},
                        "knowledge_points": []
                    }
            except Exception as e:
                print(f"Attempt {attempt + 1} failed (API/System): {e}")
                # Check for rate limit or other retryable errors
                if "429" in str(e) or "Quota" in str(e) or "Resource has been exhausted" in str(e):
                    print("Rate limit hit. Waiting 5 seconds...")
                    time.sleep(5)
                else:
                    # For other errors, maybe wait a bit less
                    time.sleep(1)

                if attempt == retries - 1:
                    return {
                        "latex_content": "\\text{Error}",
                        "difficulty": 1,
                        "ai_analysis": {"error": str(e)},
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
        text = re.sub(r'(?<!\$)\\underline\{.*?\}', r'$\g<0>$', text)
        return text


