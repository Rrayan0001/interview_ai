// Get backend URL
const getApiUrl = () => {
  // In Vercel, use relative path to hit the serverless function
  if (import.meta.env.PROD) {
    return "/api";
  }
  return import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
};

const API_URL = getApiUrl();

export const evaluateCandidate = async (data: any) => {
  const res = await fetch(`${API_URL}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Evaluation failed: ${res.statusText}`);
  }

  return res.json();
};

