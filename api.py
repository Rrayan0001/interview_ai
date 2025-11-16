import os
import tempfile
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf_to_text_groq import read_pdf_text, clean_with_groq_llm, parse_resume_with_groq
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel
from typing import TypedDict, Dict, Any, List
from backend.api import select_questions as backend_select_questions
import re

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

app = FastAPI()
# CORS: allow frontend origin from env or default to localhost:1300
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:1300")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
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

@app.get("/health")
def health():
    db_ok = False
    try:
        ensure_tables()
        db_ok = True if get_db_url() else False
    except Exception:
        db_ok = False
    return {"status": "ok", "db": "ok" if db_ok else "not_configured"}


@app.post("/parse")
async def parse_resume(pdf: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.1-8b-instant"):
    # Try to load key; keep None if missing so we can gracefully fallback
    key = os.environ.get("GROQ_API_KEY")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await pdf.read())
            tmp_path = tmp.name

        text = read_pdf_text(tmp_path)
        if not text:
            return {
                "name": "",
                "email": "",
                "phone": "",
                "experience": [],
                "tenth_percentage": "",
                "twelfth_percentage": "",
                "degree_percentage_or_cgpa": ""
            }

        # Try LLM cleanup if requested and key is present
        if cleanup and key:
            try:
                text = clean_with_groq_llm(text, model=model, api_key=key, verbose=False)
            except Exception:
                # Keep raw text if cleanup fails
                pass

        # Try LLM minimal parse if key available, else fallback
        try:
            if key:
                minimal_json = parse_resume_with_groq(
                    text=text,
                    model=model,
                    api_key=key,
                    verbose=False,
                    output_format="json",
                    output_preset="minimal",
                )
                import json
                return json.loads(minimal_json)
            # No key: fallback parser to avoid 500s/CORS issues
            return _fallback_minimal_parse(text)
        except Exception:
            # Absolute last resort: fallback parser
            return _fallback_minimal_parse(text)
    except Exception as e:
        # Never leak a 500 here; return a safe empty profile so UI proceeds
        return {
            "name": "",
            "email": "",
            "phone": "",
            "experience": [],
            "tenth_percentage": "",
            "twelfth_percentage": "",
            "degree_percentage_or_cgpa": ""
        }
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


