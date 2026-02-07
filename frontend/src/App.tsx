import React, { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
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
// Get backend URL
const getBackendUrl = () => {
  // In Vercel, the backend is serverless at /api, so we use relative path
  if (import.meta.env.PROD) {
    return "/api";
  }
  // For local development
  return import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
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
    <div className="min-h-screen bg-white p-6">
      {loading && <LoadingOverlay text="ANALYZING YOUR RESUME WITH AI..." />}

      <div className="mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="flex items-center justify-center mb-6">
            <div className="brutal-border brutal-shadow-lg p-4 bg-black mr-6">
              <Brain className="h-16 w-16 text-white" />
            </div>
            <h1 className="text-6xl font-black uppercase tracking-wider leading-none">
              AI<br />INTERVIEW<br />BOT
            </h1>
          </div>
          <div className="brutal-border brutal-shadow bg-yellow-300 p-4 max-w-3xl mx-auto">
            <p className="text-xl font-bold uppercase tracking-wide">
              UPLOAD YOUR RESUME → GET AI ANALYSIS → DOMINATE YOUR INTERVIEW
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center">
                <div className="brutal-border brutal-shadow p-2 bg-black mr-4">
                  <Upload className="h-6 w-6 text-white" />
                </div>
                UPLOAD RESUME
              </CardTitle>
              <CardDescription className="text-lg font-bold uppercase tracking-wide">
                DROP YOUR PDF → GET INSTANT AI ANALYSIS
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleParse} className="space-y-6">
                <div
                  className={cn(
                    "brutal-border brutal-shadow-lg p-12 text-center transition-all cursor-pointer bg-white",
                    dragActive && "brutal-shadow-xl transform translate-x-1 translate-y-1",
                    file && "bg-green-100 border-green-500"
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
                      <div className="brutal-border brutal-shadow p-3 bg-green-500 mr-4">
                        <FileText className="h-8 w-8 text-white" />
                      </div>
                      <div className="text-left">
                        <p className="text-2xl font-black uppercase">{file.name}</p>
                        <p className="text-lg font-bold text-green-600 uppercase">READY TO ANALYZE!</p>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="brutal-border brutal-shadow-lg p-6 bg-black mx-auto mb-6 w-fit">
                        <Upload className="h-16 w-16 text-white" />
                      </div>
                      <p className="text-3xl font-black uppercase mb-4">DROP PDF HERE</p>
                      <p className="text-xl font-bold uppercase tracking-wide">OR CLICK TO BROWSE</p>
                      <div className="brutal-border brutal-shadow bg-yellow-300 p-2 mt-4 inline-block">
                        <p className="text-sm font-bold uppercase">MAX 10MB • PDF ONLY</p>
                      </div>
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
                      <LoadingSpinner size="sm" className="mr-3" />
                      ANALYZING RESUME...
                    </>
                  ) : (
                    <>
                      <Brain className="h-5 w-5 mr-3" />
                      ANALYZE WITH AI
                    </>
                  )}
                </Button>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="brutal-border brutal-shadow bg-red-100 p-6"
                  >
                    <div className="flex items-center">
                      <div className="brutal-border p-2 bg-red-500 mr-4">
                        <AlertCircle className="h-5 w-5 text-white" />
                      </div>
                      <p className="text-xl font-bold uppercase">{error}</p>
                    </div>
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
            transition={{ delay: 0.4 }}
            className="brutal-bounce"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <div className="brutal-border brutal-shadow p-2 bg-green-500 mr-4">
                    <CheckCircle className="h-6 w-6 text-white" />
                  </div>
                  PROFILE EXTRACTED!
                </CardTitle>
                <CardDescription className="text-lg font-bold uppercase tracking-wide">
                  AI ANALYSIS COMPLETE → REVIEW YOUR DATA
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="brutal-border brutal-shadow p-4 bg-gray-50">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">NAME</label>
                    <p className="text-xl font-bold">{data.name || "—"}</p>
                  </div>
                  <div className="brutal-border brutal-shadow p-4 bg-gray-50">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">EMAIL</label>
                    <p className="text-xl font-bold">{data.email || "—"}</p>
                  </div>
                  <div className="brutal-border brutal-shadow p-4 bg-gray-50">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">PHONE</label>
                    <p className="text-xl font-bold">{data.phone || "—"}</p>
                  </div>
                  <div className="brutal-border brutal-shadow p-4 bg-yellow-200">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">10TH GRADE %</label>
                    <p className="text-xl font-bold">{data.tenth_percentage || "—"}</p>
                  </div>
                  <div className="brutal-border brutal-shadow p-4 bg-yellow-200">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">12TH GRADE %</label>
                    <p className="text-xl font-bold">{data.twelfth_percentage || "—"}</p>
                  </div>
                  <div className="brutal-border brutal-shadow p-4 bg-yellow-200">
                    <label className="text-sm font-black uppercase tracking-wide mb-2 block">DEGREE/CGPA</label>
                    <p className="text-xl font-bold">{data.degree_percentage_or_cgpa || "—"}</p>
                  </div>
                </div>

                {data.experience?.length ? (
                  <div className="brutal-border brutal-shadow-lg p-6 bg-blue-100">
                    <label className="text-lg font-black uppercase tracking-wide mb-4 block">EXPERIENCE</label>
                    <div className="flex flex-wrap gap-3">
                      {data.experience.map((exp, i) => (
                        <Badge key={i} variant="default" className="text-sm">
                          {exp}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                {userId && (
                  <div className="pt-6">
                    <Button
                      onClick={() => navigate("/questions", { state: { userId, parsed: data } })}
                      size="lg"
                      className="w-full text-xl"
                    >
                      CONTINUE TO SKILL ASSESSMENT
                      <div className="brutal-border brutal-shadow p-1 bg-white ml-4">
                        <ArrowRight className="h-5 w-5 text-black" />
                      </div>
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
    <div className="min-h-screen bg-white p-6">
      {saving && <LoadingOverlay text="SELECTING THE BEST QUESTIONS FOR YOU..." />}

      <div className="mx-auto max-w-4xl">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <h1 className="text-6xl font-black uppercase tracking-wider mb-4">SKILL LEVELS</h1>
          <div className="brutal-border brutal-shadow bg-yellow-300 p-4 max-w-2xl mx-auto">
            <p className="text-xl font-bold uppercase tracking-wide">CHOOSE YOUR POWER LEVEL → GET CUSTOM QUESTIONS</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div className="brutal-border brutal-shadow-lg bg-white p-8 mb-8">
            <form onSubmit={onSubmit} className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="brutal-border brutal-shadow p-6 bg-blue-100">
                  <div className="flex items-center mb-6">
                    <div className="brutal-border brutal-shadow p-3 bg-black mr-4">
                      <BarChart3 className="h-8 w-8 text-white" />
                    </div>
                    <h3 className="text-2xl font-black uppercase">APTITUDE</h3>
                  </div>
                  <div className="space-y-3">
                    {["beginner", "intermediate", "advance"].map((level) => (
                      <button key={level} type="button" onClick={() => setAptitude(level)} className={cn("w-full brutal-border brutal-shadow p-4 font-bold uppercase tracking-wide transition-all", aptitude === level ? "bg-black text-white transform translate-x-1 translate-y-1" : "bg-white text-black hover:transform hover:translate-x-0.5 hover:translate-y-0.5")}>{level}</button>
                    ))}
                  </div>
                </div>

                <div className="brutal-border brutal-shadow p-6 bg-green-100">
                  <div className="flex items-center mb-6">
                    <div className="brutal-border brutal-shadow p-3 bg-black mr-4">
                      <Brain className="h-8 w-8 text-white" />
                    </div>
                    <h3 className="text-2xl font-black uppercase">REASONING</h3>
                  </div>
                  <div className="space-y-3">
                    {["beginner", "intermediate", "advance"].map((level) => (
                      <button key={level} type="button" onClick={() => setReasoning(level)} className={cn("w-full brutal-border brutal-shadow p-4 font-bold uppercase tracking-wide transition-all", reasoning === level ? "bg-black text-white transform translate-x-1 translate-y-1" : "bg-white text-black hover:transform hover:translate-x-0.5 hover:translate-y-0.5")}>{level}</button>
                    ))}
                  </div>
                </div>

                <div className="brutal-border brutal-shadow p-6 bg-purple-100">
                  <div className="flex items-center mb-6">
                    <div className="brutal-border brutal-shadow p-3 bg-black mr-4">
                      <Code className="h-8 w-8 text-white" />
                    </div>
                    <h3 className="text-2xl font-black uppercase">CODING</h3>
                  </div>
                  <div className="space-y-3">
                    {["beginner", "intermediate", "advance"].map((level) => (
                      <button key={level} type="button" onClick={() => setCoding(level)} className={cn("w-full brutal-border brutal-shadow p-4 font-bold uppercase tracking-wide transition-all", coding === level ? "bg-black text-white transform translate-x-1 translate-y-1" : "bg-white text-black hover:transform hover:translate-x-0.5 hover:translate-y-0.5")}>{level}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-4 justify-center">
                <button type="button" onClick={() => navigate("/")} className="brutal-btn px-8 py-4 flex items-center text-xl"><ArrowLeft className="h-5 w-5 mr-2" />BACK</button>
                <button type="submit" disabled={saving} className="brutal-btn brutal-btn-primary px-12 py-4 flex items-center text-xl">{saving ? "GENERATING..." : "CONTINUE"}<ArrowRight className="h-5 w-5 ml-2" /></button>
              </div>

              {msg && <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="brutal-border brutal-shadow bg-green-100 p-6 text-center"><p className="text-xl font-bold uppercase text-green-700">{msg}</p></motion.div>}
              {err && <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="brutal-border brutal-shadow bg-red-100 p-6"><div className="flex items-center justify-center"><div className="brutal-border p-2 bg-red-500 mr-4"><AlertCircle className="h-5 w-5 text-white" /></div><p className="text-xl font-bold uppercase">{err}</p></div></motion.div>}
            </form>
          </div>
        </motion.div>

        {ready && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }} className="brutal-bounce">
            <div className="brutal-border brutal-shadow-lg bg-white p-8 text-center">
              <div className="brutal-border brutal-shadow-lg p-6 bg-green-500 mb-6 mx-auto w-fit">
                <CheckCircle className="h-16 w-16 text-white" />
              </div>
              <h2 className="text-4xl font-black uppercase mb-4">PROFILE READY!</h2>
              <p className="text-xl font-bold uppercase tracking-wide mb-8">YOUR PERSONALIZED QUESTION SET IS PREPARED</p>
              <button onClick={toInstructions} className="brutal-btn brutal-btn-primary px-12 py-4 text-xl flex items-center mx-auto">CONTINUE TO INSTRUCTIONS<ArrowRight className="h-5 w-5 ml-3" /></button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}



// -------------------- Instructions Page (/instructions) --------------------

function InstructionsPage() {
  const location = useLocation() as any;
  const navigate = useNavigate();
  const userId: string | undefined = location?.state?.userId;
  return (
    <div className="min-h-screen bg-white p-6">
      <div className="mx-auto max-w-4xl">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <h1 className="text-6xl font-black uppercase tracking-wider mb-4">TEST INSTRUCTIONS</h1>
          <div className="brutal-border brutal-shadow bg-yellow-300 p-4 max-w-2xl mx-auto">
            <p className="text-xl font-bold uppercase tracking-wide">READ CAREFULLY → PREPARE TO DOMINATE</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="space-y-6">
          <div className="brutal-border brutal-shadow-lg bg-white">
            <div className="brutal-border-b-3 border-black p-6">
              <h3 className="text-2xl font-black uppercase flex items-center">
                <div className="brutal-border brutal-shadow p-2 bg-black mr-4">
                  <AlertCircle className="h-6 w-6 text-white" />
                </div>
                GENERAL GUIDELINES
              </h3>
            </div>
            <div className="p-6">
              <ul className="space-y-3 text-lg">
                <li className="flex items-start"><span className="brutal-border brutal-shadow p-2 bg-black text-white font-bold mr-3 mt-1">→</span><span>Ensure a stable internet connection</span></li>
                <li className="flex items-start"><span className="brutal-border brutal-shadow p-2 bg-black text-white font-bold mr-3 mt-1">→</span><span>Do NOT refresh the page during the test</span></li>
                <li className="flex items-start"><span className="brutal-border brutal-shadow p-2 bg-black text-white font-bold mr-3 mt-1">→</span><span>Keep your device charged</span></li>
              </ul>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="brutal-border brutal-shadow-lg bg-blue-50 p-6">
              <h3 className="text-2xl font-black uppercase mb-4">APTITUDE</h3>
              <p className="font-bold">10 questions • Multiple choice • Choose the best answer</p>
            </div>
            <div className="brutal-border brutal-shadow-lg bg-green-50 p-6">
              <h3 className="text-2xl font-black uppercase mb-4">REASONING</h3>
              <p className="font-bold">10 questions • Analytical and logical skills</p>
            </div>
            <div className="brutal-border brutal-shadow-lg bg-purple-50 p-6">
              <h3 className="text-2xl font-black uppercase mb-4">CODING</h3>
              <p className="font-bold">10 questions • Fundamentals and problem-solving</p>
            </div>
          </div>

          <div className="brutal-border brutal-shadow-lg bg-red-50 p-6">
            <h3 className="text-2xl font-black uppercase flex items-center text-red-700 mb-4">
              <Clock className="h-6 w-6 mr-2" />IMPORTANT NOTES
            </h3>
            <ul className="space-y-3 text-lg font-bold">
              <li className="flex items-start"><span className="text-red-600 mr-3">⚠</span><span>The timer (30 minutes) starts once you begin</span></li>
              <li className="flex items-start"><span className="text-red-600 mr-3">⚠</span><span>You CANNOT pause the test once started</span></li>
              <li className="flex items-start"><span className="text-red-600 mr-3">⚠</span><span>Submit before time runs out to save answers</span></li>
            </ul>
          </div>

          <div className="brutal-border-thick brutal-shadow-xl bg-green-100 p-8 text-center">
            <h3 className="text-3xl font-black uppercase mb-4">READY TO START?</h3>
            <p className="text-xl font-bold mb-8">Once you click START TEST, the timer will begin and cannot be paused.</p>
            <div className="flex gap-4 justify-center">
              <button onClick={() => navigate("/questions", { state: { userId, parsed: location?.state?.parsed } })} className="brutal-btn px-8 py-4 flex items-center text-xl"><ArrowLeft className="h-5 w-5 mr-2" />BACK</button>
              <button onClick={() => navigate("/test", { state: { userId, selected: location?.state?.selected, parsed: location?.state?.parsed } })} className="brutal-btn brutal-btn-primary px-12 py-4 flex items-center text-2xl">START TEST<ArrowRight className="h-5 w-5 ml-3" /></button>
            </div>
          </div>
        </motion.div>
      </div>
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
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="brutal-border brutal-shadow-lg bg-white p-8 text-center max-w-md">
          <div className="brutal-border p-4 bg-red-500 mb-6 mx-auto w-fit">
            <AlertCircle className="h-12 w-12 text-white" />
          </div>
          <h2 className="text-2xl font-black uppercase mb-4">NO TEST LOADED</h2>
          <p className="text-lg font-bold mb-6">Please go back and select your skill levels.</p>
          <button className="brutal-btn brutal-btn-primary px-8 py-3 w-full" onClick={() => navigate("/questions")}>BACK TO SKILLS</button>
        </div>
      </div>
    );
  }

  const currentQ = flat[current];
  const answeredCount = Object.keys(answers).length;
  const progress = total ? (answeredCount / total) * 100 : 0;

  if (result) {
    return (
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <LoadingOverlay text="SUBMITTING TEST..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="brutal-border brutal-shadow-lg bg-white p-4 mb-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center">
            <div className="brutal-border p-2 bg-black mr-3">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <span className="text-xl font-black uppercase">AI ASSESSMENT</span>
          </div>

          <div className="flex-1 w-full md:mx-8">
            <div className="flex justify-between text-sm font-bold uppercase mb-1">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="brutal-progress h-4 w-full">
              <div className="brutal-progress-bar h-full" style={{ width: `${progress}%` }}></div>
            </div>
          </div>

          <div className="flex items-center">
            <div className="brutal-border p-2 bg-yellow-300 mr-3">
              <Clock className="h-6 w-6 text-black" />
            </div>
            <span className="text-xl font-black font-mono">
              {String(Math.floor(remaining / 60)).padStart(2, "0")}:{String(remaining % 60).padStart(2, "0")}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Question Panel */}
          <div className="lg:col-span-2">
            <div className="brutal-border brutal-shadow-lg bg-white h-full flex flex-col">
              <div className="brutal-border-b-3 border-black p-6 bg-gray-50 flex justify-between items-center">
                <span className="font-black uppercase text-lg">QUESTION {current + 1} OF {total}</span>
                <span className="brutal-border px-3 py-1 bg-black text-white text-sm font-bold uppercase">{currentQ.domain}</span>
              </div>

              <div className="p-8 flex-1">
                <h3 className="text-2xl font-bold mb-8 leading-relaxed">{currentQ?.q?.question || ""}</h3>

                <div className="space-y-4">
                  {(currentQ?.q?.options || []).map((opt: string, i: number) => {
                    const checked = answers[currentQ.id] === opt;
                    return (
                      <label
                        key={i}
                        className={cn(
                          "block brutal-border p-4 cursor-pointer transition-all hover:translate-x-1 hover:translate-y-1",
                          checked ? "bg-black text-white shadow-none translate-x-1 translate-y-1" : "bg-white hover:bg-gray-50 brutal-shadow"
                        )}
                      >
                        <div className="flex items-center">
                          <div className={cn(
                            "w-6 h-6 border-2 mr-4 flex items-center justify-center",
                            checked ? "border-white bg-white" : "border-black"
                          )}>
                            {checked && <div className="w-3 h-3 bg-black" />}
                          </div>
                          <input
                            type="radio"
                            name={currentQ.id}
                            value={opt}
                            checked={checked}
                            onChange={(e) => setAnswers((prev) => ({ ...prev, [currentQ.id]: e.target.value }))}
                            className="hidden"
                          />
                          <span className="text-lg font-bold">{opt}</span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="p-6 border-t-3 border-black bg-gray-50 flex justify-between">
                <button
                  className="brutal-btn px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={current === 0}
                  onClick={() => setCurrent((c) => Math.max(0, c - 1))}
                >
                  PREVIOUS
                </button>
                {current < total - 1 ? (
                  <button
                    className="brutal-btn brutal-btn-primary px-8 py-3"
                    onClick={() => setCurrent((c) => Math.min(total - 1, c + 1))}
                  >
                    NEXT
                  </button>
                ) : (
                  <button
                    className="brutal-btn bg-green-500 text-white px-8 py-3 hover:bg-green-600"
                    onClick={handleSubmit}
                  >
                    SUBMIT TEST
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Navigation Panel */}
          <div className="lg:col-span-1">
            <div className="brutal-border brutal-shadow-lg bg-white p-6">
              <h3 className="text-xl font-black uppercase mb-6 flex items-center">
                <div className="w-3 h-3 bg-black mr-2"></div>
                QUESTION NAVIGATOR
              </h3>

              <div className="grid grid-cols-5 gap-3 mb-8">
                {flat.map((f, idx) => {
                  const isCurrent = idx === current;
                  const isAnswered = !!answers[f.id];
                  return (
                    <button
                      key={f.id}
                      className={cn(
                        "aspect-square font-bold border-2 border-black transition-all text-sm",
                        isCurrent ? "bg-black text-white transform scale-110" :
                          isAnswered ? "bg-green-500 text-white" : "bg-white hover:bg-gray-100"
                      )}
                      onClick={() => setCurrent(idx)}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>

              <div className="space-y-3 border-t-3 border-black pt-6">
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-green-500 border-2 border-black mr-3"></div>
                  <span className="font-bold uppercase text-sm">ANSWERED</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-white border-2 border-black mr-3"></div>
                  <span className="font-bold uppercase text-sm">UNANSWERED</span>
                </div>
                <div className="flex items-center">
                  <div className="w-4 h-4 bg-black border-2 border-black mr-3"></div>
                  <span className="font-bold uppercase text-sm">CURRENT</span>
                </div>
              </div>

              <div className="mt-8 pt-6 border-t-3 border-black">
                <h4 className="font-black uppercase mb-3 text-sm">SECTIONS</h4>
                <div className="space-y-2 text-sm font-bold text-gray-600">
                  <div className="flex justify-between"><span>APTITUDE</span><span>1–10</span></div>
                  <div className="flex justify-between"><span>REASONING</span><span>11–20</span></div>
                  <div className="flex justify-between"><span>CODING</span><span>21–30</span></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// -------------------- Results Page (/results) --------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="brutal-border brutal-shadow-lg bg-white mb-8">
      <div className="brutal-border-b-3 border-black p-4 bg-gray-50">
        <h2 className="text-2xl font-black uppercase">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
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
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="brutal-border brutal-shadow-lg bg-white p-8 text-center">
          <p className="text-xl font-bold uppercase mb-6">No report data available.</p>
          <button className="brutal-btn brutal-btn-primary px-8 py-3" onClick={() => navigate("/")}>HOME</button>
        </div>
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
  const avg = (arr: number[]) => arr.length ? Math.round(((arr.reduce((s: number, v: number) => s + v, 0)) / arr.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-white p-6">
      {loading && <LoadingOverlay text="GENERATING YOUR PERSONALIZED REPORT..." />}

      <div className="mx-auto max-w-5xl">
        <header className="text-center mb-12">
          <div className="inline-block brutal-border brutal-shadow bg-black p-4 mb-6">
            <h1 className="text-4xl md:text-6xl font-black uppercase text-white tracking-wider">CAREER & SKILL<br />DEVELOPMENT REPORT</h1>
          </div>
          <div className="brutal-border brutal-shadow bg-yellow-300 p-4 max-w-3xl mx-auto">
            <p className="text-xl font-bold uppercase tracking-wide">A PERSONALIZED ANALYSIS BASED ON YOUR TEST PERFORMANCE AND ACADEMIC PROFILE</p>
          </div>
        </header>

        {llmMd ? (
          <section className="brutal-border brutal-shadow-lg bg-white mb-8">
            <div className="brutal-border-b-3 border-black p-4 bg-blue-100 flex justify-between items-center">
              <h2 className="text-2xl font-black uppercase flex items-center">
                <div className="brutal-border p-2 bg-black mr-3">
                  <Brain className="h-6 w-6 text-white" />
                </div>
                AI INSIGHTS
              </h2>
              <button className="brutal-btn text-sm px-4 py-2" onClick={fetchLLM}>REGENERATE</button>
            </div>
            <div className="p-8 prose prose-lg max-w-none font-mono">
              <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{llmMd}</div>
            </div>
          </section>
        ) : null}

        {llmErr && (
          <section className="brutal-border brutal-shadow bg-red-100 p-6 mb-8">
            <div className="flex items-center text-red-700 font-bold uppercase">
              <AlertCircle className="h-6 w-6 mr-3" />
              {llmErr}
            </div>
          </section>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <Section title="Performance Analysis">
            <ul className="space-y-4 font-bold text-lg">
              <li className="flex justify-between border-b-2 border-black pb-2">
                <span>TOTAL SCORE</span>
                <span className="bg-black text-white px-2">{totals.overall} / {totals.totalQuestions} ({behavior.accuracy}%)</span>
              </li>
              <li className="flex justify-between border-b-2 border-black pb-2">
                <span>APTITUDE</span>
                <span>{totals.aptitude} / {domainTotals.aptitude} ({pct(totals.aptitude, domainTotals.aptitude)}%)</span>
              </li>
              <li className="flex justify-between border-b-2 border-black pb-2">
                <span>REASONING</span>
                <span>{totals.reasoning} / {domainTotals.reasoning} ({pct(totals.reasoning, domainTotals.reasoning)}%)</span>
              </li>
              <li className="flex justify-between border-b-2 border-black pb-2">
                <span>CODING</span>
                <span>{totals.coding} / {domainTotals.coding} ({pct(totals.coding, domainTotals.coding)}%)</span>
              </li>
              <li className="flex justify-between border-b-2 border-black pb-2">
                <span>CONSISTENCY</span>
                <span>{behavior.consistency}</span>
              </li>
              <li className="pt-2">
                <div className="text-sm uppercase mb-2">BY DIFFICULTY</div>
                <div className="flex gap-2 text-sm">
                  <span className="bg-green-100 border-2 border-black px-2 py-1">EASY: {avg(easyAcc)}%</span>
                  <span className="bg-yellow-100 border-2 border-black px-2 py-1">MID: {avg(midAcc)}%</span>
                  <span className="bg-red-100 border-2 border-black px-2 py-1">HARD: {avg(hardAcc)}%</span>
                </div>
              </li>
            </ul>
          </Section>

          <Section title="Skill Gap Analysis">
            <ul className="space-y-4 text-lg">
              {strengths.length ? (
                <li className="bg-green-50 border-2 border-black p-3">
                  <strong className="block uppercase text-green-800 mb-1">Strengths</strong>
                  {strengths.join(", ")}
                </li>
              ) : null}
              {weaknesses.length ? (
                <li className="bg-red-50 border-2 border-black p-3">
                  <strong className="block uppercase text-red-800 mb-1">Weaknesses</strong>
                  {weaknesses.join(", ")}
                </li>
              ) : null}
              <li className="flex items-start"><span className="mr-2">→</span>Entry-level benchmark alignment: solidify quantitative basics, structured reasoning, and core CS fundamentals.</li>
              <li className="flex items-start"><span className="mr-2">→</span>Differentiate between conceptual clarity and error-carefulness by reviewing wrong answers with explanations.</li>
            </ul>
          </Section>
        </div>

        <Section title="Personalized 6-Week Improvement Plan">
          <ol className="space-y-4 text-lg list-decimal list-inside font-bold">
            <li className="pl-2">Weeks 1–2: Quantitative basics (percentages, ratios, arithmetic) • Daily 30 MCQs • Resource: GFG Aptitude, Khan Academy.</li>
            <li className="pl-2">Weeks 1–2 (Parallel): Reasoning (series, syllogisms, seating, data sufficiency) • Daily 20 MCQs • Resource: IndiaBix Reasoning.</li>
            <li className="pl-2">Weeks 3–4: Coding fundamentals (time/space, arrays, strings, hashing) • 3 problems/day • Resource: LeetCode Easy/Medium.</li>
            <li className="pl-2">Week 4: OOPs, DBMS, OS quick notes • 1 hr/day • Resource: InterviewBit CS notes.</li>
            <li className="pl-2">Weeks 5–6: Mixed mocks: 30Q timed sets • Post-test error log • Target accuracy +10%.</li>
            <li className="pl-2">Routine: 60–90 mins daily • Review all wrong answers same day • Maintain a mistakes journal.</li>
          </ol>
        </Section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <Section title="Career Guidance">
            <ul className="space-y-3 text-lg">
              <li className="flex items-start"><span className="bg-black text-white px-2 mr-2 text-sm mt-1">DEV</span><span><strong>Full‑stack / Frontend:</strong> Good fit if UI and JS fundamentals appeal. Improve DSA basics and project depth.</span></li>
              <li className="flex items-start"><span className="bg-black text-white px-2 mr-2 text-sm mt-1">DATA</span><span><strong>Data Analytics:</strong> Consider if quantitative accuracy trends up. Learn Excel→SQL→Python→Tableau pipeline.</span></li>
              <li className="flex items-start"><span className="bg-black text-white px-2 mr-2 text-sm mt-1">QA</span><span><strong>QA / SDET Foundations:</strong> Strong for detail-oriented profiles. Learn testing frameworks and automation basics.</span></li>
              <li className="flex items-start"><span className="bg-black text-white px-2 mr-2 text-sm mt-1">BIZ</span><span><strong>Business Analyst (Tech):</strong> Blend of reasoning + communication. Practice case studies and SQL basics.</span></li>
              <li className="flex items-start"><span className="bg-black text-white px-2 mr-2 text-sm mt-1">OPS</span><span><strong>DevOps Foundations:</strong> If systems interest you. Learn Linux, Git, CI/CD basics; scripting fundamentals.</span></li>
            </ul>
            <p className="mt-4 text-sm font-bold border-t-2 border-black pt-2">Why: choices align with current strengths and offer clear upskilling paths. Focus on closing core gaps noted above.</p>
          </Section>

          <Section title="Internship Recommendations">
            <ul className="space-y-3 text-lg">
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>Frontend / React Intern • Emphasize projects, responsive UI, component patterns.</li>
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>Full‑stack MERN Intern • Showcase CRUD apps, auth, and API design.</li>
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>QA / Automation Intern • Demonstrate test cases, Cypress/Selenium basics.</li>
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>Data Analyst Intern • Highlight Excel/SQL, small dashboards, EDA notebooks.</li>
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>Business Analyst Intern • Requirements drafting, wireframes, stakeholder docs.</li>
              <li className="flex items-center"><div className="w-2 h-2 bg-black mr-3"></div>DevOps Intern • Docker basics, CI/CD toy pipeline, IaC curiosity.</li>
            </ul>
            <p className="mt-4 text-sm font-bold border-t-2 border-black pt-2">Target startups and mid-size firms for broader exposure; tailor resume to measurable outcomes and projects.</p>
          </Section>
        </div>

        <Section title="Final Summary">
          <p className="text-xl leading-relaxed">
            Overall level: <strong className="bg-yellow-300 px-2">{behavior.accuracy >= 80 ? "Excellent" : behavior.accuracy >= 60 ? "Strong" : behavior.accuracy >= 40 ? "Average" : behavior.accuracy >= 20 ? "Developing" : "Critical Attention Needed"}</strong>.
            Strongest opportunity: <strong>{strengths[0] || "foundation building"}</strong>.
            Critical first fixes: <strong>{weaknesses.slice(0, 2).join(", ") || "reinforce fundamentals"}</strong>.
            Keep a steady routine, track mistakes, and expect visible improvement within 6–8 weeks.
          </p>
        </Section>

        {profile && (
          <Section title="Academic Profile (Provided)">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div className="brutal-border p-4 bg-gray-50">
                <div className="text-sm font-bold uppercase mb-1">10TH GRADE</div>
                <div className="text-xl font-black">{profile.tenth_percentage || "—"}</div>
              </div>
              <div className="brutal-border p-4 bg-gray-50">
                <div className="text-sm font-bold uppercase mb-1">12TH GRADE</div>
                <div className="text-xl font-black">{profile.twelfth_percentage || "—"}</div>
              </div>
              <div className="brutal-border p-4 bg-gray-50">
                <div className="text-sm font-bold uppercase mb-1">DEGREE/CGPA</div>
                <div className="text-xl font-black">{profile.degree_percentage_or_cgpa || "—"}</div>
              </div>
            </div>
          </Section>
        )}

        <div className="flex justify-center mt-12 mb-12">
          <button className="brutal-btn brutal-btn-primary text-2xl px-12 py-6" onClick={() => navigate("/")}>FINISH & RETURN HOME</button>
        </div>
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

