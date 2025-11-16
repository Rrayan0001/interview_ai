import os
import tempfile
import streamlit as st
import requests
import json

st.set_page_config(page_title="Resume Parser (Backend-only)", page_icon="📄", layout="centered")
st.title("📄 Resume Parser")
st.caption("Upload a resume PDF → backend-only Groq parsing → minimal fields only")

with st.sidebar:
    st.header("Settings")
    st.info("Groq API key is stored server-side only.")
    backend_url = st.text_input("Backend URL", value="http://localhost:8000", help="FastAPI server URL")
    use_cleanup = st.checkbox("LLM cleanup before parsing", value=False)

uploaded_file = st.file_uploader("Upload PDF (resume/CV)", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    try:
        with st.spinner("Parsing on backend..."):
            files = {"pdf": open(tmp_path, "rb")}
            params = {"cleanup": str(use_cleanup).lower()}
            try:
                resp = requests.post(f"{backend_url}/parse", files=files, params=params, timeout=120)
            finally:
                files["pdf"].close()
            if not resp.ok:
                st.error(f"Backend error {resp.status_code}: {resp.text}")
            else:
                data = resp.json()
                st.subheader("Extracted Fields")
                st.write(f"• Name: {data.get('name','')}")
                st.write(f"• Email: {data.get('email','')}")
                st.write(f"• Phone: {data.get('phone','')}")
                st.write(f"• 10th Percentage: {data.get('tenth_percentage','')}")
                st.write(f"• 12th Percentage: {data.get('twelfth_percentage','')}")
                st.write(f"• Degree Percentage/CGPA: {data.get('degree_percentage_or_cgpa','')}")
                exp = data.get("experience") or []
                if exp:
                    st.write("• Experience:")
                    for line in exp:
                        st.write(f"  - {line}")
                st.download_button(
                    "Download Minimal JSON",
                    json.dumps(data, indent=2),
                    file_name="resume_parsed_minimal.json",
                    mime="application/json",
                )
        st.success("Done.")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

st.markdown("---")
st.caption("Backend: FastAPI on port 8000. Frontend: Streamlit on port 1300.")


