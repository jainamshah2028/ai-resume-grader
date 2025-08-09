import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import io
import hashlib
import re
import time

# Lazy imports for better performance
@st.cache_resource
def load_dependencies():
    """Load heavy dependencies only when needed"""
    try:
        import fitz  # PyMuPDF for PDF processing
        import spacy  # Natural language processing
        import docx  # Python-docx for DOCX files
        return fitz, spacy, docx
    except ImportError as e:
        missing_lib = str(e).split("'")[1] if "'" in str(e) else "unknown"
        st.error(f"""
        **Missing Required Package: {missing_lib}**
        
        Please install the missing package:
        ```bash
        pip install {missing_lib}
        ```
        
        Or install all requirements:
        ```bash
        pip install -r requirements.txt
        ```
        """)
        return None, None, None

# Optimized spaCy model loading with better caching
@st.cache_resource
def load_spacy_model():
    """Load spaCy model with optimized settings for speed"""
    try:
        _, spacy, _ = load_dependencies()
        if spacy is None:
            return None
        
        # Load model with only essential components for speed
        nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        return nlp
    except OSError:
        st.error("⚠️ spaCy model not found. Please install it by running: python -m spacy download en_core_web_sm")
        return None
    except Exception as e:
        st.error(f"Error loading spaCy model: {e}")
        return None

# Page configuration
st.set_page_config(
    page_title="AI Resume Grader",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processed_resume' not in st.session_state:
    st.session_state.processed_resume = None
if 'processed_jd' not in st.session_state:
    st.session_state.processed_jd = None

# Basic styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #667eea;
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    
    .upload-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    career_level = st.selectbox(
        "Experience Level",
        ["Student/Fresher", "Entry Level (0-2 years)", "Mid Level (2-5 years)", "Senior Level (5+ years)"]
    )

# Main header
st.markdown('<div class="main-header"><h1>🧾 AI Resume Grader</h1><p>Get AI-powered analysis of your resume against job requirements</p></div>', unsafe_allow_html=True)

# Create columns
col1, col2 = st.columns([1, 1], gap="large")

# Helper functions
def get_text_hash(text):
    """Generate hash for text to check if it changed"""
    return hashlib.md5(text.encode()).hexdigest()

@st.cache_data
def extract_text_from_pdf(file_bytes, file_name):
    """Extract text from PDF file with caching"""
    fitz, _, _ = load_dependencies()
    if fitz is None:
        return ""
    
    text = ""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
    return text

@st.cache_data
def extract_text_from_docx(file_bytes, file_name):
    """Extract text from DOCX file with caching"""
    _, _, docx = load_dependencies()
    if docx is None:
        return ""
    
    text = ""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        st.error(f"Failed to read DOCX: {e}")
    return text

@st.cache_data
def extract_keywords_cached(text, min_length=3):
    """Extract keywords with caching for better performance"""
    nlp = load_spacy_model()
    if nlp is None:
        # Fallback to simple word extraction if spaCy fails
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        return set(word for word in words if len(word) >= min_length and word not in stopwords)
    
    doc = nlp(text.lower())
    keywords = set()
    for token in doc:
        if (not token.is_stop 
            and not token.is_punct 
            and not token.like_num 
            and len(token.lemma_) >= min_length
            and token.is_alpha
            and not token.is_space):
            keywords.add(token.lemma_.lower())
    return keywords

def create_score_visualization(score):
    """Create a gauge chart for the score"""
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': "Match Score %"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "green"}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90}}))
    
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# Resume Upload Section
with col1:
    st.markdown('<div class="upload-section"><h3>📄 Upload Resume</h3><p>Supported: PDF, DOCX, TXT (Max 10MB)</p></div>', unsafe_allow_html=True)
    
    uploaded_resume = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "txt", "docx"],
        help="Supported formats: PDF, TXT, DOCX (Max size: 10MB)"
    )
    
    if uploaded_resume:
        if uploaded_resume.size > 10 * 1024 * 1024:
            st.error("❌ File size too large! Please upload a file smaller than 10MB.")
        else:
            st.success(f"✅ File uploaded: {uploaded_resume.name}")
            
            # Process file
            file_bytes = uploaded_resume.read()
            
            if uploaded_resume.type == "application/pdf":
                resume_text = extract_text_from_pdf(file_bytes, uploaded_resume.name)
            elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                resume_text = extract_text_from_docx(file_bytes, uploaded_resume.name)
            else:
                resume_text = file_bytes.decode("utf-8", errors="ignore")
            
            st.session_state.processed_resume = resume_text
            
            if st.checkbox("📖 Preview uploaded file"):
                st.text_area("File Content Preview", 
                           resume_text[:500] + "..." if len(resume_text) > 500 else resume_text, 
                           height=200, disabled=True)

# Job Description Section
with col2:
    st.markdown('<div class="upload-section"><h3>💼 Job Description</h3><p>Paste the complete job posting for analysis</p></div>', unsafe_allow_html=True)
    
    job_description = st.text_area(
        "Paste the job description here",
        height=200,
        placeholder="Copy and paste the complete job posting here..."
    )
    
    if job_description:
        word_count = len(job_description.split())
        st.info(f"📊 {word_count} words entered")
        st.session_state.processed_jd = job_description

# Analysis Section
if st.session_state.processed_resume and st.session_state.processed_jd:
    st.markdown("---")
    st.markdown("## 🔍 Analysis Results")
    
    resume_text = st.session_state.processed_resume
    job_desc_text = st.session_state.processed_jd
    
    if resume_text.strip():
        with st.spinner("🔬 Analyzing skill match..."):
            # Extract keywords
            resume_keywords = extract_keywords_cached(resume_text, 3)
            jd_keywords = extract_keywords_cached(job_desc_text, 3)
            
            # Calculate matches
            matched_keywords = resume_keywords.intersection(jd_keywords)
            missing_keywords = jd_keywords - resume_keywords
            match_score = round(len(matched_keywords) / len(jd_keywords) * 100, 2) if jd_keywords else 0.0
        
        # Results Layout
        result_col1, result_col2 = st.columns([1, 1])
        
        with result_col1:
            st.markdown("### 🎯 Match Score")
            st.plotly_chart(create_score_visualization(match_score), use_container_width=True)
            
            # Statistics
            st.markdown("### 📊 Statistics")
            st.metric("Resume Keywords", len(resume_keywords))
            st.metric("Job Requirements", len(jd_keywords))
            st.metric("Matched Keywords", len(matched_keywords))
            st.metric("Missing Keywords", len(missing_keywords))
        
        with result_col2:
            st.markdown("### 🎯 Score Interpretation")
            if match_score >= 80:
                st.success("🌟 Excellent match! Your resume aligns well with the job requirements.")
            elif match_score >= 60:
                st.warning("✨ Good match! Consider adding a few more relevant keywords.")
            elif match_score >= 40:
                st.warning("💡 Fair match. Your resume could benefit from more relevant keywords.")
            else:
                st.error("🔄 Low match. Consider significantly updating your resume to better align with the job requirements.")
        
        # Detailed Analysis
        st.markdown("---")
        analysis_col1, analysis_col2 = st.columns([1, 1])
        
        with analysis_col1:
            if matched_keywords:
                st.markdown("### ✅ Matched Skills")
                matched_list = sorted(list(matched_keywords))
                for keyword in matched_list[:20]:  # Show first 20
                    st.markdown(f"• {keyword}")
                
                if len(matched_list) > 20:
                    st.info(f"... and {len(matched_list) - 20} more")
        
        with analysis_col2:
            if missing_keywords:
                st.markdown("### ⚠️ Missing Skills")
                missing_list = sorted(list(missing_keywords))
                for keyword in missing_list[:20]:  # Show first 20
                    st.markdown(f"• {keyword}")
                
                if len(missing_list) > 20:
                    st.info(f"... and {len(missing_list) - 20} more")

# Footer
st.markdown("---")
st.markdown("""
<div style='margin-top: 3rem; padding: 2rem; 
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); 
            color: white; border-radius: 20px; text-align: center;'>
    <div style='margin-bottom: 1.5rem;'>
        <h3 style='margin: 0 0 0.5rem 0; font-weight: 600;'>🧾 AI Resume Grader</h3>
        <p style='margin: 0; opacity: 0.9; font-size: 0.95rem;'>
            Helping job seekers optimize their resumes with AI-powered analysis
        </p>
    </div>
    
    <div style='display: flex; justify-content: center; gap: 2rem; margin: 1.5rem 0; flex-wrap: wrap;'>
        <div style='text-align: center;'>
            <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>📊</div>
            <strong>Smart Analysis</strong><br>
            <small style='opacity: 0.8;'>AI-powered keyword matching</small>
        </div>
        <div style='text-align: center;'>
            <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>🎓</div>
            <strong>Student Friendly</strong><br>
            <small style='opacity: 0.8;'>Special features for freshers</small>
        </div>
        <div style='text-align: center;'>
            <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>🚀</div>
            <strong>Career Growth</strong><br>
            <small style='opacity: 0.8;'>Learning recommendations</small>
        </div>
        <div style='text-align: center;'>
            <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>📥</div>
            <strong>Export Results</strong><br>
            <small style='opacity: 0.8;'>Download analysis reports</small>
        </div>
    </div>
    
    <div style='border-top: 1px solid rgba(255,255,255,0.2); padding-top: 1rem; margin-top: 1rem;'>
        <p style='margin: 0; font-size: 0.9rem; opacity: 0.8;'>
            Made with ❤️ using Streamlit, spaCy, and Plotly | 
            <a href="https://github.com/jainamshah2028/ai-resume-grader" target="_blank" 
               style='color: #74b9ff; text-decoration: none;'>
                View on GitHub
            </a> | 
            Version 2.0
        </p>
    </div>
</div>
""", unsafe_allow_html=True)
