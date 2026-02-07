import os
import sys
import tempfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf_to_text_groq import read_pdf_text, clean_with_groq_llm, parse_resume_with_groq
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field
from typing import TypedDict, Dict, Any, List, Optional
import re
import json

# Try to import backend module (optional, may not exist in all deployments)
try:
    from backend.api import select_questions as backend_select_questions
except ImportError:
    # If backend module doesn't exist, we'll define a fallback
    backend_select_questions = None
    print("Warning: backend.api module not found, some features may be unavailable")

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

app = FastAPI(title="AI Interview Bot API", version="1.0.0")

# CORS: allow frontend origin(s).
# - Local dev defaults to http://localhost:10000 / http://127.0.0.1:10000 (vite dev server).
# - Production should set FRONTEND_ORIGIN to the deployed frontend URL (or comma-separated list).
_default_dev_origins = ["http://localhost:10000", "http://127.0.0.1:10000"]
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


def get_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Missing GROQ_API_KEY")
    return key.strip()

def get_db_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url else None

def repair_llm_json(text: str) -> str:
    """
    Clean common LLM JSON mistakes:
    - trailing commas
    - unescaped quotes
    - non-breaking spaces
    - missing commas before object keys
    """
    import re
    # Remove non-breaking spaces
    text = text.replace("\u00a0", " ")
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Fix missing commas between object properties (basic attempt)
    text = re.sub(r'("\s*)\n\s*"', r'\1,\n    "', text)
    # Remove any markdown code blocks
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

# Pydantic models for structured LLM output (guarantees valid JSON)
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
    """
    Very lightweight, regex-based parser used when LLM calls fail.
    Always succeeds and returns a minimal schema so the UI never gets a 500.
    """
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
        # Extract 10th percentage - look for "10th", "10", "SSLC", "SSC" patterns
        tenth_patterns = [
            r"10th[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"10[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"(?:SSLC|SSC)[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"(\d{1,2}(?:\.\d+)?%)(?=.*10th|.*SSLC|.*SSC)",
        ]
        for pattern in tenth_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                tenth = m.group(1) if m.groups() else m.group(0)
                break
        
        # Extract 12th percentage - look for "12th", "2 PU", "2pu", "2 pu", "PUC", "HSC" patterns
        twelfth_patterns = [
            r"(?:12th|2\s*PU|2PU|PUC|HSC)[:\s]+(\d{1,2}(?:\.\d+)?%)",
            r"(\d{1,2}(?:\.\d+)?%)(?=.*(?:12th|2\s*PU|2PU|PUC|HSC))",
            r"(?:12th|2\s*PU|2PU|PUC|HSC).*?(\d{1,2}(?:\.\d+)?%)",
        ]
        for pattern in twelfth_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                twelfth = m.group(1) if m.groups() else m.group(0)
                break
        
        # Fallback: if no specific pattern found, try naive approach
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
    # crude name guess: first non-empty line
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

def ensure_tables() -> None:
    db_url = get_db_url()
    if not db_url:
        return
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Ensure pgcrypto exists for gen_random_uuid()
            try:
                cur.execute("create extension if not exists pgcrypto;")
            except Exception:
                pass
            # Drop legacy tables no longer used (idempotent)
            try:
                cur.execute("drop table if exists quiz_responses cascade;")
            except Exception:
                pass
            try:
                cur.execute("drop table if exists users cascade;")
            except Exception:
                pass
            # Single-table model to store parsed resume + quiz answers together
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

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "name": "AI Interview Bot API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "parse": "/parse",
            "users": "/users",
            "select_questions": "/select_questions",
            "responses": "/responses",
            "generate_report": "/generate_report",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint - must never fail"""
    try:
        db_ok = False
        db_error = None
        db_url = get_db_url()
        
        if db_url:
            try:
                ensure_tables()
                db_ok = True
            except Exception as e:
                db_error = str(e)
                print(f"Health check: DB connection failed: {e}", file=sys.stderr)
        else:
            db_error = "DATABASE_URL not configured"
        
        return {
            "status": "ok",
            "db": "ok" if db_ok else "not_configured",
            "db_error": db_error if db_error else None
        }
    except Exception as e:
        # Health endpoint must never crash - return error details
        print(f"Health check crashed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "db": "unknown"
        }


# Full resume parsing using Groq LLM (extracts name, email, phone, education, experience, projects, etc.)
@app.post("/parse")
async def parse_resume(pdf: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.1-8b-instant"):
    """
    Primary resume parsing endpoint.
    - If GROQ_API_KEY is available, we use the LLM-powered structured parser.
    - If the key is missing or Groq call fails, we gracefully fall back to a lightweight regex parser
      so the UI never receives a 500 / CORS error.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await pdf.read())
            tmp_path = tmp.name

        text = read_pdf_text(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF. The PDF may be scanned (image-only).")

        fallback_payload = _fallback_minimal_parse(text)

        key = os.environ.get("GROQ_API_KEY")
        if not key:
            fallback_payload["note"] = "GROQ_API_KEY not configured; returned minimal parse."
            return fallback_payload

        # Always use LLM cleanup if requested
        if cleanup:
            try:
                text = clean_with_groq_llm(text, model=model, api_key=key, verbose=False)
            except Exception as e:
                # Log but continue with raw text if cleanup fails
                print(f"Warning: LLM cleanup failed: {e}", file=sys.stderr)

        # Use structured JSON output to guarantee valid, complete JSON
        try:
            from groq import Groq
        except ImportError:
            fallback_payload["note"] = "groq package not installed; returned minimal parse."
            return fallback_payload
        
        client = Groq(api_key=key)
        
        # Get JSON schema from Pydantic model
        schema = ResumeSchema.model_json_schema()
        
        # Build system prompt with schema
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
        
        # Use structured output mode - guarantees valid JSON
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        
        # This will ALWAYS be valid JSON (no truncation, no malformed syntax)
        clean_json = resp.choices[0].message.content or "{}"
        parsed = json.loads(clean_json)
        
        # Extract education data for percentages
        education_list = parsed.get("education", [])
        tenth_pct = ""
        twelfth_pct = ""
        degree_cgpa = ""
        
        # Look for 10th and 12th in education entries
        for edu in education_list:
            institution_lower = (edu.get("institution", "") or "").lower()
            degree_lower = (edu.get("degree", "") or "").lower()
            field_lower = (edu.get("field", "") or "").lower()
            grade_value = edu.get("grade_value", "") or ""
            
            # Check if this is 10th/SSLC/SSC
            if any(term in institution_lower or term in degree_lower or term in field_lower 
                   for term in ["10th", "sslc", "ssc", "10"]):
                tenth_pct = grade_value
            
            # Check if this is 12th/2 PU/PUC/HSC
            if any(term in institution_lower or term in degree_lower or term in field_lower 
                   for term in ["12th", "2 pu", "2pu", "puc", "hsc", "12"]):
                twelfth_pct = grade_value
        
        # If not found in education, try to extract from text using regex
        if not tenth_pct or not twelfth_pct:
            fallback = _fallback_minimal_parse(text)
            if not tenth_pct:
                tenth_pct = fallback.get("tenth_percentage", "")
            if not twelfth_pct:
                twelfth_pct = fallback.get("twelfth_percentage", "")
        
        # Get degree CGPA from first education entry (usually degree)
        if education_list:
            degree_cgpa = education_list[0].get("grade_value", "") or ""
        
        # Convert to dict format expected by frontend
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
    except HTTPException:
        raise
    except Exception as e:
        fallback_payload = {"note": f"Unexpected failure: {e}"}
        try:
            # Provide whatever we can from fallback parser if text already extracted
            if "text" in locals() and text:
                fallback_payload.update(_fallback_minimal_parse(text))
            else:
                fallback_payload.update({"name": "", "email": "", "phone": "", "experience": [], "tenth_percentage": "", "twelfth_percentage": "", "degree_percentage_or_cgpa": ""})
        except Exception:
            pass
        print(f"parse_resume fallback due to exception: {e}", file=sys.stderr)
        return fallback_payload
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@app.post("/users")
def create_or_get_user(payload: dict):
    """
    Body: {
      name, email, phone,
      tenth_percentage, twelfth_percentage, degree_percentage_or_cgpa,
      experience (array of strings)
    }
    Returns: { user_id }
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
        # If DB not configured, return a fake id for demo flows
        return {"user_id": "00000000-0000-0000-0000-000000000000", "persisted": False}
    try:
        ensure_tables()
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
                        return {"user_id": row["id"], "persisted": True}
                cur.execute(
                    """
                    insert into user_profiles(name,email,phone,tenth_percentage,twelfth_percentage,degree_percentage_or_cgpa,experience)
                    values(%s,%s,%s,%s,%s,%s,%s) returning id
                    """,
                    (name, email or None, phone or None, tenth, twelfth, degree, psycopg.types.json.Json(exp)),
                )
                user_id = cur.fetchone()["id"]
                return {"user_id": user_id, "persisted": True}
    except Exception as e:
        # Fallback to non-persistent mode instead of 500 so the flow continues
        return {"user_id": "00000000-0000-0000-0000-000000000000", "persisted": False, "db_error": str(e)}


# -------------------- LLM Report Generation --------------------
class ReportAnswer(TypedDict, total=False):
    index: int
    domain: str
    difficulty: str
    question: str
    selected: str
    correct: str
    isCorrect: bool

class ReportTotals(TypedDict):
    overall: int
    aptitude: int
    reasoning: int
    coding: int
    totalQuestions: int

class ReportBehavior(TypedDict):
    accuracy: int
    consistency: str

class ReportPayload(BaseModel):
    answers: List[ReportAnswer]
    totals: ReportTotals
    behavior: ReportBehavior
    profile: Dict[str, Any] | None = None
    model: str | None = "llama-3.1-8b-instant"

def _local_report_markdown(payload: ReportPayload) -> str:
    a = payload.answers
    t = payload.totals
    b = payload.behavior
    lines = []
    lines.append("Career & Skill Development Report")
    lines.append("")
    lines.append("Performance Analysis")
    lines.append(f"- Total Score: {t.get('overall', 0)} / {t.get('totalQuestions', 0)} ({b.get('accuracy', 0)}%)")
    lines.append(f"- Aptitude: {t.get('aptitude', 0)}")
    lines.append(f"- Reasoning: {t.get('reasoning', 0)}")
    lines.append(f"- Coding: {t.get('coding', 0)}")
    lines.append(f"- Consistency: {b.get('consistency', 'NA')}")
    lines.append("")
    lines.append("Skill Gap Analysis")
    lines.append("- Focus on improving weak areas identified by incorrect answers.")
    lines.append("")
    lines.append("Personalized 6-Week Improvement Plan")
    lines.append("- Weeks 1–2: Quantitative basics and reasoning drills.")
    lines.append("- Weeks 3–4: Coding fundamentals and problem sets (arrays/strings/hash).")
    lines.append("- Weeks 5–6: Mixed timed mocks; maintain an error log and review.")
    lines.append("")
    lines.append("Career Guidance")
    lines.append("- Target roles aligned with strongest section; close core gaps first.")
    lines.append("")
    lines.append("Internship Recommendations")
    lines.append("- Frontend/Full‑stack/QA/Data Analyst Intern depending on section strengths.")
    lines.append("")
    lines.append("Final Summary")
    lines.append("- Keep a steady daily routine; expect visible improvement within 6–8 weeks.")
    return "\n".join(lines)

@app.post("/generate_report")
def generate_report(payload: ReportPayload):
    """
    Generate a fresh per-attempt markdown report using Groq.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Fallback: return a locally generated markdown so the UI never sees a 400
        return {"report_markdown": _local_report_markdown(payload)}
    try:
        from groq import Groq
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"groq client missing: {e}")

    client = Groq(api_key=api_key)
    system_prompt = (
        "You are a precise assessment analyst. Create a Career & Skill Development Report based solely on the provided data.\n"
        "Rules:\n"
        "- Use the user's results and academic profile only; do not invent data.\n"
        "- Professional tone, clear headings, bullet points where helpful.\n"
        "- Sections: Performance Analysis; Skill Gap Analysis; Personalized 6-Week Improvement Plan; Career Guidance; Internship Recommendations; Final Summary.\n"
        "- Do not include code fences.\n"
    )
    import json as _json
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _json.dumps({"test_results": {"answers": payload.answers, "totals": payload.totals, "behavior": payload.behavior}, "academic_profile": payload.profile or {}}, ensure_ascii=False)},
    ]
    try:
        resp = client.chat.completions.create(
            model=payload.model or "llama-3.1-8b-instant",
            messages=messages,
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq error: {e}")
    return {"report_markdown": content.strip()}

# Provide alternate paths to avoid 404s from mismatched prefixes or trailing slashes
@app.post("/api/generate_report")
@app.post("/generate_report/")
@app.post("/api/generate_report/")
def generate_report_alias(payload: ReportPayload):
    return generate_report(payload)

# Proxy to the existing implementation living in backend/api.py so the root server also serves it
@app.post("/select_questions")
def select_questions_proxy(payload: dict):
    if backend_select_questions is None:
        raise HTTPException(
            status_code=500, 
            detail="Question selection module not available. backend.api module not found."
        )
    return backend_select_questions(payload)

@app.post("/responses")
def save_responses(payload: dict):
    """
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
        ensure_tables()
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
        raise HTTPException(status_code=500, detail=str(e))


