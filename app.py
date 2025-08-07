
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

# Load OpenAI API key from environment variable (recommended for security)
# Note: This app primarily uses spaCy for NLP, OpenAI is optional for advanced features
if "OPENAI_API_KEY" not in os.environ:
    # For local development, you can create a .env file with your API key
    # or set it as an environment variable: set OPENAI_API_KEY=your_key_here
    pass  # App will work without OpenAI for basic resume analysis

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
    /* Main styling */
    .main-header {
        font-size: 3.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        font-weight: 800;
        letter-spacing: -1px;
    }
    
    /* Upload sections */
    .upload-section {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        padding: 2.5rem;
        border-radius: 20px;
        border: 2px solid transparent;
        background-clip: padding-box;
        margin: 1rem 0;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1), 0 1px 8px rgba(0,0,0,0.05);
        position: relative;
        overflow: hidden;
    }
    
    .upload-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, #667eea, #764ba2);
        z-index: -1;
        margin: -2px;
        border-radius: inherit;
    }
    
    .upload-section:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(102,126,234,0.15), 0 5px 15px rgba(102,126,234,0.1);
    }
    
    /* Score visualization container */
    .score-container {
        background: linear-gradient(145deg, rgba(102,126,234,0.9) 0%, rgba(118,75,162,0.9) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.2);
        padding: 2rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 15px 35px rgba(102,126,234,0.3), 0 5px 15px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .score-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 3s ease-in-out infinite alternate;
    }
    
    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(180deg); }
    }
    
    /* Keyword badges */
    .keyword-match {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1rem;
        margin: 0.3rem;
        display: inline-block;
        font-weight: 600;
        font-size: 0.85rem;
        box-shadow: 0 4px 15px rgba(16,185,129,0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .keyword-match::before {
        content: '✓';
        position: absolute;
        left: -30px;
        top: 50%;
        transform: translateY(-50%);
        transition: left 0.3s ease;
        font-weight: bold;
    }
    
    .keyword-match:hover::before {
        left: 8px;
    }
    
    .keyword-match:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 8px 25px rgba(16,185,129,0.4);
        padding-left: 1.8rem;
    }
    
    .keyword-missing {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1rem;
        margin: 0.3rem;
        display: inline-block;
        font-weight: 600;
        font-size: 0.85rem;
        box-shadow: 0 4px 15px rgba(239,68,68,0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .keyword-missing::before {
        content: '+';
        position: absolute;
        left: -30px;
        top: 50%;
        transform: translateY(-50%);
        transition: left 0.3s ease;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    .keyword-missing:hover::before {
        left: 8px;
    }
    
    .keyword-missing:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 8px 25px rgba(239,68,68,0.4);
        padding-left: 1.8rem;
    }
    
    /* Student feature sections */
    .student-feature {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 5px solid #2196f3;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        box-shadow: 0 3px 6px rgba(33,150,243,0.1);
    }
    
    /* Tip boxes */
    .tip-box {
        background: linear-gradient(135deg, #fff9c4 0%, #fff3cd 100%);
        border: 1px solid #ffeaa7;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(255,193,7,0.1);
    }
    
    /* Priority skill badges */
    .skill-priority {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(255,107,107,0.3);
    }
    
    /* Critical skill indicators */
    .critical-skill {
        background: linear-gradient(135deg, #ff4757, #c44569);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        margin: 0.3rem;
        display: inline-block;
        font-weight: bold;
        box-shadow: 0 3px 6px rgba(255,71,87,0.3);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Statistics cards */
    .stat-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }
    
    /* Section headers */
    .section-header {
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* Success/Warning/Error styling improvements */
    .stSuccess {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-radius: 10px;
        border-left: 5px solid #28a745;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border-radius: 10px;
        border-left: 5px solid #ffc107;
    }
    
    .stError {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-radius: 10px;
        border-left: 5px solid #dc3545;
    }
    
    .stInfo {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border-radius: 10px;
        border-left: 5px solid #17a2b8;
    }
    
    /* Sidebar improvements */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .stSidebar > div:first-child {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    .stSidebar .stSelectbox > div:first-child {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    
    .stSidebar .stCheckbox {
        background: rgba(255,255,255,0.05);
        padding: 0.5rem;
        border-radius: 10px;
        margin: 0.25rem 0;
        transition: all 0.3s ease;
    }
    
    .stSidebar .stCheckbox:hover {
        background: rgba(255,255,255,0.1);
        transform: translateX(5px);
    }
    
    /* Button improvements */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102,126,234,0.5);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f1f3f4 0%, #e8eaed 100%);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Progress and loading indicators */
    .stSpinner {
        border-color: #667eea !important;
    }
    
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
        border-radius: 10px !important;
        height: 8px !important;
    }
    
    .stProgress {
        background: rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    
    /* Custom loader animation */
    @keyframes pulse-glow {
        0%, 100% {
            box-shadow: 0 0 20px rgba(102,126,234,0.4);
        }
        50% {
            box-shadow: 0 0 40px rgba(102,126,234,0.8);
        }
    }
    
    .stSpinner > div {
        animation: pulse-glow 2s ease-in-out infinite !important;
    }
    
    /* Footer styling */
    .footer {
        margin-top: 3rem;
        padding: 2rem;
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        color: white;
        border-radius: 15px;
        text-align: center;
    }
    
    /* Resource links styling */
    .resource-link {
        color: #007bff;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.3s ease;
    }
    
    .resource-link:hover {
        color: #0056b3;
        text-decoration: underline;
    }
    
    /* Dark theme adaptations */
    @media (prefers-color-scheme: dark) {
        .upload-section {
            background: linear-gradient(145deg, #2d3748 0%, #1a202c 100%);
            color: #e2e8f0;
        }
        
        .stat-card {
            background: rgba(45, 55, 72, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
        }
    }
    
    /* Global animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .upload-section, .score-container, .stat-card {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Responsive design improvements */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
        
        .upload-section {
            padding: 1.5rem;
            margin: 0.5rem 0;
        }
        
        .score-container {
            padding: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Enhanced Sidebar
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 1rem 0 2rem 0;'>
        <h2 style='color: #007bff; margin: 0; font-weight: 600; font-size: 1.4rem;'>
            📊 Smart Analysis
        </h2>
        <p style='color: #6c757d; margin: 0.5rem 0 0 0; font-size: 0.9rem;'>
            Customize your experience
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Career Level Selection with enhanced styling
    st.markdown("""
    <div style='background: linear-gradient(135deg, #e8f4f8 0%, #d1ecf1 100%); 
                padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; 
                border: 1px solid #bee5eb;'>
        <h4 style='color: #0c5460; margin: 0 0 1rem 0; font-size: 1rem; font-weight: 600;'>
            🎓 Career Profile
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    career_level = st.selectbox(
        "Career Level",
        ["Student/Fresher", "Entry Level (0-2 years)", "Mid Level (2-5 years)", "Senior Level (5+ years)"],
        help="Choose your career level for tailored analysis",
        label_visibility="collapsed"
    )
    
    # Analysis Configuration
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                padding: 1rem; border-radius: 12px; margin: 1.5rem 0; 
                border: 1px solid #dee2e6;'>
        <h4 style='color: #495057; margin: 0 0 1rem 0; font-size: 1rem; font-weight: 600;'>
            ⚙️ Analysis Settings
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    analysis_type = st.selectbox(
        "Analysis Depth",
        ["Basic", "Advanced", "Detailed"],
        help="Choose the level of analysis detail",
        index=1
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
    
    # Student/Fresher Features with enhanced styling
    st.markdown("""
    <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                padding: 1rem; border-radius: 12px; margin: 1.5rem 0; 
                border: 1px solid #ffeaa7;'>
        <h4 style='color: #856404; margin: 0 0 1rem 0; font-size: 1rem; font-weight: 600;'>
            🎯 Student & Fresher Tools
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    show_skill_gaps = st.checkbox(
        "📈 Skill Gap Analysis",
        value=True if career_level == "Student/Fresher" else False,
        help="Show skills you need to develop"
    )
    
    show_learning_suggestions = st.checkbox(
        "📚 Learning Suggestions",
        value=True if career_level == "Student/Fresher" else False,
        help="Get recommendations for online courses and certifications"
    )
    
    show_project_ideas = st.checkbox(
        "💡 Project Ideas",
        value=True if career_level == "Student/Fresher" else False,
        help="Get project ideas to build relevant experience"
    )
    
    show_entry_level_tips = st.checkbox(
        "🚀 Entry-Level Tips",
        value=True if career_level == "Student/Fresher" else False,
        help="Tips for landing your first job"
    )
    
    # Quick Actions & Information
    st.markdown("""
    <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                padding: 1rem; border-radius: 12px; margin: 1.5rem 0; 
                border: 1px solid #c3e6cb;'>
        <h4 style='color: #155724; margin: 0 0 1rem 0; font-size: 1rem; font-weight: 600;'>
            ⚡ Quick Actions
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Reset Analysis", help="Clear all cached data and start fresh"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("✅ Analysis reset! Upload new files to begin.")
        st.experimental_rerun()
    
    # About Section
    with st.expander("ℹ️ About This App"):
        st.markdown("""
        **AI Resume Grader** helps you optimize your resume for specific job applications.
        
        **Features:**
        - 📄 Support for PDF, DOCX, and TXT files
        - 🎯 Keyword matching and gap analysis
        - 📊 Interactive score visualization
        - 🎓 Special features for students/freshers
        - 📥 Export analysis results
        
        **How it works:**
        1. Upload your resume
        2. Paste the job description
        3. Get instant analysis and recommendations
        
        **Technology:**
        Built with Python, Streamlit, spaCy, and Plotly.
        """)
    
    # Support Section
    with st.expander("🆘 Need Help?"):
        st.markdown("""
        **Common Issues:**
        - **File not processing:** Try a different file format or smaller file size
        - **Low match score:** Focus on adding relevant keywords from the job description
        - **Missing features:** Enable student/fresher features in the sidebar
        
        **Tips for Better Results:**
        - Use specific, detailed job descriptions
        - Ensure your resume is properly formatted
        - Include both technical and soft skills
        
        **Contact:**
        - GitHub: [jainamshah2028/ai-resume-grader](https://github.com/jainamshah2028/ai-resume-grader)
        - Issues: Report bugs on GitHub Issues
        """)
    
    # Supported Formats with better styling
    st.markdown("""
    <div style='margin-top: 2rem; padding: 1rem; background: #f8f9fa; 
                border-radius: 10px; border: 1px solid #dee2e6;'>
        <h5 style='color: #495057; margin: 0 0 0.8rem 0; font-size: 0.95rem; font-weight: 600;'>
            📁 Supported Formats
        </h5>
        <div style='color: #6c757d; font-size: 0.85rem; line-height: 1.6;'>
            <div style='margin: 0.3rem 0;'>📄 PDF documents</div>
            <div style='margin: 0.3rem 0;'>📝 Text files (.txt)</div>
            <div style='margin: 0.3rem 0;'>📘 Word documents (.docx)</div>
        </div>
    </div>
    
    <div style='margin-top: 1rem; padding: 1rem; background: #e8f4f8; 
                border-radius: 10px; border: 1px solid #bee5eb;'>
        <h5 style='color: #0c5460; margin: 0 0 0.5rem 0; font-size: 0.9rem; font-weight: 600;'>
            💡 Pro Tips
        </h5>
        <ul style='color: #0c5460; font-size: 0.8rem; margin: 0; padding-left: 1.2rem; line-height: 1.5;'>
            <li>Use specific job descriptions for better results</li>
            <li>Enable student features for career guidance</li>
            <li>Download your analysis for future reference</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Main content
st.markdown("""
<div style='text-align: center; margin-bottom: 3rem;'>
    <h1 class="main-header">🧾 AI Resume Grader</h1>
    <div style='font-size: 1.3rem; color: #495057; margin-bottom: 1rem; font-weight: 300;'>
        Upload your resume and job description to get an intelligent skill match analysis
    </div>
    <div style='font-size: 1rem; color: #6c757d; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                padding: 0.8rem 1.5rem; border-radius: 25px; display: inline-block; margin-top: 0.5rem; 
                box-shadow: 0 2px 8px rgba(33,150,243,0.2);'>
        ✨ Now with special features for students and freshers!
    </div>
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

# Student/Fresher specific data and functions
def get_learning_resources():
    """Get learning resources for different skills"""
    return {
        'python': {
            'courses': ['Python for Everybody (Coursera)', 'Complete Python Bootcamp (Udemy)', 'CS50 Python (Harvard)'],
            'certifications': ['Python Institute PCAP', 'Microsoft Python Certification'],
            'projects': ['Web scraper', 'Data analysis dashboard', 'Simple web app with Flask']
        },
        'javascript': {
            'courses': ['JavaScript Fundamentals (freeCodeCamp)', 'Modern JavaScript (Udemy)', 'JavaScript30 (Wes Bos)'],
            'certifications': ['freeCodeCamp JavaScript Certification'],
            'projects': ['Interactive website', 'To-do app', 'Weather app with API']
        },
        'java': {
            'courses': ['Java Programming (Coursera)', 'Complete Java Masterclass (Udemy)', 'Oracle Java Tutorials'],
            'certifications': ['Oracle Certified Associate (OCA)', 'Oracle Certified Professional (OCP)'],
            'projects': ['Banking system', 'Library management system', 'Simple game development']
        },
        'react': {
            'courses': ['React Complete Guide (Udemy)', 'React Documentation', 'freeCodeCamp React'],
            'certifications': ['freeCodeCamp Front End Libraries'],
            'projects': ['Portfolio website', 'E-commerce frontend', 'Social media dashboard']
        },
        'sql': {
            'courses': ['SQL for Data Science (Coursera)', 'Complete SQL Bootcamp (Udemy)', 'W3Schools SQL'],
            'certifications': ['Microsoft SQL Server Certification', 'Oracle Database Certification'],
            'projects': ['Database design for e-commerce', 'Data analysis queries', 'School management system']
        },
        'machine learning': {
            'courses': ['ML Course by Andrew Ng (Coursera)', 'Hands-On ML (Kaggle Learn)', 'Fast.ai Practical Deep Learning'],
            'certifications': ['Google ML Certification', 'AWS ML Specialty'],
            'projects': ['Prediction model', 'Image classification', 'Recommendation system']
        },
        'data science': {
            'courses': ['Data Science Specialization (Coursera)', 'Python for Data Science (edX)', 'Kaggle Learn'],
            'certifications': ['Google Data Analytics Certificate', 'IBM Data Science Certificate'],
            'projects': ['Sales analysis dashboard', 'Customer segmentation', 'Predictive analytics']
        },
        'web development': {
            'courses': ['The Odin Project', 'freeCodeCamp Full Stack', 'Web Developer Bootcamp (Udemy)'],
            'certifications': ['freeCodeCamp Responsive Web Design', 'Google UX Design Certificate'],
            'projects': ['Personal portfolio', 'Restaurant website', 'Blog platform']
        }
    }

def get_entry_level_tips():
    """Get tips for entry-level job seekers"""
    return [
        "🎯 **Tailor your resume** for each job application - highlight relevant coursework and projects",
        "🔗 **Build a strong LinkedIn profile** with a professional photo and detailed experience section",
        "📁 **Create a GitHub portfolio** showcasing your best projects with clear README files",
        "🤝 **Network actively** - attend virtual meetups, join professional groups, connect with alumni",
        "📝 **Apply to entry-level positions** even if you don't meet 100% of requirements",
        "🎤 **Practice common interview questions** and prepare STAR method answers",
        "📚 **Show enthusiasm for learning** - mention online courses, bootcamps, or self-study",
        "🏆 **Highlight transferable skills** from internships, part-time jobs, or volunteer work",
        "💼 **Consider internships and apprenticeships** as stepping stones to full-time roles",
        "📧 **Follow up professionally** after applications and interviews"
    ]

def analyze_skill_gaps(resume_keywords, jd_keywords, career_level):
    """Analyze skill gaps based on career level"""
    missing_skills = jd_keywords - resume_keywords
    
    # Priority skills for different career levels
    priority_skills = {
        'Student/Fresher': ['python', 'javascript', 'sql', 'git', 'html', 'css', 'communication', 'teamwork'],
        'Entry Level (0-2 years)': ['python', 'javascript', 'sql', 'git', 'agile', 'testing', 'debugging'],
        'Mid Level (2-5 years)': ['architecture', 'leadership', 'mentoring', 'system design', 'performance'],
        'Senior Level (5+ years)': ['strategy', 'leadership', 'architecture', 'mentoring', 'business']
    }
    
    relevant_priority = set(priority_skills.get(career_level, []))
    critical_gaps = missing_skills.intersection(relevant_priority)
    
    return {
        'all_gaps': missing_skills,
        'critical_gaps': critical_gaps,
        'priority_skills': relevant_priority
    }

def suggest_projects_for_skills(missing_skills):
    """Suggest projects based on missing skills"""
    project_suggestions = {
        'python': "Build a web scraper to collect job postings from different websites",
        'javascript': "Create an interactive resume website with animations and dynamic content",
        'react': "Develop a job application tracker with React and local storage",
        'sql': "Design a database for a university course management system",
        'machine learning': "Build a resume keyword optimizer using NLP techniques",
        'data science': "Analyze job market trends using public datasets",
        'web development': "Create a portfolio website showcasing all your projects",
        'git': "Contribute to open-source projects on GitHub",
        'api': "Build a REST API for a simple task management application",
        'testing': "Add comprehensive tests to your existing projects",
        'docker': "Containerize your web applications for easy deployment",
        'cloud': "Deploy your projects on AWS, Google Cloud, or Azure"
    }
    
    suggestions = []
    for skill in missing_skills:
        if skill in project_suggestions:
            suggestions.append(f"**{skill.title()}**: {project_suggestions[skill]}")
    
    return suggestions[:5]  # Return top 5 suggestions

# Resume Upload Section
with col1:
    st.markdown("""
    <div class="upload-section">
        <div style='text-align: center; margin-bottom: 1rem;'>
            <h3 style='color: #2c3e50; margin: 0; font-weight: 600;'>📄 Upload Resume</h3>
            <p style='color: #6c757d; margin: 0.5rem 0; font-size: 0.9rem;'>
                Drag and drop or click to upload your resume
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    uploaded_resume = st.file_uploader(
        "Choose your resume file",
        type=["pdf", "txt", "docx"],
        help="Supported formats: PDF, TXT, DOCX (Max size: 10MB)",
        label_visibility="collapsed"
    )
    
    if uploaded_resume:
        # Check file size (10MB limit)
        if uploaded_resume.size > 10 * 1024 * 1024:  # 10MB in bytes
            st.error("❌ File size too large! Please upload a file smaller than 10MB.")
            st.stop()
        
        file_info = get_file_info(uploaded_resume)
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                    border-left: 4px solid #28a745;'>
            <strong>✅ Successfully uploaded:</strong><br>
            📁 {file_info['name']}<br>
            📊 Size: {file_info['size']}
        </div>
        """, unsafe_allow_html=True)
        
        # Process file immediately and cache result
        file_bytes = uploaded_resume.read()
        file_hash = get_text_hash(file_bytes.decode('utf-8', errors='ignore') if uploaded_resume.type == 'text/plain' else str(file_bytes))
        
        # Only reprocess if file changed
        if st.session_state.last_resume_hash != file_hash:
            with st.spinner("📖 Processing resume..."):
                progress_bar = st.progress(0)
                progress_bar.progress(25)
                
                if uploaded_resume.type == "application/pdf":
                    resume_text = extract_text_from_pdf(file_bytes, uploaded_resume.name)
                elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    resume_text = extract_text_from_docx(file_bytes, uploaded_resume.name)
                else:
                    resume_text = extract_text_from_txt(file_bytes, uploaded_resume.name)
                
                progress_bar.progress(75)
                st.session_state.processed_resume = resume_text
                st.session_state.last_resume_hash = file_hash
                progress_bar.progress(100)
                st.success("✅ Resume processed successfully!")
        
        # Show file preview option
        if st.checkbox("📖 Preview uploaded file", help="Click to see the extracted text from your resume"):
            with st.expander("📄 File Content Preview"):
                preview_text = st.session_state.processed_resume or "Processing..."
                st.text_area("", 
                           preview_text[:500] + "..." if len(preview_text) > 500 else preview_text, 
                           height=200, disabled=True, label_visibility="collapsed")
    else:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                    border-left: 4px solid #17a2b8; text-align: center;'>
            👆 Please upload your resume to get started
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Job Description Section
with col2:
    st.markdown("""
    <div class="upload-section">
        <div style='text-align: center; margin-bottom: 1rem;'>
            <h3 style='color: #2c3e50; margin: 0; font-weight: 600;'>💼 Job Description</h3>
            <p style='color: #6c757d; margin: 0.5rem 0; font-size: 0.9rem;'>
                Paste the job description you want to analyze
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    job_description = st.text_area(
        "Paste the job description here",
        height=200,
        placeholder="Copy and paste the job description you want to match against...\n\nExample:\n- Bachelor's degree in Computer Science\n- 2+ years experience with Python\n- Knowledge of SQL and databases\n- Experience with web frameworks\n- Strong communication skills",
        label_visibility="collapsed"
    )
    
    if job_description:
        word_count = len(job_description.split())
        
        # Validate job description length
        if word_count < 10:
            st.warning("⚠️ Job description seems too short. Please provide more details for better analysis.")
        elif word_count > 2000:
            st.warning("⚠️ Job description is very long. Consider summarizing for better performance.")
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                    border-left: 4px solid #28a745;'>
            <strong>✅ Job description entered</strong><br>
            📊 Word count: {word_count} words
        </div>
        """, unsafe_allow_html=True)
        
        # Process job description and cache
        jd_hash = get_text_hash(job_description)
        if st.session_state.last_jd_hash != jd_hash:
            st.session_state.processed_jd = job_description
            st.session_state.last_jd_hash = jd_hash
    else:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                    border-left: 4px solid #17a2b8; text-align: center;'>
            👆 Please enter the job description
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Analysis Section - Only show if both inputs are ready
if uploaded_resume and job_description and st.session_state.processed_resume and st.session_state.processed_jd:
    st.markdown("""
    <hr style='margin: 3rem 0; border: none; height: 2px; background: linear-gradient(90deg, #007bff, #28a745);'>
    <div style='text-align: center; margin: 2rem 0;'>
        <h2 style='color: #2c3e50; font-weight: 600;'>🔍 Analysis Results</h2>
        <p style='color: #6c757d;'>Here's how your resume matches the job requirements</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Use cached/processed data
    resume_text = st.session_state.processed_resume
    job_desc_text = st.session_state.processed_jd
    
    if not resume_text.strip():
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); 
                    padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                    border-left: 5px solid #dc3545; text-align: center;'>
            <h4 style='color: #721c24; margin: 0;'>❌ Processing Error</h4>
            <p style='color: #721c24; margin: 0.5rem 0;'>
                Could not extract text from the resume. Please try a different file or format.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fast keyword extraction using cached function
        with st.spinner("🔬 Analyzing skill match..."):
            # Use optimized keyword extraction
            resume_keywords = extract_keywords_cached(resume_text, min_keyword_length)
            jd_keywords = extract_keywords_cached(job_desc_text, min_keyword_length)
            
            matched_keywords = resume_keywords.intersection(jd_keywords)
            missing_keywords = jd_keywords - resume_keywords
            
            match_score = round(len(matched_keywords) / len(jd_keywords) * 100, 2) if jd_keywords else 0.0
            
            # Analyze skill gaps for students/freshers
            skill_gap_analysis = analyze_skill_gaps(resume_keywords, jd_keywords, career_level)
        
        # Results Layout
        result_col1, result_col2 = st.columns([1, 1])
        
        with result_col1:
            # Score Display with enhanced styling
            st.markdown("""
            <div class="score-container">
                <h3 style='margin: 0 0 1rem 0; font-weight: 600;'>🎯 Match Score</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.plotly_chart(create_score_visualization(match_score), use_container_width=True)
            
            # Enhanced Statistics
            st.markdown("""
            <div style='margin-top: 1.5rem;'>
                <h3 class='section-header'>📊 Statistics Overview</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Create colored statistics cards
            col_stat1, col_stat2 = st.columns(2)
            
            with col_stat1:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                            padding: 1rem; border-radius: 15px; margin: 0.5rem 0; 
                            border-left: 4px solid #2196f3; text-align: center;'>
                    <h4 style='color: #1565c0; margin: 0; font-size: 1.8rem;'>{len(resume_keywords)}</h4>
                    <p style='color: #1976d2; margin: 0; font-weight: 500;'>Resume Keywords</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                            padding: 1rem; border-radius: 15px; margin: 0.5rem 0; 
                            border-left: 4px solid #28a745; text-align: center;'>
                    <h4 style='color: #155724; margin: 0; font-size: 1.8rem;'>{len(matched_keywords)}</h4>
                    <p style='color: #155724; margin: 0; font-weight: 500;'>Matched Keywords</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_stat2:
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                            padding: 1rem; border-radius: 15px; margin: 0.5rem 0; 
                            border-left: 4px solid #ffc107; text-align: center;'>
                    <h4 style='color: #856404; margin: 0; font-size: 1.8rem;'>{len(jd_keywords)}</h4>
                    <p style='color: #856404; margin: 0; font-weight: 500;'>Job Requirements</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); 
                            padding: 1rem; border-radius: 15px; margin: 0.5rem 0; 
                            border-left: 4px solid #dc3545; text-align: center;'>
                    <h4 style='color: #721c24; margin: 0; font-size: 1.8rem;'>{len(missing_keywords)}</h4>
                    <p style='color: #721c24; margin: 0; font-weight: 500;'>Missing Keywords</p>
                </div>
                """, unsafe_allow_html=True)
        
        with result_col2:
            # Enhanced Score interpretation with career-level specific advice
            st.markdown("""
            <div style='margin-bottom: 1.5rem;'>
                <h3 class='section-header'>🎯 Score Interpretation</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if career_level == "Student/Fresher":
                if match_score >= 60:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                                padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                                border-left: 5px solid #28a745;'>
                        <h4 style='color: #155724; margin: 0 0 0.5rem 0;'>🌟 Excellent Start!</h4>
                        <p style='color: #155724; margin: 0;'>
                            Your resume shows relevant skills for entry-level positions. You're on the right track!
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                elif match_score >= 40:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                                padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                                border-left: 5px solid #ffc107;'>
                        <h4 style='color: #856404; margin: 0 0 0.5rem 0;'>✨ Good Foundation!</h4>
                        <p style='color: #856404; margin: 0;'>
                            Focus on building the missing skills through projects and courses.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                elif match_score >= 20:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); 
                                padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                                border-left: 5px solid #17a2b8;'>
                        <h4 style='color: #0c5460; margin: 0 0 0.5rem 0;'>💡 Learning Opportunity!</h4>
                        <p style='color: #0c5460; margin: 0;'>
                            Consider taking courses in the missing skill areas to improve your profile.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background: linear-gradient(135deg, #e2e3e5 0%, #d6d8db 100%); 
                                padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                                border-left: 5px solid #6c757d;'>
                        <h4 style='color: #495057; margin: 0 0 0.5rem 0;'>🚀 Starting Your Journey!</h4>
                        <p style='color: #495057; margin: 0;'>
                            Focus on building fundamental skills first. Every expert was once a beginner!
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Show encouragement for students
                st.markdown("""
                <div style='background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                            padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                            border-left: 5px solid #2196f3;'>
                    <h4 style='color: #1565c0; margin: 0 0 0.5rem 0;'>💪 Student Tip</h4>
                    <p style='color: #1976d2; margin: 0; font-weight: 500;'>
                        As a student/fresher, focus on learning and building projects rather than having perfect keyword matches!
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                if match_score >= 80:
                    st.success("🌟 Excellent match! Your resume aligns well with the job requirements.")
                elif match_score >= 60:
                    st.warning("✨ Good match! Consider adding a few more relevant keywords.")
                elif match_score >= 40:
                    st.warning("💡 Fair match. Your resume could benefit from more relevant keywords.")
                else:
                    st.error("🔄 Low match. Consider significantly updating your resume to better align with the job requirements.")
        
        # Enhanced Detailed Analysis
        st.markdown("""
        <hr style='margin: 3rem 0; border: none; height: 1px; background: linear-gradient(90deg, #007bff, #28a745);'>
        """, unsafe_allow_html=True)
        
        analysis_col1, analysis_col2 = st.columns([1, 1])
        
        with analysis_col1:
            if matched_keywords:
                st.markdown("""
                <div style='margin-bottom: 1.5rem;'>
                    <h3 class='section-header'>✅ Matched Keywords</h3>
                    <p style='color: #6c757d; margin-bottom: 1rem;'>
                        Great! These skills from the job description were found in your resume:
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                matched_list = sorted(list(matched_keywords))
                
                # Display as enhanced badges
                keyword_html = '<div style="margin: 1rem 0;">'
                for keyword in matched_list:
                    keyword_html += f'<span class="keyword-match">{keyword}</span> '
                keyword_html += '</div>'
                st.markdown(keyword_html, unsafe_allow_html=True)
                
                # Enhanced download section
                st.markdown("""
                <div style='margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                            border-radius: 10px; border: 1px solid #dee2e6;'>
                    <p style='margin: 0 0 0.5rem 0; font-weight: 500; color: #495057;'>
                        📥 Export your matched keywords
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📥 Download Matched Keywords", help="Download your matched keywords as a CSV file"):
                    matched_df = pd.DataFrame(matched_list, columns=["Matched Keywords"])
                    csv = matched_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV File",
                        data=csv,
                        file_name=f"matched_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                # Add full analysis export
                if st.button("📊 Download Full Analysis Report", help="Download complete analysis as PDF"):
                    # Create analysis summary
                    analysis_summary = f"""
                    AI Resume Grader Analysis Report
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    
                    MATCH SCORE: {match_score}%
                    
                    STATISTICS:
                    - Resume Keywords: {len(resume_keywords)}
                    - Job Requirements: {len(jd_keywords)}
                    - Matched Keywords: {len(matched_keywords)}
                    - Missing Keywords: {len(missing_keywords)}
                    
                    MATCHED SKILLS:
                    {', '.join(sorted(matched_keywords))}
                    
                    MISSING SKILLS:
                    {', '.join(sorted(list(missing_keywords)[:20]))}
                    
                    CAREER LEVEL: {career_level}
                    """
                    
                    st.download_button(
                        label="📄 Download Analysis Report",
                        data=analysis_summary,
                        file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
            else:
                st.markdown("""
                <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                            padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                            border-left: 5px solid #ffc107; text-align: center;'>
                    <h4 style='color: #856404; margin: 0 0 0.5rem 0;'>⚠️ No Matching Keywords</h4>
                    <p style='color: #856404; margin: 0;'>
                        Consider updating your resume to include more relevant keywords from the job description.
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        with analysis_col2:
            if show_missing_keywords and missing_keywords:
                st.markdown("""
                <div style='margin-bottom: 1.5rem;'>
                    <h3 class='section-header'>❌ Missing Keywords</h3>
                    <p style='color: #6c757d; margin-bottom: 1rem;'>
                        These skills from the job description could be added to your resume:
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                missing_list = sorted(list(missing_keywords))
                
                # Display as enhanced badges with limit
                keyword_html = '<div style="margin: 1rem 0;">'
                for keyword in missing_list[:20]:  # Limit to first 20
                    keyword_html += f'<span class="keyword-missing">{keyword}</span> '
                
                if len(missing_list) > 20:
                    keyword_html += f'</div><div style="margin-top: 1rem; padding: 0.5rem; background: #f8f9fa; border-radius: 5px; text-align: center;"><small style="color: #6c757d;">... and {len(missing_list) - 20} more keywords</small></div>'
                else:
                    keyword_html += '</div>'
                
                st.markdown(keyword_html, unsafe_allow_html=True)
                
                st.markdown("""
                <div style='background: linear-gradient(135d, #d1ecf1 0%, #bee5eb 100%); 
                            padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                            border-left: 4px solid #17a2b8;'>
                    <p style='color: #0c5460; margin: 0; font-weight: 500;'>
                        💡 Consider adding these keywords to improve your match score!
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
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
        
        # NEW STUDENT/FRESHER FEATURES
        if career_level in ["Student/Fresher", "Entry Level (0-2 years)"]:
            
            # Skill Gap Analysis
            if show_skill_gaps:
                st.markdown("---")
                st.markdown("## 📈 Skill Gap Analysis")
                
                col_gaps1, col_gaps2 = st.columns([1, 1])
                
                with col_gaps1:
                    if skill_gap_analysis['critical_gaps']:
                        st.markdown("### 🔥 Critical Skills to Learn")
                        critical_list = sorted(list(skill_gap_analysis['critical_gaps']))
                        for skill in critical_list[:8]:
                            st.markdown(f"• **{skill.title()}** - High priority for your career level")
                    else:
                        st.success("✅ You have the critical skills for your career level!")
                
                with col_gaps2:
                    st.markdown("### 🎯 Priority Skills for Your Level")
                    priority_list = sorted(list(skill_gap_analysis['priority_skills']))
                    for skill in priority_list[:8]:
                        status = "✅" if skill in resume_keywords else "⭕"
                        st.markdown(f"{status} {skill.title()}")
            
            # Learning Suggestions
            if show_learning_suggestions and missing_keywords:
                st.markdown("---")
                st.markdown("## 📚 Learning Suggestions")
                
                learning_resources = get_learning_resources()
                relevant_skills = [skill for skill in missing_keywords if skill in learning_resources]
                
                if relevant_skills:
                    for skill in relevant_skills[:3]:  # Show top 3 skills
                        with st.expander(f"🎓 Learn {skill.title()}"):
                            resources = learning_resources[skill]
                            
                            col_learn1, col_learn2 = st.columns([1, 1])
                            
                            with col_learn1:
                                st.markdown("**📖 Recommended Courses:**")
                                for course in resources['courses']:
                                    st.markdown(f"• {course}")
                                
                                st.markdown("**🏆 Certifications:**")
                                for cert in resources['certifications']:
                                    st.markdown(f"• {cert}")
                            
                            with col_learn2:
                                st.markdown("**💻 Project Ideas:**")
                                for project in resources['projects']:
                                    st.markdown(f"• {project}")
                else:
                    st.info("🎉 Great! You already have knowledge in the major skill areas. Focus on deepening your expertise!")
            
            # Project Ideas
            if show_project_ideas and missing_keywords:
                st.markdown("---")
                st.markdown("## 💡 Project Ideas to Build Experience")
                
                project_suggestions = suggest_projects_for_skills(missing_keywords)
                
                if project_suggestions:
                    st.markdown("### 🛠️ Recommended Projects:")
                    for i, suggestion in enumerate(project_suggestions, 1):
                        st.markdown(f"{i}. {suggestion}")
                    
                    st.info("💡 **Pro Tip**: Add these projects to your GitHub and mention them in your resume!")
                else:
                    st.success("🎉 You seem to have good technical coverage! Focus on polishing existing projects.")
            
            # Entry-Level Tips
            if show_entry_level_tips:
                st.markdown("---")
                st.markdown("## 🚀 Entry-Level Job Hunting Tips")
                
                tips = get_entry_level_tips()
                
                col_tips1, col_tips2 = st.columns([1, 1])
                
                with col_tips1:
                    for i, tip in enumerate(tips[:5]):
                        st.markdown(tip)
                
                with col_tips2:
                    for tip in tips[5:]:
                        st.markdown(tip)
                
                # Additional resources section
                st.markdown("### 🔗 Helpful Resources")
                resources_col1, resources_col2 = st.columns([1, 1])
                
                with resources_col1:
                    st.markdown("""
                    **Job Boards for Freshers:**
                    • [AngelList](https://angel.co) - Startups
                    • [LinkedIn](https://linkedin.com/jobs) - Professional network
                    • [Indeed](https://indeed.com) - General job search
                    • [Glassdoor](https://glassdoor.com) - Company reviews
                    """)
                
                with resources_col2:
                    st.markdown("""
                    **Learning Platforms:**
                    • [freeCodeCamp](https://freecodecamp.org) - Free coding bootcamp
                    • [Coursera](https://coursera.org) - University courses
                    • [Udemy](https://udemy.com) - Practical skills
                    • [Kaggle Learn](https://kaggle.com/learn) - Data science
                    """)
        
        # Career-specific insights
        if career_level == "Student/Fresher":
            st.markdown("---")
            st.markdown("## 🎓 Student-Specific Insights")
            
            insight_col1, insight_col2 = st.columns([1, 1])
            
            with insight_col1:
                st.markdown("### 💪 Strengths to Highlight")
                st.markdown("""
                • **Fresh perspective** and eagerness to learn
                • **Up-to-date knowledge** of latest technologies
                • **Adaptability** and quick learning ability
                • **Academic projects** and coursework
                • **Internship experiences** (if any)
                """)
            
            with insight_col2:
                st.markdown("### 🎯 What Employers Look For")
                st.markdown("""
                • **Problem-solving skills** through projects
                • **Communication skills** and teamwork
                • **Passion for technology** and learning
                • **Basic technical competency**
                • **Professional attitude** and reliability
                """)

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
