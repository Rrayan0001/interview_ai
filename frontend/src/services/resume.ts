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

export const uploadResume = async (file: File, cleanup: boolean = true) => {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_URL}/upload-resume?cleanup=${cleanup}`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.statusText}`);
  }

  return res.json();
};

