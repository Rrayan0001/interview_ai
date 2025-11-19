# AI Interview Bot - Complete System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture](#architecture)
4. [Complete User Workflow](#complete-user-workflow)
5. [Backend API Endpoints](#backend-api-endpoints)
6. [Frontend Routes & Components](#frontend-routes--components)
7. [Data Models & Database Schema](#data-models--database-schema)
8. [AI/LLM Integration](#aillm-integration)
9. [Question Selection Algorithm](#question-selection-algorithm)
10. [Report Generation System](#report-generation-system)
11. [Deployment Architecture](#deployment-architecture)
12. [Environment Variables](#environment-variables)

---

## System Overview

**AI Interview Bot** is a full-stack web application designed to:
- Parse resumes/CVs from PDF files using AI
- Assess user skill levels through personalized MCQ tests
- Generate comprehensive career development reports using LLM

### Key Features
- **Intelligent Resume Parsing**: Extracts structured data from PDF resumes using Groq LLM
- **Adaptive Question Selection**: Selects questions based on resume strength and user-selected skill levels
- **Timed Assessment**: 30-minute test with 30 questions (10 each: Aptitude, Reasoning, Coding)
- **AI-Powered Reports**: Generates personalized career & skill development reports for each test attempt
- **Database Persistence**: Stores user profiles and assessment data in PostgreSQL (Neon)

---

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router DOM v6
- **Styling**: Custom CSS with modern white theme
- **State Management**: React Hooks (useState, useEffect, useMemo)

### Backend
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn (ASGI)
- **Database**: PostgreSQL (Neon) with psycopg
- **AI/LLM**: Groq API (llama-3.1-8b-instant model)
- **PDF Processing**: pypdf library
- **Deployment**: Vercel Serverless Functions (Mangum adapter)

### External Services
- **Groq API**: For LLM-powered text cleanup, resume parsing, and report generation
- **Neon PostgreSQL**: Cloud-hosted database for user data persistence
- **Vercel**: Frontend and backend deployment platform

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                          │
│  React SPA (Port 10000) - React Router, TypeScript         │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
                     │
┌────────────────────▼────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PDF Parser   │  │ Question    │  │ Report       │     │
│  │ (Groq LLM)   │  │ Selector    │  │ Generator    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────┬───────────────────┬───────────────────┬─────────────┘
       │                   │                   │
       │                   │                   │
┌──────▼──────┐  ┌────────▼────────┐  ┌───────▼────────┐
│  Groq API   │  │ Neon PostgreSQL│  │ Question Banks│
│  (LLM)      │  │ (Database)      │  │ (.txt files)   │
└─────────────┘  └─────────────────┘  └───────────────┘
```

### Component Flow
1. **Frontend** → User interactions, state management, UI rendering
2. **Backend API** → Request handling, business logic, data processing
3. **Groq LLM** → Text cleanup, resume parsing, report generation
4. **PostgreSQL** → User profile storage, data persistence
5. **Question Banks** → Static text files with MCQ questions

---

## Complete User Workflow

### Step 1: Resume Upload & Parsing (`/`)
**User Action**: Upload PDF resume

**Frontend Flow**:
1. User drags/drops or selects PDF file
2. Clicks "Parse Resume" button
3. Shows loading overlay: "Analyzing your resume…"

**Backend Flow**:
1. Receives PDF via `POST /parse?cleanup=true`
2. Extracts raw text using `pypdf`
3. Sends text to Groq LLM for cleanup (normalization)
4. Parses resume using Groq with structured JSON output
5. Returns: `{name, email, phone, experience[], tenth_percentage, twelfth_percentage, degree_percentage_or_cgpa}`

**Database Flow**:
1. Frontend calls `POST /users` with parsed data
2. Backend creates/updates `user_profiles` table
3. Returns `user_id` (UUID)

**UI Update**:
- Displays profile summary card
- Shows "Continue" button → navigates to `/questions`

---

### Step 2: Skill Level Selection (`/questions`)
**User Action**: Select proficiency levels for three categories

**Frontend Flow**:
1. Displays three skill cards: Aptitude, Reasoning, Coding
2. Each has three options: Beginner, Intermediate, Advance
3. User selects levels and clicks "Continue"
4. Shows loading: "Selecting the best questions for you…"

**Backend Flow**:
1. Frontend calls `POST /responses` with `{user_id, aptitude_level, reasoning_level, coding_level}`
2. Updates `user_profiles` table with skill levels
3. Frontend calls `POST /select_questions` with:
   ```json
   {
     "user_id": "uuid",
     "aptitude_level": "beginner|intermediate|advance",
     "reasoning_level": "beginner|intermediate|advance",
     "coding_level": "beginner|intermediate|advance",
     "counts": {"aptitude": 10, "reasoning": 10, "coding": 10}
   }
   ```
4. Backend:
   - Fetches user profile from database
   - Computes resume strength (WEAK/AVERAGE/STRONG/EXTREMELY_STRONG)
   - Applies difficulty matrix to determine final levels
   - Loads questions from text files (`aptitude.txt`, `reasoning.txt`, `coding.txt`)
   - Selects questions matching final difficulty levels
   - Returns question set

**UI Update**:
- Shows "Continue to Instructions" button
- Navigates to `/instructions`

---

### Step 3: Test Instructions (`/instructions`)
**User Action**: Review test guidelines

**Frontend Flow**:
1. Displays accordion sections:
   - General Guidelines
   - Aptitude Test (10 questions)
   - Logical Reasoning Test (10 questions)
   - Coding Test (10 questions)
   - Important Notes
2. Shows "Ready to Start?" card with warning about timer
3. "Start Test" button → navigates to `/test`

---

### Step 4: Timed Assessment (`/test`)
**User Action**: Answer 30 MCQ questions within 30 minutes

**Frontend Flow**:
1. **Split-Screen Layout**:
   - **Left Panel (70%)**: Current question, options, navigation
   - **Right Panel (30%)**: Question grid (1-30), progress, section labels

2. **Timer**: 30:00 countdown (auto-submits at 00:00)

3. **Question Navigation**:
   - Previous/Next buttons
   - Click question numbers to jump
   - Visual indicators: Answered (blue), Current (highlighted), Unanswered (gray)

4. **Answer Tracking**:
   - Radio buttons for each option
   - Selected answers stored in state
   - Progress bar shows completion percentage

5. **Submission**:
   - "Submit Test" button (on last question)
   - Auto-submit on timer expiration
   - Computes score client-side
   - Builds report payload

**Score Calculation**:
```typescript
{
  answers: [
    {
      index: 1,
      domain: "aptitude",
      difficulty: "beginner",
      question: "...",
      selected: "Option A",
      correct: "Option B",
      isCorrect: false
    },
    // ... 29 more
  ],
  totals: {
    overall: 22,
    aptitude: 7,
    reasoning: 8,
    coding: 7,
    totalQuestions: 30
  },
  behavior: {
    accuracy: 73,
    consistency: "Moderately consistent"
  },
  profile: { /* parsed resume data */ }
}
```

**Navigation**: Automatically redirects to `/results` with report payload

---

### Step 5: Results & Report (`/results`)
**User Action**: View comprehensive career development report

**Frontend Flow**:
1. Shows loading: "Generating your personalized report…"
2. Calls `POST /generate_report` with report payload
3. Displays LLM-generated markdown report

**Backend Flow**:
1. Receives report payload
2. Sends to Groq LLM with system prompt:
   - Performance Analysis
   - Skill Gap Analysis
   - Personalized 6-Week Improvement Plan
   - Career Guidance
   - Internship Recommendations
   - Final Summary
3. Returns markdown text

**UI Sections**:
- **LLM Report**: Full markdown report (regenerated each time)
- **Performance Analysis**: Score breakdown by domain and difficulty
- **Skill Gap Analysis**: Strengths and weaknesses
- **Improvement Plan**: 6-week structured roadmap
- **Career Guidance**: Role recommendations
- **Internship Recommendations**: 5-10 tailored suggestions
- **Final Summary**: Overall assessment and next steps

**Navigation**: "Finish" button → returns to `/`

---

## Backend API Endpoints

### Base URL
- **Local**: `http://localhost:8000`
- **Production**: `https://interview-ai-ruddy.vercel.app`

### Endpoints

#### 1. `GET /`
**Purpose**: API information
**Response**:
```json
{
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
```

#### 2. `GET /health`
**Purpose**: Health check
**Response**:
```json
{
  "status": "ok",
  "db": "ok" | "not_configured",
  "db_error": null | "error message"
}
```

#### 3. `POST /parse`
**Purpose**: Parse resume PDF
**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `pdf` (file), `cleanup=true` (query param)

**Response**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "experience": [
    "Software Engineer @ Tech Corp",
    "Intern @ Startup Inc"
  ],
  "tenth_percentage": "91%",
  "twelfth_percentage": "88%",
  "degree_percentage_or_cgpa": "8.4/10"
}
```

**Process**:
1. Extract text from PDF using `pypdf`
2. Clean text with Groq LLM (if `cleanup=true`)
3. Parse with Groq using structured JSON output (`response_format={"type": "json_object"}`)
4. Return minimal schema

#### 4. `POST /users`
**Purpose**: Create or update user profile
**Request**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "tenth_percentage": "91%",
  "twelfth_percentage": "88%",
  "degree_percentage_or_cgpa": "8.4/10",
  "experience": ["...", "..."]
}
```

**Response**:
```json
{
  "user_id": "uuid-string",
  "persisted": true | false
}
```

**Logic**:
- If email exists → update existing record
- Otherwise → create new record
- Returns fake UUID if database not configured

#### 5. `POST /responses`
**Purpose**: Save user skill level selections
**Request**:
```json
{
  "user_id": "uuid",
  "aptitude_level": "beginner" | "intermediate" | "advance",
  "reasoning_level": "beginner" | "intermediate" | "advance",
  "coding_level": "beginner" | "intermediate" | "advance"
}
```

**Response**:
```json
{
  "saved": true | false
}
```

#### 6. `POST /select_questions`
**Purpose**: Select personalized question set
**Request**:
```json
{
  "user_id": "uuid",
  "aptitude_level": "beginner",
  "reasoning_level": "intermediate",
  "coding_level": "advance",
  "counts": {
    "aptitude": 10,
    "reasoning": 10,
    "coding": 10
  }
}
```

**Response**:
```json
{
  "aptitude": {
    "final_level": "beginner",
    "questions": [
      {
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "B",
        "explanation": "",
        "level": "beginner"
      },
      // ... 9 more
    ]
  },
  "reasoning": { /* same structure */ },
  "coding": { /* same structure */ }
}
```

**Algorithm**:
1. Fetch user profile from database
2. Compute resume strength (see Question Selection Algorithm)
3. Apply difficulty matrix
4. Load questions from text files
5. Select questions matching final levels
6. Return structured response

#### 7. `POST /generate_report`
**Purpose**: Generate AI-powered career report
**Request**:
```json
{
  "answers": [
    {
      "index": 1,
      "domain": "aptitude",
      "difficulty": "beginner",
      "question": "...",
      "selected": "A",
      "correct": "B",
      "isCorrect": false
    }
    // ... 29 more
  ],
  "totals": {
    "overall": 22,
    "aptitude": 7,
    "reasoning": 8,
    "coding": 7,
    "totalQuestions": 30
  },
  "behavior": {
    "accuracy": 73,
    "consistency": "Moderately consistent"
  },
  "profile": { /* parsed resume */ },
  "model": "llama-3.1-8b-instant"
}
```

**Response**:
```json
{
  "report_markdown": "# Career & Skill Development Report\n\n..."
}
```

**Process**:
1. Build system prompt with report structure
2. Send to Groq LLM with test results and profile
3. Return markdown report (fresh for each attempt)

---

## Frontend Routes & Components

### Routes (React Router)
- `/` → `ParsePage`
- `/questions` → `QuestionsPage`
- `/instructions` → `InstructionsPage`
- `/test` → `TestPage`
- `/results` → `ResultsPage`

### Components

#### ParsePage (`/`)
- **State**: `file`, `loading`, `data`, `error`, `userId`
- **Actions**:
  - `handleParse()`: Upload PDF, parse, save to DB
- **UI**: File uploader, profile summary card, Continue button

#### QuestionsPage (`/questions`)
- **State**: `aptitude`, `reasoning`, `coding`, `saving`, `selected`, `ready`
- **Actions**:
  - `onSubmit()`: Save levels, select questions
- **UI**: Three skill cards with pill buttons, Continue button

#### InstructionsPage (`/instructions`)
- **State**: None (static)
- **UI**: Accordion sections, "Ready to Start?" card, Start Test button

#### TestPage (`/test`)
- **State**: `current`, `answers`, `remaining`, `result`
- **Actions**:
  - Timer countdown (30 minutes)
  - Answer selection
  - `buildReport()`: Compute scores
  - `handleSubmit()`: Navigate to results
- **UI**: Split-screen layout, timer, progress bar, question grid

#### ResultsPage (`/results`)
- **State**: `loading`, `llmMd`, `llmErr`
- **Actions**:
  - `fetchLLM()`: Generate report from backend
- **UI**: LLM report, performance analysis, skill gaps, improvement plan, career guidance

---

## Data Models & Database Schema

### PostgreSQL Table: `user_profiles`

```sql
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  tenth_percentage TEXT,
  twelfth_percentage TEXT,
  degree_percentage_or_cgpa TEXT,
  experience JSONB,
  aptitude_level TEXT,
  reasoning_level TEXT,
  coding_level TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Data Flow

```
PDF Upload
    ↓
Extract Text (pypdf)
    ↓
Clean with Groq LLM
    ↓
Parse with Groq (Structured JSON)
    ↓
Save to user_profiles
    ↓
Select Skill Levels
    ↓
Update user_profiles (aptitude_level, reasoning_level, coding_level)
    ↓
Select Questions (based on resume strength + user levels)
    ↓
Take Test (client-side scoring)
    ↓
Generate Report (Groq LLM)
    ↓
Display Results
```

---

## AI/LLM Integration

### Groq API Usage

#### 1. Text Cleanup (`clean_with_groq_llm`)
**Model**: `llama-3.1-8b-instant`
**Purpose**: Normalize extracted PDF text
**Process**:
- Chunks text into 12,000 character segments
- Sends to Groq with cleanup prompt
- Merges cleaned chunks
- Returns normalized text

#### 2. Resume Parsing (`parse_resume_with_groq`)
**Model**: `llama-3.1-8b-instant`
**Purpose**: Extract structured data from resume text
**Output Format**: JSON (structured output mode)
**Schema**: Pydantic `ResumeSchema`
- Uses `response_format={"type": "json_object"}`
- Temperature: `0.0` (deterministic)
- Guarantees valid JSON (no truncation, no malformed syntax)

**Fields Extracted**:
- `name`, `email`, `phone`
- `links`: `{linkedin, github, portfolio, other[]}`
- `summary`
- `education[]`: `{institution, degree, field, start, end, grade_type, grade_value}`
- `experience[]`: `{title, company, location, start, end, bullets[]}`
- `projects[]`: `{name, description, tech_stack[]}`
- `skills`: `{programming_languages[], frameworks_libraries[], tools[], other[]}`

#### 3. Report Generation (`generate_report`)
**Model**: `llama-3.1-8b-instant`
**Purpose**: Generate personalized career development report
**Temperature**: `0.2` (slightly creative but grounded)
**Input**: Test results, academic profile
**Output**: Markdown report with:
- Performance Analysis
- Skill Gap Analysis
- Personalized 6-Week Improvement Plan
- Career Guidance
- Internship Recommendations
- Final Summary

**Key Feature**: Fresh report generated for each test attempt (not cached)

---

## Question Selection Algorithm

### Resume Strength Calculation

**Input**: User profile from database
**Factors**:
1. **CGPA/Degree %**: 
   - ≥9.0: +4 points
   - ≥8.0: +3 points
   - ≥7.0: +2 points
   - <7.0: +1 point

2. **12th Percentage**:
   - ≥95%: +4 points
   - ≥90%: +3 points
   - ≥80%: +2 points
   - <80%: +1 point

3. **10th Percentage**:
   - ≥95%: +3 points
   - ≥85%: +2 points
   - <85%: +1 point

4. **Experience Count**:
   - ≥3: +4 points
   - 2: +3 points
   - 1: +2 points
   - 0: +1 point

**Total Score → Strength**:
- ≥12: `EXTREMELY_STRONG`
- ≥9: `STRONG`
- ≥6: `AVERAGE`
- <6: `WEAK`

### Difficulty Decision Matrix

| Resume Strength | User Selection | Final Level |
|----------------|----------------|-------------|
| WEAK | Beginner | Beginner |
| WEAK | Intermediate | Beginner |
| WEAK | Advance | Intermediate |
| AVERAGE | Beginner | Beginner |
| AVERAGE | Intermediate | Intermediate |
| AVERAGE | Advance | Advance |
| STRONG | Beginner | Beginner |
| STRONG | Intermediate | Advance |
| STRONG | Advance | Advance |
| EXTREMELY_STRONG | Beginner | Beginner |
| EXTREMELY_STRONG | Intermediate | Advance |
| EXTREMELY_STRONG | Advance | Advance |

### Question Loading

**Sources**:
1. `aptitude.txt` (project root)
2. `reasoning.txt` (project root)
3. `coding.txt` (project root)

**Parsing Logic**:
- Detects difficulty sections: "Beginner", "Intermediate", "Advanced"
- Extracts questions with format:
  ```
  Question text
  A) Option A
  B) Option B
  C) Option C
  D) Option D
  Answer: B
  ```
- Falls back to positional split (1-40 beginner, 41-70 intermediate, 71-100 advance)

**Selection**:
- Filters questions by final difficulty level
- Randomly shuffles and selects required count
- If insufficient, fills from remaining questions (no duplicates)

---

## Report Generation System

### Input Data Structure

```typescript
{
  answers: Array<{
    index: number;
    domain: "aptitude" | "reasoning" | "coding";
    difficulty?: string;
    question: string;
    selected?: string;
    correct: string;
    isCorrect: boolean;
  }>;
  totals: {
    overall: number;
    aptitude: number;
    reasoning: number;
    coding: number;
    totalQuestions: number;
  };
  behavior: {
    accuracy: number; // percentage
    consistency: "Highly consistent" | "Moderately consistent" | "Inconsistent";
  };
  profile: {
    name: string;
    email: string;
    phone: string;
    tenth_percentage: string;
    twelfth_percentage: string;
    degree_percentage_or_cgpa: string;
    experience: string[];
  } | null;
}
```

### LLM Prompt Structure

**System Prompt**:
```
You are a precise assessment analyst. Create a Career & Skill Development Report based solely on the provided data.

Rules:
- Use the user's results and academic profile only; do not invent data.
- Professional tone, clear headings, bullet points where helpful.
- Sections: Performance Analysis; Skill Gap Analysis; Personalized 6-Week Improvement Plan; Career Guidance; Internship Recommendations; Final Summary.
- Keep recommendations realistic for current level. Do not include code fences.
```

**User Content**:
```json
{
  "test_results": {
    "answers": [...],
    "totals": {...},
    "behavior": {...}
  },
  "academic_profile": {...},
  "format_instructions": {
    "headings": true,
    "no_code": true,
    "language": "English"
  }
}
```

### Report Sections

1. **Performance Analysis**
   - Total score breakdown
   - Domain-wise scores (Aptitude, Reasoning, Coding)
   - Accuracy percentage
   - Consistency indicator
   - Difficulty-level performance

2. **Skill Gap Analysis**
   - Strengths identification
   - Weaknesses identification
   - Industry benchmark comparison
   - Conceptual vs. careless error distinction

3. **Personalized 6-Week Improvement Plan**
   - Week-by-week structure
   - Specific topics to study
   - Recommended resources
   - Practice routines
   - Target improvements

4. **Career Guidance**
   - Role recommendations (Full-stack, Frontend, Data Analytics, QA, Business Analyst, DevOps)
   - Fit explanation
   - Required improvements for each role

5. **Internship Recommendations**
   - 5-10 tailored internship types
   - Company type suggestions (startups, mid-size)
   - Resume highlighting tips

6. **Final Summary**
   - Overall level assessment
   - Strongest opportunity
   - Critical weaknesses to fix first
   - Encouraging closing statement

---

## Deployment Architecture

### Vercel Serverless Functions

**Handler**: `api/index.py`
- Wraps FastAPI app with Mangum (AWS Lambda adapter)
- Handles serverless function invocation
- Logs all requests and errors

**Configuration**: `vercel.json`
```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "runtime": "python3.12"
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index"
    }
  ]
}
```

### Environment Variables

**Required**:
- `GROQ_API_KEY`: Groq API key for LLM calls
- `DATABASE_URL`: Neon PostgreSQL connection string
- `FRONTEND_ORIGIN`: Frontend URL for CORS (comma-separated or `*`)

**Local Development**:
- `.env` file with above variables
- Backend: `uvicorn api:app --host 0.0.0.0 --port 8000`
- Frontend: `npm run dev` (Vite on port 10000)

### CORS Configuration

```python
_default_dev_origins = ["http://localhost:10000", "http://127.0.0.1:10000"]
frontend_origin_raw = os.getenv("FRONTEND_ORIGIN", "").strip()
if not frontend_origin_raw:
    allowed_origins = _default_dev_origins
elif frontend_origin_raw == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in frontend_origin_raw.split(",") if origin.strip()]
    if not allowed_origins:
        allowed_origins = _default_dev_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Environment Variables

### Backend (`.env`)
```bash
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://neondb_owner:password@ep-...-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
FRONTEND_ORIGIN=http://localhost:10000
```

### Frontend (`.env`)
```bash
VITE_BACKEND_URL=http://localhost:8000
```

### Production (Vercel)
Set in Vercel Dashboard → Project Settings → Environment Variables:
- `GROQ_API_KEY`
- `DATABASE_URL`
- `FRONTEND_ORIGIN` (e.g., `https://your-frontend.vercel.app`)

---

## File Structure

```
project-root/
├── api.py                    # Main FastAPI backend
├── api/
│   └── index.py              # Vercel serverless handler
├── backend/
│   └── api.py                # Question selection logic
├── pdf_to_text_groq.py       # PDF extraction & LLM parsing
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main React app with routes
│   │   ├── main.tsx          # React entry point
│   │   └── styles.css        # Global styles
│   ├── index.html
│   └── package.json
├── aptitude.txt              # Aptitude question bank
├── reasoning.txt             # Reasoning question bank
├── coding.txt                # Coding question bank
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel configuration
├── Procfile                  # Process configuration
└── .env                      # Environment variables (local)
```

---

## Key Algorithms & Logic

### 1. Resume Strength Computation
- Weighted scoring based on academic performance and experience
- Categorizes into 4 levels for adaptive difficulty

### 2. Difficulty Matrix
- Combines resume strength with user self-assessment
- Prevents overconfidence (weak resume + advanced selection → intermediate)
- Respects explicit beginner choices

### 3. Question Selection
- Loads from plain text files with flexible parsing
- Filters by computed final difficulty
- Ensures no duplicates, fills gaps if needed

### 4. Score Calculation
- Client-side computation for immediate feedback
- Domain-wise breakdown
- Consistency analysis using rolling window variance

### 5. Report Generation
- Fresh LLM call for each attempt (no caching)
- Structured prompt ensures comprehensive coverage
- Fallback to local markdown if LLM fails

---

## Error Handling

### Backend
- All endpoints wrapped in try-except
- Graceful fallbacks (e.g., fake UUID if DB unavailable)
- Detailed error messages in responses
- Health endpoint never crashes

### Frontend
- Loading states for all async operations
- Error messages displayed to user
- Navigation guards (redirects if data missing)
- Timer auto-submission prevents data loss

---

## Security Considerations

1. **API Keys**: Never exposed to frontend, stored server-side only
2. **CORS**: Configured for specific origins (not wildcard in production)
3. **Input Validation**: Pydantic models validate all inputs
4. **SQL Injection**: Parameterized queries (psycopg)
5. **File Upload**: Temporary files cleaned up after processing

---

## Performance Optimizations

1. **LLM Calls**: Chunked text processing for large PDFs
2. **Database**: Connection pooling, autocommit for simple queries
3. **Frontend**: React memoization, efficient state updates
4. **Question Loading**: Cached in memory after first load
5. **Report Generation**: Async, non-blocking

---

## Future Enhancements

1. **User Authentication**: Login/signup system
2. **Test History**: Store and view past attempts
3. **Question Bank Expansion**: More questions per category
4. **Export Reports**: PDF download functionality
5. **Admin Dashboard**: View all users and analytics
6. **Email Reports**: Send reports via email
7. **Multi-language Support**: Internationalization

---

## Conclusion

The AI Interview Bot is a comprehensive assessment platform that combines:
- **AI-powered resume parsing** for accurate data extraction
- **Intelligent question selection** based on resume strength and user input
- **Timed assessment** with real-time progress tracking
- **Personalized career reports** generated fresh for each attempt

The system is designed for scalability, with serverless deployment, efficient database usage, and modular architecture that allows for easy extension and maintenance.

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Author**: AI Interview Bot Development Team


