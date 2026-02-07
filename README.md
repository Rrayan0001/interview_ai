# AI Interview Bot

A full-stack application for resume parsing, candidate evaluation, and career development reporting.

## 🏗️ Architecture

- **Frontend**: React + Vite + TypeScript
- **Backend**: FastAPI (Python)
- **AI/ML**: Groq LLM for resume parsing and report generation
- **Database**: PostgreSQL (Neon) - Optional

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Groq API Key (get from [console.groq.com](https://console.groq.com))

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Rrayan0001/interview_ai.git
   cd interview_ai
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   export GROQ_API_KEY=your_key_here
   uvicorn main:app --reload
   ```
   Backend: `http://localhost:8000`

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend: `http://localhost:10000`

## 📁 Project Structure

```
.
├── backend/           # FastAPI backend
│   ├── main.py       # Main application
│   └── requirements.txt
├── frontend/          # React frontend
│   ├── src/
│   │   ├── App.tsx
│   │   └── services/  # API service functions
│   └── package.json
├── pdf_to_text_groq.py  # PDF parsing utilities
└── requirements.txt   # Root dependencies (legacy)
```

## 🔑 Features

- ✅ Resume PDF parsing with Groq LLM
- ✅ Extracts: Name, Email, Phone, 10th/12th percentages, Degree CGPA, Experience
- ✅ Candidate evaluation and scoring
- ✅ AI-powered career development reports
- ✅ Fallback parsing (works without API key)

## 📖 Documentation

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript, Vite
- **Backend**: FastAPI, Python
- **AI**: Groq API (LLM)
- **PDF**: pypdf
- **Database**: PostgreSQL (via psycopg)

## 📝 License

MIT

