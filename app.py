
import fitz
import streamlit as st # type: ignore
import spacy # type: ignore

# app.py
import io
# Import necessary libraries
import os

# Load OpenAI API key from environment variable or set it here (not recommended for production)
# For production, set this as an environment variable: export OPENAI_API_KEY="your_api_key"
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY"  # Replace with your OpenAI API key or use environment variable
# Ensure the necessary models are downloaded
if not os.path.exists("en_core_web_sm"):
    import spacy.cli # type: ignore
    spacy.cli.download("en_core_web_sm")        

st.set_page_config(page_title="AI Resume Grader", layout="wide")
st.title("🧾 AI Resume Grader")

st.markdown("Upload your resume and job description to get a skill match score.")

uploaded_resume = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
job_description = st.text_area("Paste Job Description")

def extract_keywords(doc):
    return set([
        token.lemma_.lower() for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.like_num
        and len(token.lemma_) > 2
        and token.is_alpha
    ])

def extract_text_from_pdf(file):
    text = ""
    try:
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
    return text

if uploaded_resume and job_description:
    nlp = spacy.load("en_core_web_sm")

    if uploaded_resume.type == "application/pdf":
        resume_text = extract_text_from_pdf(uploaded_resume)
    else:
        resume_text = uploaded_resume.read().decode("utf-8", errors="ignore")

    if not resume_text.strip():
        st.warning("Could not extract text from the resume. Please try a different file.")
    else:
        resume_doc = nlp(resume_text.lower())
        jd_doc = nlp(job_description.lower())

        resume_tokens = extract_keywords(resume_doc)
        jd_tokens = extract_keywords(jd_doc)

        matched = resume_tokens.intersection(jd_tokens)
        match_score = round(len(matched) / len(jd_tokens) * 100, 2) if jd_tokens else 0.0

        st.markdown(f"### ✅ Skill Match Score: {match_score}%")
        if matched:
            st.markdown("#### ✅ Matched Keywords:")
            st.write(", ".join(sorted(matched)))
        else:
            st.warning("No matching keywords found.")
