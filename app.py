
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import io

# Lazy imports for better performance
@st.cache_resource
def load_dependencies():
    """Load heavy dependencies only when needed"""
    try:
        import fitz
        import spacy
        import docx
        return fitz, spacy, docx
    except ImportError as e:
        st.error(f"Missing dependency: {e}. Please install required packages.")
        return None, None, None

# Load OpenAI API key from environment variable or set it here (not recommended for production)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = ""  # Replace with your OpenAI API key or use environment variable

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

# Initialize session state for better performance
if 'processed_resume' not in st.session_state:
    st.session_state.processed_resume = None
if 'processed_jd' not in st.session_state:
    st.session_state.processed_jd = None
if 'last_resume_hash' not in st.session_state:
    st.session_state.last_resume_hash = None
if 'last_jd_hash' not in st.session_state:
    st.session_state.last_jd_hash = None

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    .score-number {
        font-size: 3rem;
        font-weight: bold;
        margin: 0;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px dashed #dee2e6;
        margin: 1rem 0;
    }
    .keyword-match {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.2rem;
        display: inline-block;
    }
    .keyword-missing {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("📊 Analysis Options")
    
    analysis_type = st.selectbox(
        "Analysis Depth",
        ["Basic", "Advanced", "Detailed"],
        help="Choose the level of analysis detail"
    )
    
    min_keyword_length = st.slider(
        "Minimum Keyword Length",
        min_value=2,
        max_value=6,
        value=3,
        help="Minimum length for keywords to be considered"
    )
    
    show_missing_keywords = st.checkbox(
        "Show Missing Keywords",
        value=True,
        help="Display keywords found in job description but not in resume"
    )
    
    st.markdown("---")
    st.markdown("### 📁 Supported Formats")
    st.markdown("- 📄 PDF files")
    st.markdown("- 📝 Text files (.txt)")
    st.markdown("- 📘 Word documents (.docx)")

# Main content
st.markdown('<h1 class="main-header">🧾 AI Resume Grader</h1>', unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; margin-bottom: 2rem; font-size: 1.2rem; color: #666;'>
    Upload your resume and job description to get an intelligent skill match analysis
</div>
""", unsafe_allow_html=True)

# Create two columns for better layout
col1, col2 = st.columns([1, 1], gap="large")

# Optimized text extraction functions with caching
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
def extract_text_from_txt(file_bytes, file_name):
    """Extract text from TXT file with caching"""
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Failed to read TXT: {e}")
        return ""

# Optimized keyword extraction with caching
@st.cache_data
def extract_keywords_cached(text, min_length=3):
    """Extract keywords with caching for better performance"""
    nlp = load_spacy_model()
    if nlp is None:
        # Fallback to simple word extraction if spaCy fails
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        # Simple stopword removal
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

def extract_keywords(doc, min_length=3):
    """Legacy function for compatibility"""
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

def get_file_info(file):
    """Get file information for display"""
    if file:
        return {
            "name": file.name,
            "size": f"{file.size / 1024:.1f} KB",
            "type": file.type
        }
    return None

def create_score_visualization(score):
    """Create a simple, fast gauge chart for the score"""
    # Simplified gauge for better performance
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

def get_text_hash(text):
    """Generate hash for text to check if it changed"""
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()

# Resume Upload Section
with col1:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 📄 Upload Resume")
    
    uploaded_resume = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "txt", "docx"],
        help="Supported formats: PDF, TXT, DOCX",
        label_visibility="collapsed"
    )
    
    if uploaded_resume:
        file_info = get_file_info(uploaded_resume)
        st.success(f"✅ Uploaded: {file_info['name']} ({file_info['size']})")
        
        # Process file immediately and cache result
        file_bytes = uploaded_resume.read()
        file_hash = get_text_hash(file_bytes.decode('utf-8', errors='ignore') if uploaded_resume.type == 'text/plain' else str(file_bytes))
        
        # Only reprocess if file changed
        if st.session_state.last_resume_hash != file_hash:
            with st.spinner("📖 Processing resume..."):
                if uploaded_resume.type == "application/pdf":
                    resume_text = extract_text_from_pdf(file_bytes, uploaded_resume.name)
                elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    resume_text = extract_text_from_docx(file_bytes, uploaded_resume.name)
                else:
                    resume_text = extract_text_from_txt(file_bytes, uploaded_resume.name)
                
                st.session_state.processed_resume = resume_text
                st.session_state.last_resume_hash = file_hash
        
        # Show file preview option
        if st.checkbox("📖 Preview uploaded file"):
            with st.expander("File Preview"):
                preview_text = st.session_state.processed_resume or "Processing..."
                st.text_area("File Content Preview", 
                           preview_text[:500] + "..." if len(preview_text) > 500 else preview_text, 
                           height=200, disabled=True)
    else:
        st.info("👆 Please upload your resume to get started")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Job Description Section
with col2:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    st.markdown("### 💼 Job Description")
    
    job_description = st.text_area(
        "Paste the job description here",
        height=200,
        placeholder="Copy and paste the job description you want to match against...",
        label_visibility="collapsed"
    )
    
    if job_description:
        word_count = len(job_description.split())
        st.success(f"✅ Job description entered ({word_count} words)")
        
        # Process job description and cache
        jd_hash = get_text_hash(job_description)
        if st.session_state.last_jd_hash != jd_hash:
            st.session_state.processed_jd = job_description
            st.session_state.last_jd_hash = jd_hash
    else:
        st.info("👆 Please enter the job description")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Analysis Section - Only show if both inputs are ready
if uploaded_resume and job_description and st.session_state.processed_resume and st.session_state.processed_jd:
    st.markdown("---")
    st.markdown("## 🔍 Analysis Results")
    
    # Use cached/processed data
    resume_text = st.session_state.processed_resume
    job_desc_text = st.session_state.processed_jd
    
    if not resume_text.strip():
        st.error("❌ Could not extract text from the resume. Please try a different file.")
    else:
        # Fast keyword extraction using cached function
        with st.spinner("🔬 Analyzing skill match..."):
            # Use optimized keyword extraction
            resume_keywords = extract_keywords_cached(resume_text, min_keyword_length)
            jd_keywords = extract_keywords_cached(job_desc_text, min_keyword_length)
            
            matched_keywords = resume_keywords.intersection(jd_keywords)
            missing_keywords = jd_keywords - resume_keywords
            
            match_score = round(len(matched_keywords) / len(jd_keywords) * 100, 2) if jd_keywords else 0.0
        
        # Results Layout
        result_col1, result_col2 = st.columns([1, 1])
        
        with result_col1:
            # Score Display
            st.plotly_chart(create_score_visualization(match_score), use_container_width=True)
            
            # Statistics
            st.markdown("### 📊 Statistics")
            stats_df = pd.DataFrame([
                ["Resume Keywords", len(resume_keywords)],
                ["Job Requirements", len(jd_keywords)],
                ["Matched Keywords", len(matched_keywords)],
                ["Missing Keywords", len(missing_keywords)]
            ], columns=["Metric", "Count"])
            
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        with result_col2:
            # Score interpretation
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
                st.markdown("### ✅ Matched Keywords")
                matched_list = sorted(list(matched_keywords))
                
                # Display as badges
                keyword_html = ""
                for keyword in matched_list:
                    keyword_html += f'<span class="keyword-match">{keyword}</span> '
                st.markdown(keyword_html, unsafe_allow_html=True)
                
                # Download option
                if st.button("📥 Download Matched Keywords"):
                    matched_df = pd.DataFrame(matched_list, columns=["Matched Keywords"])
                    csv = matched_df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"matched_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("❌ No matching keywords found.")
        
        with analysis_col2:
            if show_missing_keywords and missing_keywords:
                st.markdown("### ❌ Missing Keywords")
                missing_list = sorted(list(missing_keywords))
                
                # Display as badges
                keyword_html = ""
                for keyword in missing_list[:20]:  # Limit to first 20
                    keyword_html += f'<span class="keyword-missing">{keyword}</span> '
                
                if len(missing_list) > 20:
                    keyword_html += f'<br><small>... and {len(missing_list) - 20} more</small>'
                
                st.markdown(keyword_html, unsafe_allow_html=True)
                
                st.info("💡 Consider adding these keywords to improve your match score!")
        
        # Advanced Analysis (simplified for performance)
        if analysis_type in ["Advanced", "Detailed"]:
            st.markdown("---")
            st.markdown("### 🔬 Advanced Analysis")
            
            # Simplified keyword frequency analysis
            if analysis_type == "Detailed":
                freq_col1, freq_col2 = st.columns([1, 1])
                
                with freq_col1:
                    st.markdown("#### Top Resume Keywords")
                    # Simple frequency count without spaCy processing
                    resume_words = resume_text.lower().split()
                    resume_freq = {}
                    for word in resume_words:
                        clean_word = ''.join(c for c in word if c.isalpha())
                        if clean_word in resume_keywords:
                            resume_freq[clean_word] = resume_freq.get(clean_word, 0) + 1
                    
                    if resume_freq:
                        top_resume = sorted(resume_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                        resume_df = pd.DataFrame(top_resume, columns=["Keyword", "Frequency"])
                        st.dataframe(resume_df, use_container_width=True, hide_index=True)
                
                with freq_col2:
                    st.markdown("#### Top Job Requirements")
                    # Simple frequency count without spaCy processing
                    jd_words = job_desc_text.lower().split()
                    jd_freq = {}
                    for word in jd_words:
                        clean_word = ''.join(c for c in word if c.isalpha())
                        if clean_word in jd_keywords:
                            jd_freq[clean_word] = jd_freq.get(clean_word, 0) + 1
                    
                    if jd_freq:
                        top_jd = sorted(jd_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                        jd_df = pd.DataFrame(top_jd, columns=["Keyword", "Frequency"])
                        st.dataframe(jd_df, use_container_width=True, hide_index=True)

elif uploaded_resume or job_description:
    st.info("📋 Please upload both a resume and enter a job description to see the analysis.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; margin-top: 2rem;'>
    Made with ❤️ using Streamlit and spaCy | 
    <a href="https://github.com/jainamshah2028/ai-resume-grader" target="_blank">View on GitHub</a>
</div>
""", unsafe_allow_html=True)
