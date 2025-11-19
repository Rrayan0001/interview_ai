import os
import sys
import tempfile
import json
import re
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import TypedDict

# Add parent directory to path to import pdf_to_text_groq
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from pdf_to_text_groq import read_pdf_text, clean_with_groq_llm
except ImportError:
    print("Warning: pdf_to_text_groq not found, some features may be unavailable")
    read_pdf_text = None
    clean_with_groq_llm = None

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="AI Interview Bot API", version="1.0.0")

# CORS configuration
_default_dev_origins = ["http://localhost:10000", "http://127.0.0.1:10000", "http://localhost:3000"]
_frontend_origin_raw = os.getenv("FRONTEND_ORIGIN", "").strip()
if not _frontend_origin_raw:
    allowed_origins = _default_dev_origins
elif _frontend_origin_raw == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in _frontend_origin_raw.split(",") if origin.strip()]
    if not allowed_origins:
        allowed_origins = _default_dev_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def get_groq_key() -> Optional[str]:
    key = os.environ.get("GROQ_API_KEY")
    return key.strip() if key else None

def get_db_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url else None

# Pydantic models
class ExperienceItem(BaseModel):
    title: str
    company: Optional[str] = ""
    location: Optional[str] = ""
    start: Optional[str] = ""
    end: Optional[str] = ""
    bullets: Optional[List[str]] = []

class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = ""
    field: Optional[str] = ""
    start: Optional[str] = ""
    end: Optional[str] = ""
    grade_type: Optional[str] = ""
    grade_value: Optional[str] = ""

class ProjectItem(BaseModel):
    name: str
    description: Optional[str] = ""
    tech_stack: Optional[List[str]] = []

class SkillsItem(BaseModel):
    programming_languages: Optional[List[str]] = []
    frameworks_libraries: Optional[List[str]] = []
    tools: Optional[List[str]] = []
    other: Optional[List[str]] = []

class LinksItem(BaseModel):
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    portfolio: Optional[str] = ""
    other: Optional[List[str]] = []

class ResumeSchema(BaseModel):
    name: str
    email: str
    phone: str
    links: LinksItem
    summary: Optional[str] = ""
    education: List[EducationItem]
    experience: List[ExperienceItem]
    projects: List[ProjectItem]
    skills: SkillsItem

def _fallback_minimal_parse(text: str) -> Dict[str, Any]:
    """Lightweight regex-based parser fallback"""
    email = ""
    phone = ""
    tenth = ""
    twelfth = ""
    degree = ""
    name = ""
    
    try:
        m_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if m_email:
            email = m_email.group(0)
    except Exception:
        pass
    
    try:
        m_phone = re.search(r"(?:\+\d{1,3}[\s-]?)?\d{10}", text)
        if m_phone:
            phone = m_phone.group(0)
    except Exception:
        pass
    
    try:
        # Extract 10th percentage
        tenth_patterns = [
            r"10th[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"10[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"(?:SSLC|SSC)[:\s]+(\d{1,2}(?:\.\d+)?%)",
        ]
        for pattern in tenth_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                tenth = m.group(1) if m.groups() else m.group(0)
                break
        
        # Extract 12th percentage - look for "2 PU", "2pu", "2 pu", "PUC", "HSC"
        twelfth_patterns = [
            r"(?:12th|2\s*PU|2PU|PUC|HSC)[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"(\d{1,2}(?:\.\d+)?%)(?=.*(?:12th|2\s*PU|2PU|PUC|HSC))",
        ]
        for pattern in twelfth_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                twelfth = m.group(1) if m.groups() else m.group(0)
                break
        
        if not tenth or not twelfth:
            percents = re.findall(r"(\d{1,2}(?:\.\d+)?%)", text)
            if percents and not tenth:
                tenth = percents[0]
            if len(percents) > 1 and not twelfth:
                twelfth = percents[1]
    except Exception:
        pass
    
    try:
        cgpa = re.search(r"(\d(?:\.\d+)?\s*/\s*10(?:\.0)?)", text)
        if cgpa:
            degree = cgpa.group(1).replace(" ", "")
    except Exception:
        pass
    
    # Name extraction
    for line in text.splitlines():
        ln = line.strip()
        if len(ln.split()) >= 2 and len(ln) <= 80:
            name = ln
            break
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "experience": [],
        "tenth_percentage": tenth,
        "twelfth_percentage": twelfth,
        "degree_percentage_or_cgpa": degree,
    }

# Endpoints
@app.get("/")
def home():
    return {"status": "backend is live", "version": "1.0.0"}

@app.get("/health")
def health():
    """Health check endpoint"""
    db_ok = False
    try:
        db_url = get_db_url()
        if db_url:
            import psycopg
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False
    
    return {
        "status": "ok",
        "db": "ok" if db_ok else "not_configured"
    }

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.1-8b-instant"):
    """
    Upload and parse resume PDF.
    Returns extracted information including name, email, phone, percentages, and experience.
    """
    if not read_pdf_text:
        raise HTTPException(status_code=500, detail="PDF parsing not available")
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        text = read_pdf_text(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF")

        fallback_payload = _fallback_minimal_parse(text)

        key = get_groq_key()
        if not key:
            fallback_payload["note"] = "GROQ_API_KEY not configured; returned minimal parse."
            return fallback_payload

        # LLM cleanup if requested
        if cleanup and clean_with_groq_llm:
            try:
                text = clean_with_groq_llm(text, model=model, api_key=key, verbose=False)
            except Exception as e:
                print(f"Warning: LLM cleanup failed: {e}", file=sys.stderr)

        # Use Groq for structured parsing
        try:
            from groq import Groq
            client = Groq(api_key=key)
            
            schema = ResumeSchema.model_json_schema()
            system_prompt = (
                "Extract resume details from the provided text and return ONLY valid JSON matching this exact schema:\n"
                + json.dumps(schema, indent=2, ensure_ascii=False)
                + "\n\nCRITICAL: Return ONLY the JSON object. No markdown, no code blocks, no explanations. "
                "Populate all fields from the resume text. Use empty strings or empty arrays for missing data.\n\n"
                "IMPORTANT: For 12th percentage, look for variations like '12th', '2 PU', '2pu', '2 pu', 'PUC', or 'HSC'. "
                "For 10th percentage, look for '10th', 'SSLC', or 'SSC'. Extract the percentage values associated with these labels."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ]
            
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            
            clean_json = resp.choices[0].message.content or "{}"
            parsed = json.loads(clean_json)
            
            # Extract education data for percentages
            education_list = parsed.get("education", [])
            tenth_pct = ""
            twelfth_pct = ""
            degree_cgpa = ""
            
            for edu in education_list:
                institution_lower = (edu.get("institution", "") or "").lower()
                degree_lower = (edu.get("degree", "") or "").lower()
                field_lower = (edu.get("field", "") or "").lower()
                grade_value = edu.get("grade_value", "") or ""
                
                if any(term in institution_lower or term in degree_lower or term in field_lower 
                       for term in ["10th", "sslc", "ssc", "10"]):
                    tenth_pct = grade_value
                
                if any(term in institution_lower or term in degree_lower or term in field_lower 
                       for term in ["12th", "2 pu", "2pu", "puc", "hsc", "12"]):
                    twelfth_pct = grade_value
            
            # Fallback to regex if not found
            if not tenth_pct or not twelfth_pct:
                fallback = _fallback_minimal_parse(text)
                if not tenth_pct:
                    tenth_pct = fallback.get("tenth_percentage", "")
                if not twelfth_pct:
                    twelfth_pct = fallback.get("twelfth_percentage", "")
            
            if education_list:
                degree_cgpa = education_list[0].get("grade_value", "") or ""
            
            return {
                "name": parsed.get("name", ""),
                "email": parsed.get("email", ""),
                "phone": parsed.get("phone", ""),
                "experience": [
                    f"{exp.get('title', '')} @ {exp.get('company', '')}" 
                    if exp.get('company') else exp.get('title', '')
                    for exp in parsed.get("experience", [])
                ] if parsed.get("experience") else [],
                "tenth_percentage": tenth_pct,
                "twelfth_percentage": twelfth_pct,
                "degree_percentage_or_cgpa": degree_cgpa,
            }
        except ImportError:
            fallback_payload["note"] = "groq package not installed; returned minimal parse."
            return fallback_payload
        except Exception as e:
            print(f"Groq parsing failed: {e}", file=sys.stderr)
            return fallback_payload
    except HTTPException:
        raise
    except Exception as e:
        fallback_payload = {"note": f"Unexpected failure: {e}"}
        try:
            if "text" in locals() and text:
                fallback_payload.update(_fallback_minimal_parse(text))
            else:
                fallback_payload.update({
                    "name": "", "email": "", "phone": "", "experience": [],
                    "tenth_percentage": "", "twelfth_percentage": "", "degree_percentage_or_cgpa": ""
                })
        except Exception:
            pass
        return fallback_payload
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@app.post("/evaluate")
async def evaluate(payload: dict):
    """
    Evaluate candidate based on test results and resume data.
    Returns a score and evaluation metrics.
    """
    # Extract data from payload
    answers = payload.get("answers", [])
    totals = payload.get("totals", {})
    profile = payload.get("profile", {})
    
    # Calculate score (you can enhance this logic)
    overall_score = totals.get("overall", 0)
    total_questions = totals.get("totalQuestions", 1)
    score_percentage = (overall_score / total_questions * 100) if total_questions > 0 else 0
    
    return {
        "score": round(score_percentage, 2),
        "overall": overall_score,
        "total": total_questions,
        "aptitude": totals.get("aptitude", 0),
        "reasoning": totals.get("reasoning", 0),
        "coding": totals.get("coding", 0),
    }

@app.post("/generate-report")
async def generate_report(payload: dict):
    """
    Generate a comprehensive career development report using Groq LLM.
    """
    key = get_groq_key()
    if not key:
        return {"report_markdown": "# Report Generation Unavailable\n\nGROQ_API_KEY not configured."}
    
    try:
        from groq import Groq
        client = Groq(api_key=key)
        
        answers = payload.get("answers", [])
        totals = payload.get("totals", {})
        behavior = payload.get("behavior", {})
        profile = payload.get("profile", {})
        model = payload.get("model", "llama-3.1-8b-instant")
        
        system_prompt = (
            "You are a precise assessment analyst. Create a Career & Skill Development Report based solely on the provided data.\n"
            "Rules:\n"
            "- Use the user's results and academic profile only; do not invent data.\n"
            "- Professional tone, clear headings, bullet points where helpful.\n"
            "- Sections: Performance Analysis; Skill Gap Analysis; Personalized 6-Week Improvement Plan; Career Guidance; Internship Recommendations; Final Summary.\n"
            "- Keep recommendations realistic for current level. Do not include code fences.\n"
        )
        
        user_content = {
            "test_results": {
                "answers": answers,
                "totals": totals,
                "behavior": behavior,
            },
            "academic_profile": profile or {},
            "format_instructions": {
                "headings": True,
                "no_code": True,
                "language": "English",
            },
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
        ]
        
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        
        content = resp.choices[0].message.content or ""
        return {"report_markdown": content.strip()}
    except Exception as e:
        return {
            "report_markdown": f"# Report Generation Error\n\n{str(e)}",
            "error": str(e)
        }
