const API_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export const generateReport = async (data: any) => {
  const res = await fetch(`${API_URL}/generate-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`Report generation failed: ${res.statusText}`);
  }

  return res.json();
};

