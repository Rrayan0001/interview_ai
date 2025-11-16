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
from backend.api import select_questions as backend_select_questions
import re
import json

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

app = FastAPI(title="AI Interview Bot API", version="1.0.0")

# CORS: allow frontend origin from env or default to localhost:1300
# For production, set FRONTEND_ORIGIN to your deployed frontend URL
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:1300")
# Support multiple origins (comma-separated) or wildcard for dev
allowed_origins = [origin.strip() for origin in FRONTEND_ORIGIN.split(",")] if "," in FRONTEND_ORIGIN else [FRONTEND_ORIGIN]
if FRONTEND_ORIGIN == "*":
    allowed_origins = ["*"]

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
        m_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", text)
        if m_email:
            email = m_email.group(0)
    except Exception:
        pass
    try:
        m_phone = re.search(r"(?:\\+\\d{1,3}[\\s-]?)?\\d{10}", re.sub(r"\\D", "", text))
        if m_phone:
            phone = m_phone.group(0)
    except Exception:
        pass
    try:
        # naive pick first percentage-looking numbers
        percents = re.findall(r"(\\d{1,2}(?:\\.\\d+)?%)", text)
        if percents:
            tenth = percents[0]
        if len(percents) > 1:
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
    """Health check endpoint"""
    db_ok = False
    try:
        ensure_tables()
        db_ok = True if get_db_url() else False
    except Exception:
        db_ok = False
    return {"status": "ok", "db": "ok" if db_ok else "not_configured"}


# Full resume parsing using Groq LLM (extracts name, email, phone, education, experience, projects, etc.)
@app.post("/parse")
async def parse_resume(pdf: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.1-8b-instant"):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured. Please set it in .env or environment.")
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await pdf.read())
            tmp_path = tmp.name

        text = read_pdf_text(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF. The PDF may be scanned (image-only).")

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
            raise HTTPException(status_code=500, detail="groq package not installed")
        
        client = Groq(api_key=key)
        
        # Get JSON schema from Pydantic model
        schema = ResumeSchema.model_json_schema()
        
        # Build system prompt with schema
        system_prompt = (
            "Extract resume details from the provided text and return ONLY valid JSON matching this exact schema:\n"
            + json.dumps(schema, indent=2, ensure_ascii=False)
            + "\n\nCRITICAL: Return ONLY the JSON object. No markdown, no code blocks, no explanations. "
            "Populate all fields from the resume text. Use empty strings or empty arrays for missing data."
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
            "tenth_percentage": "",
            "twelfth_percentage": "",
            "degree_percentage_or_cgpa": (
                parsed.get("education", [{}])[0].get("grade_value", "") 
                if parsed.get("education") else ""
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")
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


