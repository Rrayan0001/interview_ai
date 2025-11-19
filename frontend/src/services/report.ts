// Get backend URL - use Railway in production, localhost in dev
const getApiUrl = () => {
  const envUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
  if (import.meta.env.PROD) {
    // Force Railway if env var is missing or points to localhost
    if (!envUrl || envUrl.includes("localhost")) {
      return "https://web-production-dad96.up.railway.app";
    }
    return envUrl;
  }
  return envUrl || "http://localhost:8000";
};

const API_URL = getApiUrl();

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

