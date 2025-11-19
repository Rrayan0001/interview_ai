const API_URL = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "http://localhost:8000";

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

