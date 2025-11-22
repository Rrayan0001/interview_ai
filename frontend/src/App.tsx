import React, { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, Brain, Code, BarChart3, Clock, CheckCircle, AlertCircle, ArrowRight, ArrowLeft } from "lucide-react";

// UI Components
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Progress } from "./components/ui/progress";
import { Badge } from "./components/ui/badge";
import { LoadingOverlay, LoadingSpinner } from "./components/ui/loading";
import { cn } from "./lib/utils";

// -------------------- Types --------------------

type Parsed = {
  name: string;
  email: string;
  phone: string;
  experience: string[];
  tenth_percentage: string;
  twelfth_percentage: string;
  degree_percentage_or_cgpa: string;
};

type QuestionsGroup = { final_level: string; questions: any[] };

type QuestionsPayload = {
  aptitude: QuestionsGroup;
  reasoning: QuestionsGroup;
  coding: QuestionsGroup;
};

type ReportPayload = {
  answers: Array<{
    index: number;
    domain: "aptitude" | "reasoning" | "coding";
    difficulty?: string;
    question: string;
    selected?: string;
    correct: string;
    isCorrect: boolean;
  }>;
  totals: { overall: number; aptitude: number; reasoning: number; coding: number; totalQuestions: number };
  behavior: { accuracy: number; consistency: string };
  profile?: Parsed | null;
};

// Get backend URL from environment variable, with fallback
const getBackendUrl = () => {
  const envUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
  
  // Force Railway URL in production, ignoring localhost if set by mistake
  if (import.meta.env.PROD) {
    if (!envUrl || envUrl.includes("localhost")) {
      return "https://web-production-dad96.up.railway.app";
    }
    return envUrl;
  }
  
  // For development, use env var or localhost
  return envUrl || "http://localhost:8000";
};

const backendUrl = getBackendUrl();

// Debug log (only in development)
if (typeof window !== "undefined" && import.meta.env.DEV) {
  console.log("Backend URL:", backendUrl);
  console.log("VITE_BACKEND_URL env:", import.meta.env.VITE_BACKEND_URL);
}

// -------------------- Modern UI Components --------------------

function TimerCircle({ seconds }: { seconds: number }) {
  const pct = Math.max(0, Math.min(1, seconds / (30 * 60)));
  const deg = Math.round(360 * pct);
  const mm = Math.floor(seconds / 60);
  const ss = Math.floor(seconds % 60);
  return (
    <div className="timer-circle" style={{ background: `conic-gradient(var(--accent) ${deg}deg, #e6e8ee ${deg}deg)` }}>
      <div className="timer-circle-inner">
        {String(mm).padStart(2, "0")}:{String(ss).padStart(2, "0")}
      </div>
    </div>
  );
}

function Modal({
  open,
  title,
  children,
  onCancel,
  onConfirm,
  confirmText = "Confirm",
  cancelText = "Cancel",
}: {
  open: boolean;
  title: string;
  children: React.ReactNode;
  onCancel: () => void;
  onConfirm: () => void;
  confirmText?: string;
  cancelText?: string;
}) {
  if (!open) return null;
  return (
    <div className="overlay">
      <div className="modal">
        <h3>{title}</h3>
        <div className="modal-body">{children}</div>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onCancel}>{cancelText}</button>
          <button className="btn btn-primary" onClick={onConfirm}>{confirmText}</button>
        </div>
      </div>
    </div>
  );
}

// -------------------- Parse Page (/) --------------------

function ParsePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<Parsed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const navigate = useNavigate();

  async function handleParse(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const form = new FormData();
      form.append("pdf", file);
      const res = await fetch(`${backendUrl}/parse?cleanup=true`, { method: "POST", body: form });
      if (!res.ok) throw new Error(await res.text());
      const json = (await res.json()) as Parsed;
      setData(json);
      const userRes = await fetch(`${backendUrl}/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: json.name || "",
          email: json.email || "",
          phone: json.phone || "",
          tenth_percentage: json.tenth_percentage || "",
          twelfth_percentage: json.twelfth_percentage || "",
          degree_percentage_or_cgpa: json.degree_percentage_or_cgpa || "",
          experience: json.experience || [],
        }),
      });
      if (!userRes?.ok) throw new Error(await userRes.text());
      const u = await userRes.json();
      setUserId(u.user_id);
    } catch (err: any) {
      setError(err.message || "Parse failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      {loading && <LoadingOverlay text="Analyzing your resume with AI…" />}
      
      <div className="mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="flex items-center justify-center mb-4">
            <Brain className="h-12 w-12 text-primary mr-3" />
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              AI Interview Bot
            </h1>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Upload your resume and let our AI analyze your profile to create a personalized interview experience
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Upload className="h-5 w-5 mr-2" />
                Upload Resume
              </CardTitle>
              <CardDescription>
                Upload your PDF resume for AI-powered analysis and personalized questions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleParse} className="space-y-4">
                <div
                  className={cn(
                    "border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
                    dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
                    file && "border-green-500 bg-green-50"
                  )}
                  onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={(e) => { 
                    e.preventDefault(); 
                    setDragActive(false); 
                    const f = e.dataTransfer.files?.[0]; 
                    if (f && f.type === "application/pdf") setFile(f); 
                  }}
                  onClick={() => document.getElementById("file-input")?.click()}
                >
                  <input 
                    id="file-input" 
                    type="file" 
                    accept="application/pdf" 
                    className="hidden" 
                    onChange={(e) => setFile(e.target.files?.[0] || null)} 
                  />
                  
                  {file ? (
                    <div className="flex items-center justify-center">
                      <FileText className="h-8 w-8 text-green-600 mr-3" />
                      <div>
                        <p className="font-medium text-green-700">{file.name}</p>
                        <p className="text-sm text-green-600">Ready to analyze</p>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <Upload className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-lg font-medium mb-2">Drop your PDF here or click to browse</p>
                      <p className="text-sm text-muted-foreground">Supports PDF files up to 10MB</p>
                    </div>
                  )}
                </div>
                
                <Button 
                  type="submit" 
                  disabled={!file || loading} 
                  className="w-full"
                  size="lg"
                >
                  {loading ? (
                    <>
                      <LoadingSpinner size="sm" className="mr-2" />
                      Analyzing Resume...
                    </>
                  ) : (
                    <>
                      <Brain className="h-4 w-4 mr-2" />
                      Analyze Resume with AI
                    </>
                  )}
                </Button>
                
                {error && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center p-4 bg-destructive/10 border border-destructive/20 rounded-lg"
                  >
                    <AlertCircle className="h-5 w-5 text-destructive mr-3" />
                    <p className="text-destructive font-medium">{error}</p>
                  </motion.div>
                )}
              </form>
            </CardContent>
          </Card>
        </motion.div>

        {data && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                  Profile Extracted Successfully
                </CardTitle>
                <CardDescription>
                  Review your extracted information before proceeding
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Name</label>
                    <p className="font-medium">{data.name || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Email</label>
                    <p className="font-medium">{data.email || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Phone</label>
                    <p className="font-medium">{data.phone || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">10th Grade %</label>
                    <p className="font-medium">{data.tenth_percentage || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">12th Grade %</label>
                    <p className="font-medium">{data.twelfth_percentage || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-muted-foreground">Degree %/CGPA</label>
                    <p className="font-medium">{data.degree_percentage_or_cgpa || "—"}</p>
                  </div>
                </div>
                
                {data.experience?.length ? (
                  <div className="space-y-3">
                    <label className="text-sm font-medium text-muted-foreground">Experience</label>
                    <div className="space-y-2">
                      {data.experience.map((exp, i) => (
                        <Badge key={i} variant="secondary" className="mr-2 mb-2">
                          {exp}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}
                
                {userId && (
                  <div className="pt-4">
                    <Button 
                      onClick={() => navigate("/questions", { state: { userId, parsed: data } })}
                      size="lg"
                      className="w-full"
                    >
                      Continue to Skill Assessment
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
}

// -------------------- Questions Page (/questions) --------------------

function QuestionsPage() {
  const location = useLocation() as any;
  const navigate = useNavigate();
  const userId: string | undefined = location?.state?.userId;
  const parsed: Parsed | undefined = location?.state?.parsed;

  const [aptitude, setAptitude] = useState("beginner");
  const [reasoning, setReasoning] = useState("beginner");
  const [coding, setCoding] = useState("beginner");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<QuestionsPayload | null>(null);
  const [ready, setReady] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) { setErr("Missing userId; parse your resume first."); return; }
    setSaving(true); setErr(null); setMsg(null);
    try {
      const res = await fetch(`${backendUrl}/responses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, aptitude_level: aptitude, reasoning_level: reasoning, coding_level: coding }),
      });
      if (!res.ok) throw new Error(await res.text());
      setMsg("Responses saved successfully.");

      // Include resume data in the request
      // Include resume data from parsed state or fallback to empty
      const resumeData = parsed ? {
        tenth_percentage: parsed.tenth_percentage || "--",
        twelfth_percentage: parsed.twelfth_percentage || "--",
        degree_percentage_or_cgpa: parsed.degree_percentage_or_cgpa || "--",
        experience: parsed.experience || []
      } : undefined;

      const qs = await fetch(`${backendUrl}/select_questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user_id: userId, 
          aptitude_level: aptitude, 
          reasoning_level: reasoning, 
          coding_level: coding, 
          counts: { aptitude: 10, reasoning: 10, coding: 10 },
          resume: resumeData
        }),
      });
      if (!qs.ok) throw new Error(await qs.text());
      const payload = (await qs.json()) as QuestionsPayload;
      setSelected(payload);
      setReady(true);
    } catch (e: any) {
      setErr(e.message || "Failed to generate questions");
    } finally {
      setSaving(false);
    }
  }

  function toInstructions() {
    if (!selected) return;
    navigate("/instructions", { state: { userId, selected, parsed } });
  }

  return (
    <div className="container">
      {saving && <LoaderOverlay text="Selecting the best questions for you…" />}
      <header className="page-head">
        <h1>Choose Your Skill Levels</h1>
        <p>We tailor the exam based on your comfort level.</p>
      </header>

      <form className="card levels" onSubmit={onSubmit}>
        <div className="levels-grid">
          <div className="skill-card">
            <div className="skill-card-header">Aptitude</div>
            <div className="pill-group">
              {["beginner", "intermediate", "advance"].map((o) => (
                <button type="button" className={`pill ${aptitude === o ? "active" : ""}`} key={o} onClick={() => setAptitude(o)}>
                  {o.charAt(0).toUpperCase() + o.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="skill-card">
            <div className="skill-card-header">Reasoning</div>
            <div className="pill-group">
              {["beginner", "intermediate", "advance"].map((o) => (
                <button type="button" className={`pill ${reasoning === o ? "active" : ""}`} key={o} onClick={() => setReasoning(o)}>
                  {o.charAt(0).toUpperCase() + o.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="skill-card">
            <div className="skill-card-header">Coding</div>
            <div className="pill-group">
              {["beginner", "intermediate", "advance"].map((o) => (
                <button type="button" className={`pill ${coding === o ? "active" : ""}`} key={o} onClick={() => setCoding(o)}>
                  {o.charAt(0).toUpperCase() + o.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-primary" type="submit" disabled={saving}>Continue</button>
          <button className="btn-ghost" type="button" onClick={() => navigate("/")}>Back</button>
        </div>
        {msg && <div className="info">{msg}</div>}
        {err && <div className="error">{err}</div>}
      </form>

      {ready && (
        <section className="card ready-card">
          <h2>Profile Ready</h2>
          <p>We’ve prepared your personalized question set.</p>
          <button className="btn btn-primary" onClick={toInstructions}>Continue to Instructions</button>
        </section>
      )}
    </div>
  );
}

// -------------------- Instructions Page (/instructions) --------------------

function InstructionsPage() {
  const location = useLocation() as any;
  const navigate = useNavigate();
  const userId: string | undefined = location?.state?.userId;

  return (
    <div className="container">
      <header className="page-head">
        <h1>Test Instructions</h1>
        <p>Read all instructions carefully before starting the assessment.</p>
      </header>
      <section className="card">
        <details open>
          <summary><strong>General Guidelines</strong></summary>
          <p>Ensure a stable internet connection. Do not refresh the page during the test. Keep your device charged.</p>
        </details>
        <details>
          <summary><strong>Aptitude Test</strong></summary>
          <p>10 questions, multiple choice. Choose the best answer.</p>
        </details>
        <details>
          <summary><strong>Logical Reasoning Test</strong></summary>
          <p>10 questions focusing on analytical and logical skills.</p>
        </details>
        <details>
          <summary><strong>Coding Test</strong></summary>
          <p>10 questions assessing fundamentals and problem-solving.</p>
        </details>
        <details>
          <summary><strong>Important Notes</strong></summary>
          <ul>
            <li>The timer (30 minutes) starts once you begin the test.</li>
            <li>You cannot pause the test once started.</li>
            <li>Submit before time runs out to save your answers.</li>
          </ul>
        </details>
      </section>
      <section className="card" style={{ background: "#ecfdf5", borderColor: "#bbf7d0" }}>
        <h3>Ready to Start?</h3>
        <p>Once you click <strong>Start Test</strong>, the timer will begin and cannot be paused.</p>
        <div className="actions">
          <button className="btn-ghost" onClick={() => navigate("/questions", { state: { userId, parsed: location?.state?.parsed } })}>Back</button>
          <button className="btn btn-primary" onClick={() => navigate("/test", { state: { userId, selected: location?.state?.selected, parsed: location?.state?.parsed } })}>Start Test</button>
        </div>
      </section>
    </div>
  );
}

// -------------------- Test Page (/test) — Split Screen --------------------

type FlatQ = { id: string; domain: "aptitude" | "reasoning" | "coding"; q: any };

function TestPage() {
  const location = useLocation() as any;
  const navigate = useNavigate();
  const selected: QuestionsPayload | undefined = location?.state?.selected;
  const parsed: Parsed | undefined = location?.state?.parsed;

  const flat: FlatQ[] = useMemo(() => {
    const arr: FlatQ[] = [];
    if (!selected) return arr;
    (selected.aptitude?.questions || []).forEach((q: any, i: number) => arr.push({ id: `q-${i + 1}`, domain: "aptitude", q }));
    (selected.reasoning?.questions || []).forEach((q: any, i: number) => arr.push({ id: `q-${10 + i + 1}`, domain: "reasoning", q }));
    (selected.coding?.questions || []).forEach((q: any, i: number) => arr.push({ id: `q-${20 + i + 1}`, domain: "coding", q }));
    return arr;
  }, [selected]);

  const total = flat.length || 0;
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [remaining, setRemaining] = useState(30 * 60);
  const [result, setResult] = useState<ReportPayload | null>(null);

  useEffect(() => {
    if (!selected) return;
    if (remaining <= 0) return setResult(buildReport());
    const id = setInterval(() => setRemaining((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(id);
  }, [remaining]);

  function buildReport(): ReportPayload {
    const per: ReportPayload["answers"] = flat.map((f, idx) => {
      const chosen = answers[f.id];
      const correct = f.q?.correct_answer ?? "";
      return {
        index: idx + 1,
        domain: f.domain,
        difficulty: f.q?.level || f.q?.difficulty || undefined,
        question: f.q?.question || "",
        selected: chosen,
        correct,
        isCorrect: !!chosen && !!correct && chosen === correct,
      };
    });

    const totals = per.reduce(
      (acc, r) => {
        if (r.isCorrect) {
          acc.overall += 1;
          acc[r.domain] += 1 as any;
        }
        return acc;
      },
      { overall: 0, aptitude: 0, reasoning: 0, coding: 0, totalQuestions: per.length }
    );

    // Simple behavior indicator: variance of correctness over rolling windows -> consistency label
    const correctSeq = per.map((p) => (p.isCorrect ? 1 : 0));
    const window = 5;
    const chunks: number[] = [];
    for (let i = 0; i < correctSeq.length; i += window) {
      const slice = correctSeq.slice(i, i + window);
      const mean = slice.reduce((a: number, b: number) => a + b, 0) / (slice.length || 1);
      chunks.push(mean);
    }
    const mean = chunks.reduce((a: number, b: number) => a + b, 0) / (chunks.length || 1);
    const variance = chunks.reduce((a: number, b: number) => a + (b - mean) * (b - mean), 0) / (chunks.length || 1);
    const consistency = variance < 0.05 ? "Highly consistent" : variance < 0.12 ? "Moderately consistent" : "Inconsistent";

    return {
      answers: per,
      totals,
      behavior: { accuracy: totals.totalQuestions ? Math.round((totals.overall / totals.totalQuestions) * 100) : 0, consistency },
      profile: parsed || null,
    };
  }

  function handleSubmit() {
    const report = buildReport();
    setResult(report);
    navigate("/results", { state: { report } });
  }

  if (!selected) {
    return (
      <div className="container">
        <div className="card">No test loaded. Go back to Skill Level.</div>
        <button className="btn btn-primary" onClick={() => navigate("/questions")}>Back</button>
      </div>
    );
  }

  const currentQ = flat[current];
  const answeredCount = Object.keys(answers).length;
  const progress = total ? (answeredCount / total) * 100 : 0;

  if (result) {
    // Guard: navigation should already redirect; still show minimal
    return (
      <div className="container"><div className="card">Submitting…</div></div>
    );
  }

  return (
    <div className="container">
      <div className="card test-header">
        <div className="test-header-left">AI Assessment</div>
        <div className="test-header-center"><ProgressBar value={progress} /></div>
        <div className="test-header-right"><TimerCircle seconds={remaining} /></div>
      </div>

      <div className="split">
        <div className="left-panel card">
          <div className="q-meta">Question {current + 1} of {total}</div>
          <div className="q-view">
            <h3 className="q-title">{currentQ?.q?.question || ""}</h3>
            <div className="options">
              {(currentQ?.q?.options || []).map((opt: string, i: number) => {
                const checked = answers[currentQ.id] === opt;
                return (
                  <label key={i} className={`opt ${checked ? "opt-active" : ""}`}>
                    <input
                      type="radio"
                      name={currentQ.id}
                      value={opt}
                      checked={checked}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [currentQ.id]: e.target.value }))}
                    />
                    <span>{opt}</span>
                  </label>
                );
              })}
            </div>
          </div>
          <div className="actions">
            <button className="btn-ghost" disabled={current === 0} onClick={() => setCurrent((c) => Math.max(0, c - 1))}>Previous</button>
            {current < total - 1 ? (
              <button className="btn btn-primary" onClick={() => setCurrent((c) => Math.min(total - 1, c + 1))}>Next</button>
            ) : (
              <button className="btn btn-primary" onClick={handleSubmit}>Submit Test</button>
            )}
          </div>
        </div>

        <div className="right-panel card">
          <h3>Questions</h3>
          <div className="grid-nav">
            {flat.map((f, idx) => {
              const isCurrent = idx === current;
              const isAnswered = !!answers[f.id];
              return (
                <button
                  key={f.id}
                  className={`bubble ${isCurrent ? "bubble-current" : isAnswered ? "bubble-answered" : ""}`}
                  onClick={() => setCurrent(idx)}
                >
                  {idx + 1}
                </button>
              );
            })}
          </div>
          <div className="legend">
            <span className="legend-item"><span className="legend-dot bubble bubble-answered" /> Answered</span>
            <span className="legend-item"><span className="legend-dot bubble" /> Unanswered</span>
            <span className="legend-item"><span className="legend-dot bubble bubble-current" /> Current</span>
          </div>
          <div className="section-tags">
            <div>Aptitude 1–10</div>
            <div>Reasoning 11–20</div>
            <div>Coding 21–30</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// -------------------- Results Page (/results) --------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  );
}

function ResultsPage() {
  const location = useLocation() as any;
  const navigate = useNavigate();
  const report: ReportPayload | undefined = location?.state?.report;
  const [loading, setLoading] = useState(false);
  const [llmMd, setLlmMd] = useState<string | null>(null);
  const [llmErr, setLlmErr] = useState<string | null>(null);

  if (!report) {
    return (
      <div className="container">
        <div className="card">No report data available.</div>
        <button className="btn btn-primary" onClick={() => navigate("/")}>Home</button>
      </div>
    );
  }

  const { answers, totals, behavior, profile } = report;

  async function fetchLLM() {
    setLoading(true); setLlmErr(null);
    try {
      const res = await fetch(`${backendUrl}/generate_report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });
      if (!res.ok) throw new Error(await res.text());
      const j = await res.json();
      setLlmMd(j.report_markdown || "");
    } catch (e: any) {
      setLlmErr(e.message || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchLLM(); }, []);

  // Domain accuracy
  const domainTotals = {
    aptitude: answers.filter(a => a.domain === "aptitude").length || 0,
    reasoning: answers.filter(a => a.domain === "reasoning").length || 0,
    coding: answers.filter(a => a.domain === "coding").length || 0,
  } as any;

  function pct(n: number, d: number) { return d ? Math.round((n / d) * 100) : 0; }

  // Strengths & weaknesses quick take
  const strengths: string[] = [];
  const weaknesses: string[] = [];
  if (pct(totals.aptitude, domainTotals.aptitude) >= 70) strengths.push("Aptitude reasoning and quantitative basics");
  else weaknesses.push("Quantitative techniques and applied aptitude");
  if (pct(totals.reasoning, domainTotals.reasoning) >= 70) strengths.push("Logical reasoning and patterns");
  else weaknesses.push("Analytical reasoning and pattern recognition");
  if (pct(totals.coding, domainTotals.coding) >= 70) strengths.push("Coding fundamentals and theory");
  else weaknesses.push("Core coding concepts and algorithms");

  // Difficulty lens
  const byDifficulty = (lvl: string) => answers.filter(a => (a.difficulty || "").toLowerCase().includes(lvl)).map(a => a.isCorrect ? 1 : 0);
  const easyAcc = byDifficulty("begin");
  const midAcc = byDifficulty("inter");
  const hardAcc = byDifficulty("adv");
  const avg = (arr: number[]) => arr.length ? Math.round(((arr.reduce((s: number, v: number)=>s+v,0))/arr.length)*100) : 0;

  return (
    <div className="container">
      {loading && <LoaderOverlay text="Generating your personalized report…" />}
      <header className="page-head">
        <h1>Career & Skill Development Report</h1>
        <p>A personalized analysis based on your test performance and academic profile.</p>
      </header>

      {llmMd ? (
        <section className="card">
          <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{llmMd}</div>
          <div className="actions mt">
            <button className="btn btn-primary" onClick={fetchLLM}>Regenerate</button>
          </div>
        </section>
      ) : null}

      {llmErr && (
        <section className="card"><div className="error">{llmErr}</div></section>
      )}

      <Section title="Performance Analysis">
        <ul className="nice-list">
          <li><strong>Total Score:</strong> {totals.overall} / {totals.totalQuestions} ({behavior.accuracy}%)</li>
          <li><strong>Aptitude:</strong> {totals.aptitude} / {domainTotals.aptitude} ({pct(totals.aptitude, domainTotals.aptitude)}%)</li>
          <li><strong>Reasoning:</strong> {totals.reasoning} / {domainTotals.reasoning} ({pct(totals.reasoning, domainTotals.reasoning)}%)</li>
          <li><strong>Coding:</strong> {totals.coding} / {domainTotals.coding} ({pct(totals.coding, domainTotals.coding)}%)</li>
          <li><strong>Consistency:</strong> {behavior.consistency}</li>
          <li><strong>By Difficulty:</strong> Easy ≈ {avg(easyAcc)}% • Intermediate ≈ {avg(midAcc)}% • Advanced ≈ {avg(hardAcc)}%</li>
        </ul>
      </Section>

      <Section title="Skill Gap Analysis">
        <ul className="nice-list">
          {strengths.length ? <li><strong>Strengths:</strong> {strengths.join(", ")}</li> : null}
          {weaknesses.length ? <li><strong>Weaknesses:</strong> {weaknesses.join(", ")}</li> : null}
          <li>Entry-level benchmark alignment: solidify quantitative basics, structured reasoning, and core CS fundamentals.</li>
          <li>Differentiate between conceptual clarity and error-carefulness by reviewing wrong answers with explanations.</li>
        </ul>
      </Section>

      <Section title="Personalized 6-Week Improvement Plan">
        <ol className="nice-list">
          <li><strong>Weeks 1–2:</strong> Quantitative basics (percentages, ratios, arithmetic) • Daily 30 MCQs • Resource: GFG Aptitude, Khan Academy.</li>
          <li><strong>Weeks 1–2 (Parallel):</strong> Reasoning (series, syllogisms, seating, data sufficiency) • Daily 20 MCQs • Resource: IndiaBix Reasoning.</li>
          <li><strong>Weeks 3–4:</strong> Coding fundamentals (time/space, arrays, strings, hashing) • 3 problems/day • Resource: LeetCode Easy/Medium.</li>
          <li><strong>Week 4:</strong> OOPs, DBMS, OS quick notes • 1 hr/day • Resource: InterviewBit CS notes.</li>
          <li><strong>Weeks 5–6:</strong> Mixed mocks: 30Q timed sets • Post-test error log • Target accuracy +10%.</li>
          <li><strong>Routine:</strong> 60–90 mins daily • Review all wrong answers same day • Maintain a mistakes journal.</li>
        </ol>
      </Section>

      <Section title="Career Guidance">
        <ul className="nice-list">
          <li><strong>Full‑stack / Frontend Development:</strong> Good fit if UI and JS fundamentals appeal. Improve DSA basics and project depth.</li>
          <li><strong>Data Analytics:</strong> Consider if quantitative accuracy trends up. Learn Excel→SQL→Python→Tableau pipeline.</li>
          <li><strong>QA / SDET Foundations:</strong> Strong for detail-oriented profiles. Learn testing frameworks and automation basics.</li>
          <li><strong>Business Analyst (Tech):</strong> Blend of reasoning + communication. Practice case studies and SQL basics.</li>
          <li><strong>DevOps Foundations:</strong> If systems interest you. Learn Linux, Git, CI/CD basics; scripting fundamentals.</li>
        </ul>
        <p className="mt small">Why: choices align with current strengths and offer clear upskilling paths. Focus on closing core gaps noted above.</p>
      </Section>

      <Section title="Internship Recommendations">
        <ul className="nice-list">
          <li>Frontend / React Intern • Emphasize projects, responsive UI, component patterns.</li>
          <li>Full‑stack MERN Intern • Showcase CRUD apps, auth, and API design.</li>
          <li>QA / Automation Intern • Demonstrate test cases, Cypress/Selenium basics.</li>
          <li>Data Analyst Intern • Highlight Excel/SQL, small dashboards, EDA notebooks.</li>
          <li>Business Analyst Intern • Requirements drafting, wireframes, stakeholder docs.</li>
          <li>DevOps Intern • Docker basics, CI/CD toy pipeline, IaC curiosity.</li>
        </ul>
        <p className="small">Target startups and mid-size firms for broader exposure; tailor resume to measurable outcomes and projects.</p>
      </Section>

      <Section title="Final Summary">
        <p>
          Overall level: <strong>{behavior.accuracy >= 70 ? "Strong" : behavior.accuracy >= 50 ? "Average" : "Developing"}</strong>. Strongest opportunity: {strengths[0] || "foundation building"}. Critical first fixes: {weaknesses.slice(0,2).join(", ") || "reinforce fundamentals"}. Keep a steady routine, track mistakes, and expect visible improvement within 6–8 weeks.
        </p>
      </Section>

      {profile && (
        <Section title="Academic Profile (Provided)">
          <ul className="nice-list">
            <li>10th: {profile.tenth_percentage || "—"}</li>
            <li>12th: {profile.twelfth_percentage || "—"}</li>
            <li>Degree %/CGPA: {profile.degree_percentage_or_cgpa || "—"}</li>
          </ul>
        </Section>
      )}

      <div className="actions">
        <button className="btn btn-primary" onClick={() => navigate("/")}>Finish</button>
      </div>
    </div>
  );
}

// -------------------- App Root --------------------

export default function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/" element={<ParsePage />} />
        <Route path="/questions" element={<QuestionsPage />} />
        <Route path="/instructions" element={<InstructionsPage />} />
        <Route path="/test" element={<TestPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

