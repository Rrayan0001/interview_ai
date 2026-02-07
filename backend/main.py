import os
import sys
import tempfile
import json
import re
import random
import zipfile
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

# CORS configuration - Explicitly allow Vercel frontend
_default_dev_origins = ["http://localhost:10000", "http://127.0.0.1:10000", "http://localhost:3000"]
_production_origins = ["https://interview-ai-one-mocha.vercel.app"]

_frontend_origin_raw = os.getenv("FRONTEND_ORIGIN", "").strip()
if not _frontend_origin_raw:
    # Default: allow dev origins + production Vercel URL
    allowed_origins = _default_dev_origins + _production_origins
elif _frontend_origin_raw == "*":
    allowed_origins = ["*"]
else:
    # Parse custom origins and always include production + dev
    allowed_origins = [origin.strip() for origin in _frontend_origin_raw.split(",") if origin.strip()]
    allowed_origins.extend(_production_origins)
    allowed_origins.extend(_default_dev_origins)
    # Remove duplicates while preserving order
    seen = set()
    allowed_origins = [x for x in allowed_origins if not (x in seen or seen.add(x))]

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
        
        # Extract 12th percentage - Widen search to include "Class 12", "XII", "Intermediate", "Pre-University College", "(PUC)"
        twelfth_patterns = [
            r"(?:12th|2\s*PU|2PU|PUC|HSC|II\s*PU|Class\s*12|XII|Intermediate|Pre[- ]?University|Pre[- ]?Univ)[:\s\-]+(\d{1,2}(?:\.\d+)?\s*%)",
            r"(?:12th|2\s*PU|2PU|PUC|HSC|II\s*PU|Class\s*12|XII|Intermediate|Pre[- ]?University|Pre[- ]?Univ).*?(\d{1,2}(?:\.\d+)?\s*%)",
            r"(\d{1,2}(?:\.\d+)?\s*%)(?=.*(?:12th|2\s*PU|2PU|PUC|HSC|II\s*PU|Class\s*12|XII|Intermediate|Pre[- ]?University|Pre[- ]?Univ))",
            # Look for number without % if explicitly labeled
            r"(?:12th|2\s*PU|2PU|PUC|HSC|II\s*PU|Class\s*12|XII|Intermediate|Pre[- ]?University|Pre[- ]?Univ).*?(\d+(?:\.\d+)?)\s*%",
            # Pattern for "(PUC)" or "Pre-University College"
            r"(?:\(PUC\)|Pre[- ]?University\s+College).*?(\d{1,2}(?:\.\d+)?\s*%)",
        ]
        for pattern in twelfth_patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if m:
                twelfth = m.group(1).strip() if m.groups() else m.group(0).strip()
                if not twelfth.endswith("%"):
                    twelfth += "%"
                break
        
        # Context-aware window search for 12th if regex failed
        if not twelfth:
            # Find keywords and look for percentages in +/- 60 chars
            keywords = ["12th", "puc", "hsc", "xii", "intermediate", "class 12", "2 pu", "pre-university", "pre university", "pre-univ", "(puc)"]
            for keyword in keywords:
                for m in re.finditer(re.escape(keyword), text, re.IGNORECASE):
                    start = max(0, m.start() - 60)
                    end = min(len(text), m.end() + 60)
                    window = text[start:end]
                    # Find percentage in this window
                    p_match = re.search(r"(\d{1,2}(?:\.\d+)?\s*%)", window)
                    if p_match:
                        val = p_match.group(1).replace(" ", "")
                        # Avoid if it's 10th/SSLC
                        if "10th" not in window.lower() and "sslc" not in window.lower() and "ssc" not in window.lower():
                            twelfth = val
                            break
                if twelfth: break

        # Only use fallback if specific patterns didn't match
        # This prevents confusing 10th and 12th percentages
        if not tenth or not twelfth:
            # Find all percentages with context
            all_percents = []
            for match in re.finditer(r"(\d{1,2}(?:\.\d+)?%)", text):
                percent = match.group(1)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].lower()
                
                # Classify based on nearby text
                if any(term in context for term in ["10th", "sslc", "ssc", "class 10", "x "]) and not tenth:
                    tenth = percent
                elif any(term in context for term in ["12th", "2 pu", "2pu", "puc", "hsc", "class 12", "xii", "intermediate", "pre-university", "pre university", "(puc)"]) and not twelfth:
                    twelfth = percent
                else:
                    all_percents.append((percent, context))
            
            # If still missing, use position-based assignment (10th usually comes before 12th)
            if not tenth and all_percents:
                tenth = all_percents[0][0]
            if not twelfth and len(all_percents) > 1:
                twelfth = all_percents[1][0]
            elif not twelfth and len(all_percents) == 1 and not tenth:
                # Only one percentage found, assume it's 10th
                tenth = all_percents[0][0]
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
    
    # Use "--" for missing data
    return {
        "name": name or "--",
        "email": email or "--",
        "phone": phone or "--",
        "experience": [],
        "tenth_percentage": tenth or "--",
        "twelfth_percentage": twelfth or "--",
        "degree_percentage_or_cgpa": degree or "--",
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

@app.post("/parse")
async def parse_resume(pdf: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.1-8b-instant"):
    """Alias for /upload-resume - maintains backward compatibility"""
    return await upload_resume(pdf, cleanup, model)

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
                "CRITICAL EDUCATION EXTRACTION RULES:\n"
                "- For 10th/SSLC/SSC: Look ONLY for '10th', 'SSLC', 'SSC', 'Class 10', or 'X'. DO NOT confuse with 12th.\n"
                "- For 12th/PUC/HSC: Look ONLY for '12th', '2 PU', '2pu', '2 pu', 'PUC', 'HSC', 'Class 12', 'II PUC', 'XII', 'Intermediate', 'Pre-University College', 'Pre-University', or '(PUC)'. "
                "These are DIFFERENT from 10th - do not mix them up.\n"
                "- When creating education entries, clearly label each one. If you see '2 PU' or 'PUC', that is 12th, NOT 10th.\n"
                "- If a percentage appears near '2 PU', 'PUC', or 'HSC', it belongs to 12th, not 10th.\n"
                "- If a percentage appears near 'SSLC', 'SSC', or '10th', it belongs to 10th, not 12th.\n"
                "- Be very careful to distinguish between these two - they are completely different education levels."
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
            
            # Extract education data for percentages - be more specific to avoid confusion
            education_list = parsed.get("education", [])
            tenth_pct = ""
            twelfth_pct = ""
            degree_cgpa = ""
            
            # First pass: Look for explicit 10th/SSLC/SSC labels
            # Process in order: 10th first, then 12th, to avoid confusion
            for edu in education_list:
                institution_lower = (edu.get("institution", "") or "").lower()
                degree_lower = (edu.get("degree", "") or "").lower()
                field_lower = (edu.get("field", "") or "").lower()
                grade_value = edu.get("grade_value", "") or ""
                
                # Check for 10th - must be explicit, avoid matching "12th" or "2 pu"
                # Only assign if we haven't found it yet and it's clearly 10th
                if not tenth_pct and (any(term in institution_lower or term in degree_lower or term in field_lower 
                       for term in ["10th", "sslc", "ssc", "class 10", "x "]) and 
                    "12th" not in institution_lower and "12th" not in degree_lower and 
                    "2 pu" not in institution_lower and "2pu" not in institution_lower and
                    "puc" not in institution_lower and "hsc" not in institution_lower):
                    tenth_pct = grade_value
                
                # Check for 12th - must be explicit, avoid matching "10th"
                # Only assign if we haven't found it yet and it's clearly 12th
                if not twelfth_pct and (any(term in institution_lower or term in degree_lower or term in field_lower 
                       for term in ["12th", "2 pu", "2pu", "puc", "hsc", "ii pu", "class 12", "xii", "intermediate", 
                                   "pre-university", "pre university", "pre-univ", "(puc)"]) and
                    "10th" not in institution_lower and "10th" not in degree_lower and
                    "sslc" not in institution_lower and "ssc" not in institution_lower):
                    twelfth_pct = grade_value
            
            # Fallback to regex if not found - use improved extraction
            if not tenth_pct or not twelfth_pct:
                fallback = _fallback_minimal_parse(text)
                # Only use fallback if LLM didn't find it
                if not tenth_pct:
                    tenth_pct = fallback.get("tenth_percentage", "")
                if not twelfth_pct:
                    twelfth_pct = fallback.get("twelfth_percentage", "")
            
            # Get degree CGPA - look for highest education (usually last or degree-level)
            # Skip entries that are clearly 10th/12th
            for edu in reversed(education_list):  # Check from end (usually degree is last)
                institution_lower = (edu.get("institution", "") or "").lower()
                degree_lower = (edu.get("degree", "") or "").lower()
                field_lower = (edu.get("field", "") or "").lower()
                grade_value = edu.get("grade_value", "") or ""
                
                # Skip if it's clearly 10th or 12th
                if any(term in institution_lower or term in degree_lower or term in field_lower 
                       for term in ["10th", "12th", "sslc", "ssc", "2 pu", "2pu", "puc", "hsc", "class 10", "class 12"]):
                    continue
                
                # Check if grade_value looks like CGPA (has "/" or is a decimal between 0-10)
                if grade_value:
                    # If it contains "/" it's likely CGPA format
                    if "/" in grade_value:
                        degree_cgpa = grade_value
                        break
                    # If it's a number, check if it's in CGPA range (0-10)
                    try:
                        val = float(grade_value.replace("%", ""))
                        if 0 <= val <= 10:  # Likely CGPA
                            degree_cgpa = grade_value
                            break
                    except:
                        pass
            
            # If still no degree, use first education entry that's not 10th/12th
            if not degree_cgpa and education_list:
                for edu in education_list:
                    institution_lower = (edu.get("institution", "") or "").lower()
                    degree_lower = (edu.get("degree", "") or "").lower()
                    field_lower = (edu.get("field", "") or "").lower()
                    grade_value = edu.get("grade_value", "") or ""
                    
                    if not any(term in institution_lower or term in degree_lower or term in field_lower 
                               for term in ["10th", "12th", "sslc", "ssc", "2 pu", "2pu", "puc", "hsc"]):
                        if grade_value:
                            degree_cgpa = grade_value
                            break
            
            # Use "--" for missing data
            return {
                "name": parsed.get("name", "") or "--",
                "email": parsed.get("email", "") or "--",
                "phone": parsed.get("phone", "") or "--",
                "experience": [
                    f"{exp.get('title', '')} @ {exp.get('company', '')}" 
                    if exp.get('company') else exp.get('title', '')
                    for exp in parsed.get("experience", [])
                ] if parsed.get("experience") else [],
                "tenth_percentage": tenth_pct or "--",
                "twelfth_percentage": twelfth_pct or "--",
                "degree_percentage_or_cgpa": degree_cgpa or "--",
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
                    "name": "--", "email": "--", "phone": "--", "experience": [],
                    "tenth_percentage": "--", "twelfth_percentage": "--", "degree_percentage_or_cgpa": "--"
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

@app.post("/generate_report")
async def generate_report_underscore(payload: dict):
    """Alias for /generate-report with underscore (frontend compatibility)"""
    return await generate_report(payload)

@app.post("/users")
def create_or_get_user(payload: dict):
    """
    Create or get user profile.
    Body: { name, email, phone, tenth_percentage, twelfth_percentage, degree_percentage_or_cgpa, experience }
    Returns: { user_id, persisted }
    """
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    
    tenth = payload.get("tenth_percentage") or ""
    twelfth = payload.get("twelfth_percentage") or ""
    degree = payload.get("degree_percentage_or_cgpa") or ""
    exp = payload.get("experience") or []
    
    db_url = get_db_url()
    if not db_url:
        return {"user_id": "00000000-0000-0000-0000-000000000000", "persisted": False}
    
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        # Ensure tables exist
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("create extension if not exists pgcrypto;")
                except Exception:
                    pass
                cur.execute("""
                    create table if not exists user_profiles (
                      id uuid primary key default gen_random_uuid(),
                      name text not null,
                      email text,
                      phone text,
                      tenth_percentage text,
                      twelfth_percentage text,
                      degree_percentage_or_cgpa text,
                      experience jsonb,
                      aptitude_level text,
                      reasoning_level text,
                      coding_level text,
                      created_at timestamptz not null default now()
                    );
                """)
        
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if email:
                    cur.execute("select id from user_profiles where email=%s limit 1", (email,))
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            """
                            update user_profiles
                            set name=%s, phone=%s, tenth_percentage=%s, twelfth_percentage=%s,
                                degree_percentage_or_cgpa=%s, experience=%s
                            where id=%s
                            """,
                            (name, phone or None, tenth, twelfth, degree, psycopg.types.json.Json(exp), row["id"]),
                        )
                        return {"user_id": str(row["id"]), "persisted": True}
                
                cur.execute(
                    """
                    insert into user_profiles(name,email,phone,tenth_percentage,twelfth_percentage,degree_percentage_or_cgpa,experience)
                    values(%s,%s,%s,%s,%s,%s,%s) returning id
                    """,
                    (name, email or None, phone or None, tenth, twelfth, degree, psycopg.types.json.Json(exp)),
                )
                user_id = cur.fetchone()["id"]
                return {"user_id": str(user_id), "persisted": True}
    except Exception as e:
        return {"user_id": "00000000-0000-0000-0000-000000000000", "persisted": False, "db_error": str(e)}

def parse_percent(s: str) -> Optional[float]:
    """Parse percentage string to float"""
    try:
        if not s:
            return None
        t = s.strip().replace("%", "")
        return float(t)
    except Exception:
        return None

def parse_cgpa(s: str) -> Optional[float]:
    """Parse CGPA string to float"""
    if not s:
        return None
    try:
        main = s.split("/")[0].strip()
        return float(main)
    except Exception:
        return None

def compute_resume_strength(row: Dict[str, Any]) -> str:
    """Compute resume strength based on academic scores and experience"""
    cgpa = parse_cgpa(row.get("degree_percentage_or_cgpa") or "")
    twelfth = parse_percent(row.get("twelfth_percentage") or "")
    tenth = parse_percent(row.get("tenth_percentage") or "")
    exp_list = row.get("experience") or []
    exp_len = len(exp_list) if isinstance(exp_list, list) else 0
    score = 0
    
    if cgpa is not None:
        if cgpa >= 9.0: score += 4
        elif cgpa >= 8.0: score += 3
        elif cgpa >= 7.0: score += 2
        else: score += 1
    if twelfth is not None:
        if twelfth >= 95: score += 4
        elif twelfth >= 90: score += 3
        elif twelfth >= 80: score += 2
        else: score += 1
    if tenth is not None:
        if tenth >= 95: score += 3
        elif tenth >= 85: score += 2
        else: score += 1
    if exp_len >= 3: score += 4
    elif exp_len == 2: score += 3
    elif exp_len == 1: score += 2
    else: score += 1

    if score >= 12:
        return "EXTREMELY_STRONG"
    if score >= 9:
        return "STRONG"
    if score >= 6:
        return "AVERAGE"
    return "WEAK"

def final_level_by_matrix(resume_strength: str, user_level: str) -> str:
    """Determine final question level based on resume strength and user's self-assessed level"""
    u = user_level.lower()
    if resume_strength == "WEAK":
        if u == "beginner": return "beginner"
        if u == "intermediate": return "beginner"
        if u == "advance": return "intermediate"
    elif resume_strength == "AVERAGE":
        if u == "beginner": return "beginner"
        if u == "intermediate": return "intermediate"
        if u == "advance": return "advance"
    elif resume_strength == "STRONG":
        if u == "beginner": return "beginner"
        if u == "intermediate": return "advance"
        if u == "advance": return "advance"
    elif resume_strength == "EXTREMELY_STRONG":
        if u == "beginner": return "beginner"
        if u == "intermediate": return "advance"
        if u == "advance": return "advance"
    return u

def load_questions_bundle(bundle_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load questions from zip file or txt files"""
    result: Dict[str, List[Dict[str, Any]]] = {"aptitude": [], "reasoning": [], "coding": []}
    
    # Try zip file first
    if os.path.isfile(bundle_path):
        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                for name in zf.namelist():
                    lower = name.lower()
                    if not lower.endswith(".json"):
                        continue
                    with zf.open(name) as f:
                        try:
                            data = json.loads(f.read().decode("utf-8"))
                            if "aptitude" in lower:
                                result["aptitude"].extend(data)
                            elif "reason" in lower:
                                result["reasoning"].extend(data)
                            elif "coding" in lower or "general" in lower or "dsa" in lower or "oops" in lower or "os" in lower:
                                result["coding"].extend(data)
                        except Exception:
                            continue
            if any(result.values()):
                return result
        except Exception:
            pass
    
    # Fallback: parse txt files
    def parse_txt(path: str) -> List[Dict[str, Any]]:
        if not os.path.isfile(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = [ln.rstrip() for ln in content.splitlines()]
        out: List[Dict[str, Any]] = []
        cur: List[str] = []
        cur_level = "beginner"
        
        def flush(seg: List[str], level: str):
            txt = "\n".join(seg).strip()
            if not txt:
                return
            m_ans = re.search(r"Answer:\s*([A-Da-d])", txt)
            if not m_ans:
                return
            ans_key = m_ans.group(1).upper()
            head = re.split(r"Answer:\s*[A-Da-d]", txt)[0].strip()
            head = re.sub(r"^(Q?\d+\.\s*)", "", head)
            m_opts = re.search(r"A\)\s*(.*?)\s+B\)\s*(.*?)\s+C\)\s*(.*?)\s+D\)\s*(.*)", head, flags=re.S)
            question = head
            options: List[str] = []
            if m_opts:
                question = head[:m_opts.start()].strip().rstrip(":").strip()
                options = [m_opts.group(i).strip() for i in range(1,5)]
            else:
                question_line, *rest = head.splitlines()
                question = question_line.strip().rstrip(":").strip()
                for opt_key in ["A", "B", "C", "D"]:
                    mm = re.search(rf"^{opt_key}[\).\]]\s*(.*)$", head, flags=re.M)
                    if mm:
                        options.append(mm.group(1).strip())
            correct = ""
            if options:
                idx = {"A":0,"B":1,"C":2,"D":3}.get(ans_key, None)
                if idx is not None and 0 <= idx < len(options):
                    correct = options[idx]
            out.append({
                "question": question,
                "options": options,
                "correct_answer": correct,
                "explanation": "",
                "level": level,
            })
        
        for ln in lines:
            if not ln.strip():
                continue
            low = ln.lower()
            if "beginner" in low:
                cur_level = "beginner"
                continue
            if "intermediate" in low:
                cur_level = "intermediate"
                continue
            if "advanced" in low:
                cur_level = "advance"
                continue
            cur.append(ln)
            if ln.strip().startswith("Answer:"):
                flush(cur, cur_level)
                cur = []
        if cur:
            flush(cur, cur_level)
        
        # Fallback parser if nothing found
        if not out:
            blocks = re.split(r"(?=^(?:Q?\d+\.))", content, flags=re.M)
            for blk in blocks:
                blk = blk.strip()
                if not blk:
                    continue
                m_q = re.match(r"^(?:Q?\d+\.\s*)?(.*)", blk, flags=re.M)
                if not m_q:
                    continue
                question = m_q.group(1).strip()
                opts = []
                for opt_key in ["A", "B", "C", "D"]:
                    m_opt = re.search(rf"^{opt_key}[\).\]]\s*(.*)$", blk, flags=re.M)
                    if m_opt:
                        opts.append(m_opt.group(1).strip())
                m_ca = re.search(r"Answer:\s*([A-D])", blk, flags=re.M)
                correct = ""
                if m_ca:
                    key = m_ca.group(1).upper()
                    idx = {"A":0,"B":1,"C":2,"D":3}.get(key, None)
                    if idx is not None and idx < len(opts):
                        correct = opts[idx]
                out.append({
                    "question": question,
                    "options": opts,
                    "correct_answer": correct,
                    "explanation": "",
                })
            for i, q in enumerate(out, start=1):
                q["level"] = "beginner" if i <= 40 else ("intermediate" if i <= 70 else "advance")
        return out
    
    # Load from project root or questions_bundle directory
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "questions_bundle"))
    
    result["aptitude"] = parse_txt(os.path.join(root, "aptitude.txt")) or parse_txt(os.path.join(base_dir, "aptitude.txt"))
    result["reasoning"] = parse_txt(os.path.join(root, "reasoning.txt")) or parse_txt(os.path.join(base_dir, "reasoning.txt"))
    result["coding"] = parse_txt(os.path.join(root, "coding.txt")) or parse_txt(os.path.join(base_dir, "coding.txt")) or parse_txt(os.path.join(base_dir, "general.txt"))
    
    if not any(result.values()):
        raise RuntimeError("No questions found in zip or txt banks")
    return result

def pick_by_level(items: List[Dict[str, Any]], level: str, count: int) -> List[Dict[str, Any]]:
    """Pick questions of a specific level"""
    pool = [q for q in items if str(q.get("level", "")).lower() == level.lower()]
    if len(pool) < count:
        chosen = pool[:]
        remaining = [q for q in items if q not in chosen]
        random.shuffle(remaining)
        chosen.extend(remaining[: max(0, count - len(chosen))])
        return chosen[:count]
    random.shuffle(pool)
    return pool[:count]

@app.post("/select_questions")
def select_questions(payload: dict):
    """
    Select questions based on user level and resume strength.
    Body: { user_id?, aptitude_level, reasoning_level, coding_level, counts?: { aptitude?, reasoning?, coding? } }
    """
    user_id = payload.get("user_id")
    levels = {
        "aptitude": payload.get("aptitude_level", "beginner"),
        "reasoning": payload.get("reasoning_level", "beginner"),
        "coding": payload.get("coding_level", "beginner"),
    }
    counts = payload.get("counts") or {}
    num_apt = int(counts.get("aptitude", 10))
    num_rea = int(counts.get("reasoning", 10))
    num_cod = int(counts.get("coding", 10))

    # Fetch resume data
    resume_row: Dict[str, Any] = {}
    direct_resume = payload.get("resume")
    db_url = get_db_url()
    
    if user_id and db_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("select * from user_profiles where id=%s limit 1", (user_id,))
                    row = cur.fetchone()
                    if row:
                        resume_row = row
                    elif isinstance(direct_resume, dict):
                        # If user not found but resume data provided, use it
                        resume_row = direct_resume
                    else:
                        # If no user and no resume, create minimal resume from available data
                        resume_row = {
                            "tenth_percentage": payload.get("tenth_percentage", ""),
                            "twelfth_percentage": payload.get("twelfth_percentage", ""),
                            "degree_percentage_or_cgpa": payload.get("degree_percentage_or_cgpa", ""),
                            "experience": payload.get("experience", []),
                        }
        except HTTPException:
            raise
        except Exception as e:
            # If DB fails, fall back to resume data or minimal data
            if isinstance(direct_resume, dict):
                resume_row = direct_resume
            else:
                resume_row = {
                    "tenth_percentage": payload.get("tenth_percentage", ""),
                    "twelfth_percentage": payload.get("twelfth_percentage", ""),
                    "degree_percentage_or_cgpa": payload.get("degree_percentage_or_cgpa", ""),
                    "experience": payload.get("experience", []),
                }
    elif isinstance(direct_resume, dict):
        resume_row = direct_resume
    else:
        # No user_id, no resume, no DB - use minimal data from payload
        resume_row = {
            "tenth_percentage": payload.get("tenth_percentage", ""),
            "twelfth_percentage": payload.get("twelfth_percentage", ""),
            "degree_percentage_or_cgpa": payload.get("degree_percentage_or_cgpa", ""),
            "experience": payload.get("experience", []),
        }

    # Compute resume strength and adjust levels
    strength = compute_resume_strength(resume_row)
    final_levels = {
        "aptitude": final_level_by_matrix(strength, levels["aptitude"]),
        "reasoning": final_level_by_matrix(strength, levels["reasoning"]),
        "coding": final_level_by_matrix(strength, levels["coding"]),
    }

    # Load questions
    bundle_path = os.path.join(os.path.dirname(__file__), "..", "questions_bundle.zip")
    bundle_path = os.path.abspath(bundle_path)
    try:
        bank = load_questions_bundle(bundle_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load questions: {str(e)}")

    return {
        "aptitude": {
            "final_level": final_levels["aptitude"],
            "questions": pick_by_level(bank["aptitude"], final_levels["aptitude"], num_apt),
        },
        "reasoning": {
            "final_level": final_levels["reasoning"],
            "questions": pick_by_level(bank["reasoning"], final_levels["reasoning"], num_rea),
        },
        "coding": {
            "final_level": final_levels["coding"],
            "questions": pick_by_level(bank["coding"], final_levels["coding"], num_cod),
        },
    }

@app.post("/responses")
def save_responses(payload: dict):
    """
    Save test responses.
    Body: { user_id, aptitude_level, reasoning_level, coding_level }
    """
    user_id = payload.get("user_id")
    aptitude = payload.get("aptitude_level")
    reasoning = payload.get("reasoning_level")
    coding = payload.get("coding_level")
    
    if not (user_id and aptitude and reasoning and coding):
        raise HTTPException(status_code=400, detail="missing fields")
    
    db_url = get_db_url()
    if not db_url:
        return {"saved": False}
    
    try:
        import psycopg
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update user_profiles
                    set aptitude_level=%s, reasoning_level=%s, coding_level=%s
                    where id=%s
                    """,
                    (aptitude, reasoning, coding, user_id),
                )
        return {"saved": True}
    except Exception as e:
        return {"saved": False, "error": str(e)}

@app.get("/{path:path}")
def catch_all(path: str):
    """Catch-all route for undefined endpoints"""
    return {
        "error": "Endpoint not found",
        "path": path,
        "available_endpoints": [
            "GET /",
            "GET /health",
            "POST /parse",
            "POST /upload-resume",
            "POST /users",
            "POST /select_questions",
            "POST /responses",
            "POST /evaluate",
            "POST /generate-report",
            "POST /generate_report"
        ]
    }, 404
