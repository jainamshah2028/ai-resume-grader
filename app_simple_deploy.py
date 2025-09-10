import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
import time

# Simple text processing without heavy dependencies for fallback
def simple_text_processing(text):
    """Basic text processing without spaCy"""
    if not text:
        return []
    
    # Basic keyword extraction using regex
    text = text.lower()
    # Remove common words
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
    
    # Extract words that look like skills/keywords
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    # Return unique keywords
    return list(set(keywords))

# Lazy loading function
@st.cache_resource
def load_dependencies():
    """Load heavy dependencies only when needed"""
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
            return spacy, nlp, True
        except OSError:
            # Model not found, try to use blank model
            nlp = spacy.blank("en")
            return spacy, nlp, False
    except ImportError:
        return None, None, False

@st.cache_resource
def load_file_processors():
    """Load file processing libraries"""
    processors = {}
    try:
        import fitz  # PyMuPDF
        processors['pdf'] = fitz
    except ImportError:
        processors['pdf'] = None
    
    try:
        from docx import Document
        processors['docx'] = Document
    except ImportError:
        processors['docx'] = None
    
    return processors

def extract_text_from_file(uploaded_file):
    """Extract text from uploaded file with fallback options"""
    try:
        processors = load_file_processors()
        
        if uploaded_file.type == "application/pdf":
            if processors['pdf']:
                # Use PyMuPDF if available
                pdf_document = processors['pdf'].open(stream=uploaded_file.read(), filetype="pdf")
                text = ""
                for page in pdf_document:
                    text += page.get_text()
                pdf_document.close()
                return text
            else:
                st.error("PDF processing not available. Please upload a TXT file.")
                return ""
                
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if processors['docx']:
                # Use python-docx if available
                doc = processors['docx'](uploaded_file)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            else:
                st.error("DOCX processing not available. Please upload a TXT file.")
                return ""
                
        elif uploaded_file.type == "text/plain":
            # Text files are always supported
            return str(uploaded_file.read(), "utf-8")
        else:
            st.error("Unsupported file type. Please upload PDF, DOCX, or TXT.")
            return ""
            
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""

def extract_keywords(text):
    """Extract keywords with fallback to simple processing"""
    spacy_lib, nlp, has_model = load_dependencies()
    
    if spacy_lib and nlp:
        try:
            # Use spaCy if available
            doc = nlp(text.lower())
            keywords = []
            for token in doc:
                if (token.is_alpha and 
                    len(token.text) > 2 and 
                    not token.is_stop and 
                    not token.is_punct):
                    keywords.append(token.lemma_)
            return list(set(keywords))
        except Exception:
            # Fall back to simple processing
            return simple_text_processing(text)
    else:
        # Use simple processing
        return simple_text_processing(text)

def calculate_match_score(resume_keywords, jd_keywords):
    """Calculate match score between resume and job description"""
    if not jd_keywords:
        return 0.0, set(), set()
    
    resume_set = set(resume_keywords)
    jd_set = set(jd_keywords)
    
    matched = resume_set.intersection(jd_set)
    missing = jd_set - resume_set
    
    match_percentage = (len(matched) / len(jd_set)) * 100 if jd_set else 0
    
    return round(match_percentage, 1), matched, missing

# Page configuration
st.set_page_config(
    page_title="AI Resume Grader",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        color: white;
    }
    
    .upload-section.resume {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
    }
    
    .upload-section.job-desc {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border: 2px solid rgba(245, 87, 108, 0.3);
    }
    
    .upload-section h3 {
        color: white !important;
        margin-bottom: 0.5rem !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        font-weight: 600;
    }
    
    .upload-section p {
        color: rgba(255, 255, 255, 0.9) !important;
        margin: 0 !important;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Main app
def main():
    # Header
    st.markdown('<h1 class="main-header">🧾 AI Resume Grader</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 2rem;">Analyze your resume against job descriptions and get actionable insights</p>', unsafe_allow_html=True)
    
    # Create two columns for upload sections
    col1, col2 = st.columns([1, 1])
    
    # Resume upload section
    with col1:
        st.markdown("""
        <div class="upload-section resume">
            <h3>📄 Upload Resume</h3>
            <p>Supported: PDF, DOCX, TXT (Max 10MB)</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_resume = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "txt", "docx"],
            help="Supported formats: PDF, TXT, DOCX (Max size: 10MB)",
            label_visibility="collapsed",
            key="resume_uploader"
        )
    
    # Job description section
    with col2:
        st.markdown("""
        <div class="upload-section job-desc">
            <h3>💼 Job Description</h3>
            <p>Paste the complete job posting for analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        job_description = st.text_area(
            "Paste the job description here",
            height=200,
            placeholder="Copy and paste the complete job posting here...",
            label_visibility="collapsed",
            key="job_desc_input"
        )
    
    # Analysis section
    if uploaded_resume and job_description and len(job_description.strip()) > 50:
        if st.button("🚀 Analyze Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing your resume..."):
                # Extract text from resume
                resume_text = extract_text_from_file(uploaded_resume)
                
                if resume_text:
                    # Extract keywords
                    resume_keywords = extract_keywords(resume_text)
                    jd_keywords = extract_keywords(job_description)
                    
                    # Calculate match score
                    match_score, matched_keywords, missing_keywords = calculate_match_score(resume_keywords, jd_keywords)
                    
                    # Display results
                    st.markdown("---")
                    st.markdown("## 📊 Analysis Results")
                    
                    # Score display
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        st.metric(
                            label="Match Score",
                            value=f"{match_score}%",
                            delta=f"{len(matched_keywords)} matches"
                        )
                    
                    with col2:
                        st.metric(
                            label="Matched Keywords",
                            value=len(matched_keywords),
                            delta=f"Out of {len(jd_keywords)} total"
                        )
                    
                    with col3:
                        st.metric(
                            label="Missing Keywords",
                            value=len(missing_keywords),
                            delta="Opportunities to improve"
                        )
                    
                    # Detailed analysis
                    if matched_keywords:
                        st.markdown("### ✅ Matched Skills")
                        matched_list = sorted(list(matched_keywords))
                        st.write(", ".join(matched_list[:20]))  # Show first 20
                        
                    if missing_keywords:
                        st.markdown("### ⚠️ Missing Skills")
                        missing_list = sorted(list(missing_keywords))
                        st.write(", ".join(missing_list[:20]))  # Show first 20
                        
                    # Recommendations
                    st.markdown("### 💡 Recommendations")
                    if match_score >= 70:
                        st.success("🎉 Great match! Your resume aligns well with the job requirements.")
                    elif match_score >= 50:
                        st.warning("👍 Good match! Consider adding a few more relevant keywords.")
                    else:
                        st.error("📝 Consider updating your resume to better match the job requirements.")
                
    elif uploaded_resume or job_description:
        st.info("📋 Please upload both a resume and enter a job description to see the analysis.")

if __name__ == "__main__":
    main()
