// Get backend URL
const getApiUrl = () => {
  // In Vercel, use relative path to hit the serverless function
  if (import.meta.env.PROD) {
    return "/api";
  }
  return import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
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

