import os
import tempfile
from typing import Optional, List, Dict, Any, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf_to_text_groq import read_pdf_text, clean_with_groq_llm, parse_resume_with_groq
import psycopg
from psycopg.rows import dict_row
import zipfile
import json as pyjson
import random
import re
from pydantic import BaseModel
from typing import TypedDict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(
    title="AI Interview Bot API",
    root_path="/api" if os.environ.get("VERCEL") else ""
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "AI Interview Bot API is running", "docs": "/docs"}

def get_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Missing GROQ_API_KEY")
    return key.strip()

def get_db_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    return url.strip() if url else None

def ensure_tables() -> None:
    db_url = get_db_url()
    if not db_url:
        return
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("create extension if not exists pgcrypto;")
            except Exception:
                pass
            # Clean up legacy tables if present
            try:
                cur.execute("drop table if exists quiz_responses cascade;")
            except Exception:
                pass
            try:
                cur.execute("drop table if exists users cascade;")
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
async def parse_resume(pdf: UploadFile = File(...), cleanup: bool = False, model: str = "llama-3.3-70b-versatile"):
    key = get_groq_key()
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

        if cleanup:
            try:
                text = clean_with_groq_llm(text, model=model, api_key=key, verbose=False)
            except Exception:
                pass

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@app.post("/users")
def create_or_get_user(payload: dict):
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
        raise HTTPException(status_code=500, detail=str(e))

def parse_percent(s: str) -> Optional[float]:
    try:
        if not s:
            return None
        t = s.strip().replace("%", "")
        return float(t)
    except Exception:
        return None

def parse_cgpa(s: str) -> Optional[float]:
    if not s:
        return None
    try:
        # examples: "8.40 / 10.0", "8.4/10"
        main = s.split("/")[0].strip()
        return float(main)
    except Exception:
        return None

def compute_resume_strength(row: Dict[str, Any]) -> str:
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
    """
    Flexible loader:
    1) If questions_bundle.zip with JSON files is present, use it.
    2) Otherwise, parse plain-text banks at questions_bundle/{aptitude.txt, reasoning.txt, general.txt}.
       Assign difficulty by position: 1-40 beginner, 41-70 intermediate, 71-100 advance.
    """
    result: Dict[str, List[Dict[str, Any]]]= {"aptitude": [], "reasoning": [], "coding": []}
    if os.path.isfile(bundle_path):
        with zipfile.ZipFile(bundle_path, "r") as zf:
            for name in zf.namelist():
                lower = name.lower()
                if not lower.endswith(".json"):
                    continue
                with zf.open(name) as f:
                    try:
                        data = pyjson.loads(f.read().decode("utf-8"))
                        if "aptitude" in lower:
                            result["aptitude"].extend(data)
                        elif "reason" in lower:
                            result["reasoning"].extend(data)
                        elif "coding" in lower or "general" in lower or "dsa" in lower or "oops" in lower or "os" in lower:
                            result["coding"].extend(data)
                    except Exception:
                        continue
        # If zip provided something, return now
        if any(result.values()):
            return result
    # Fallback: parse txt banks
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "questions_bundle"))
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
            # Find 'Answer:' line
            m_ans = re.search(r"Answer:\s*([A-Da-d])", txt)
            if not m_ans:
                return
            ans_key = m_ans.group(1).upper()
            # Extract everything before Answer:
            head = re.split(r"Answer:\s*[A-Da-d]", txt)[0].strip()
            # If numbered prefix like "Q12. ..." or "12. ..." remove it
            head = re.sub(r"^(Q?\d+\.\s*)", "", head)
            # Split options even if they are on the same line
            # Look for 'A) ... B) ... C) ... D) ...'
            m_opts = re.search(r"A\)\s*(.*?)\s+B\)\s*(.*?)\s+C\)\s*(.*?)\s+D\)\s*(.*)", head, flags=re.S)
            question = head
            options: List[str] = []
            if m_opts:
                question = head[:m_opts.start()].strip().rstrip(":").strip()
                options = [m_opts.group(i).strip() for i in range(1,5)]
            else:
                # Try multi-line options style 'A. ...' on separate lines
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
        # If still anything buffered, try to flush
        if cur:
            flush(cur, cur_level)
        # Fallback: if none parsed, try the previous Q-based parser
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
            # Assign levels by index
            for i, q in enumerate(out, start=1):
                q["level"] = "beginner" if i <= 40 else ("intermediate" if i <= 70 else "advance")
        return out
    # Prefer project-root files if present
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result["aptitude"] = parse_txt(os.path.join(root, "aptitude.txt")) or parse_txt(os.path.join(base_dir, "aptitude.txt"))
    result["reasoning"] = parse_txt(os.path.join(root, "reasoning.txt")) or parse_txt(os.path.join(base_dir, "reasoning.txt"))
    # coding: prefer coding.txt, else general.txt
    result["coding"] = parse_txt(os.path.join(root, "coding.txt")) or parse_txt(os.path.join(base_dir, "coding.txt")) or parse_txt(os.path.join(base_dir, "general.txt"))
    if not any(result.values()):
        raise RuntimeError("No questions found in zip or txt banks")
    return result

def pick_by_level(items: List[Dict[str, Any]], level: str, count: int) -> List[Dict[str, Any]]:
    pool = [q for q in items if str(q.get("level", "")).lower() == level.lower()]
    if len(pool) < count:
        # if insufficient, take all and fill with random remaining without repeats
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
    Body:
    {
      user_id?: string,
      aptitude_level: "beginner"|"intermediate"|"advance",
      reasoning_level: "...",
      coding_level: "...",
      counts?: { aptitude?: int, reasoning?: int, coding?: int }
    }
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

    # Fetch row if user_id provided, else allow direct resume data
    resume_row: Dict[str, Any] = {}
    direct_resume = payload.get("resume")  # optional direct fields
    db_url = get_db_url()
    if user_id and db_url:
        try:
            with psycopg.connect(db_url, autocommit=True) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("select * from user_profiles where id=%s limit 1", (user_id,))
                    row = cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail="user not found")
                    resume_row = row
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif isinstance(direct_resume, dict):
        resume_row = direct_resume
    else:
        raise HTTPException(status_code=400, detail="Provide user_id or resume data")

    strength = compute_resume_strength(resume_row)
    final_levels = {
        "aptitude": final_level_by_matrix(strength, levels["aptitude"]),
        "reasoning": final_level_by_matrix(strength, levels["reasoning"]),
        "coding": final_level_by_matrix(strength, levels["coding"]),
    }

    bundle_path = os.path.join(os.path.dirname(__file__), "..", "questions_bundle.zip")
    bundle_path = os.path.abspath(bundle_path)
    try:
        bank = load_questions_bundle(bundle_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    out = {
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
    return out
@app.post("/responses")
def save_responses(payload: dict):
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
    answers: list[ReportAnswer]
    totals: ReportTotals
    behavior: ReportBehavior
    profile: dict | None = None
    model: str | None = "llama-3.3-70b-versatile"

@app.post("/generate_report")
def generate_report(payload: ReportPayload):
    """
    Generates a fresh Career & Skill Development Report using Groq for each attempt.
    Input shape mirrors the client-computed results to avoid re-computation server-side.
    Returns markdown.
    """
    api_key = get_groq_key()
    try:
        from groq import Groq
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"groq client missing: {e}")

    client = Groq(api_key=api_key)

    # Build a concise but information-rich prompt to avoid hallucination.
    system_prompt = (
        "You are a precise assessment analyst. Create a Career & Skill Development Report based solely on the provided data.\n"
        "Rules:\n"
        "- Use the user's results and academic profile only; do not invent data.\n"
        "- Professional tone, clear headings, bullet points where helpful.\n"
        "- Sections: Performance Analysis; Skill Gap Analysis; Personalized 6-Week Improvement Plan; Career Guidance; Internship Recommendations; Final Summary.\n"
        "- Keep recommendations realistic for current level. Do not include code fences.\n"
        "- CRITICAL RULE: If the user's score is low (below 30%), be brutally honest. Do not use positive words like 'Developing' or 'Potential'. Clearly state that they failed the assessment and have significant gaps. Do not sugarcoat poor performance.\n"
    )
    user_content = {
        "test_results": {
            "answers": payload.answers,
            "totals": payload.totals,
            "behavior": payload.behavior,
        },
        "academic_profile": payload.profile or {},
        "format_instructions": {
            "headings": True,
            "no_code": True,
            "language": "English",
        },
    }

    # Send to Groq
    import json as _json
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _json.dumps(user_content, ensure_ascii=False)},
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

@app.post("/api/generate_report")
@app.post("/generate_report/")
@app.post("/api/generate_report/")
def generate_report_alias(payload: ReportPayload):
    return generate_report(payload)


