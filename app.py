
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

# Load OpenAI API key from environment variable (recommended for security)
# Note: This app primarily uses spaCy for NLP, OpenAI is optional for advanced features
if "OPENAI_API_KEY" not in os.environ:
    # For local development, you can create a .env file with your API key
    # or set it as an environment variable: set OPENAI_API_KEY=your_key_here
    pass  # App will work without OpenAI for basic resume analysis

# Optimized spaCy model loading with better caching
@st.cache_resource
def load_spacy_model():
    """Load spaCy model with fallback options for deployment"""
    try:
        _, spacy, _ = load_dependencies()
        if spacy is None:
            return None
        
        # Try to load the model with different approaches
        try:
            # First attempt: load installed model
            nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
            return nlp
        except OSError:
            # Second attempt: download and load model
            try:
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True, capture_output=True)
                nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
                return nlp
            except:
                # Third attempt: use blank model as fallback
                st.warning("⚠️ Using basic English model. Some features may be limited.")
                nlp = spacy.blank("en")
                return nlp
                
    except Exception as e:
        st.error(f"Error loading spaCy model: {e}")
        # Fallback to basic model
        try:
            _, spacy, _ = load_dependencies()
            if spacy:
                return spacy.blank("en")
        except:
            pass
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

# Lightweight CSS for better performance
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
    
    .keyword-match {
        background: #28a745;
        color: white;
        border-radius: 15px;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    
    .keyword-missing {
        background: #dc3545;
        color: white;
        border-radius: 15px;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85rem;
    }
    
    .score-container {
        background: #667eea;
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Enhanced Sidebar
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 1rem 0 2rem 0; background: rgba(255,255,255,0.1); border-radius: 15px; margin-bottom: 1rem;'>
        <h2 style='color: white; margin: 0; font-weight: 600; font-size: 1.4rem;'>
            ⚙️ Settings
        </h2>
        <p style='color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0; font-size: 0.9rem;'>
            Customize your analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Career Level Selection with enhanced styling
    st.markdown("""
    <div style='background: linear-gradient(135deg, #e8f4f8 0%, #d1ecf1 100%); 
                padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; 
                border: 1px solid #bee5eb;'>
        <h4 style='color: #0c5460; margin: 0 0 1rem 0; font-size: 1rem; font-weight: 600;'>
            � Target Role
        </h4>
        <p style='color: #0c5460; margin: 0; font-size: 0.8rem;'>
            Choose your experience level for tailored analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    career_level = st.selectbox(
        "Experience Level",
        ["Student/Fresher", "Entry Level (0-2 years)", "Mid Level (2-5 years)", "Senior Level (5+ years)"],
        help="This determines which skills and analysis features you'll see",
        label_visibility="collapsed"
    )
    
    # Advanced Settings Expander
    with st.expander("🔧 Advanced Settings", expanded=False):
        st.markdown("**Analysis Depth**")
        st.caption("How deep should we scan your resume?")
        
        analysis_type = st.selectbox(
            "Analysis Depth",
            ["Basic", "Advanced", "Detailed"],
            help="Choose the level of analysis detail",
            index=1,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.markdown("**Keyword Filtering**")
        st.caption("Minimum length for keywords to be considered")
        
        min_keyword_length = st.slider(
            "Minimum Keyword Length",
            min_value=2,
            max_value=6,
            value=3,
            help="Keywords shorter than this will be filtered out",
            label_visibility="collapsed"
        )
        
        # Add custom CSS for slider
        st.markdown("""
        <style>
        .stSlider > div > div > div > div {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        </style>
        """, unsafe_allow_html=True)
    
    show_missing_keywords = st.checkbox(
        "🎯 Show skill gaps to address",
        value=True,
        help="Display keywords from the job description that aren't in your resume - these are opportunities for improvement"
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
        "📈 Skill development roadmap",
        value=True if career_level == "Student/Fresher" else False,
        help="Get personalized suggestions for building missing skills through courses and projects"
    )
    
    show_learning_suggestions = st.checkbox(
        "📚 Curated learning resources",
        value=True if career_level == "Student/Fresher" else False,
        help="Access hand-picked online courses, tutorials, and certifications for skill development"
    )
    
    show_project_ideas = st.checkbox(
        "💡 Portfolio project ideas",
        value=True if career_level == "Student/Fresher" else False,
        help="Practical project suggestions to demonstrate skills and build your portfolio"
    )
    
    show_entry_level_tips = st.checkbox(
        "🚀 Career launch strategies",
        value=True if career_level == "Student/Fresher" else False,
        help="Expert tips and strategies for landing your first job or internship"
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
    
    show_detailed_comparison = st.checkbox(
        "🔍 Show detailed keyword analysis",
        value=False,
        help="Deep dive into keyword frequency and distribution patterns for advanced optimization"
    )
    
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
<div class="main-header">
    <h1>🧾 AI Resume Grader</h1>
    <p>Get AI-powered analysis of your resume against job requirements</p>
</div>
""", unsafe_allow_html=True)

# Create two columns for better layout
col1, col2 = st.columns([1, 1], gap="large")

# Initialize variables to prevent NameError
uploaded_resume = None
job_description = None

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
    
    if uploaded_resume:
        # Check file size (10MB limit)
        if uploaded_resume.size > 10 * 1024 * 1024:  # 10MB in bytes
            st.error("❌ File size too large! Please upload a file smaller than 10MB.")
            st.stop()
        
        file_info = get_file_info(uploaded_resume)
        file_type_icon = {
            "application/pdf": "📕",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📘",
            "text/plain": "📄"
        }.get(uploaded_resume.type, "📁")
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                    padding: 1.5rem; border-radius: 15px; margin: 1rem 0; 
                    border-left: 4px solid #28a745; box-shadow: 0 2px 8px rgba(40,167,69,0.1);'>
            <div style='display: flex; align-items: center; margin-bottom: 0.5rem;'>
                <span style='font-size: 1.5rem; margin-right: 0.5rem;'>{file_type_icon}</span>
                <strong style='color: #155724;'>✅ File uploaded successfully!</strong>
            </div>
            <div style='color: #155724; font-size: 0.9rem;'>
                📁 <strong>{file_info['name']}</strong><br>
                📊 Size: {file_info['size']}<br>
                🔧 Type: {file_info['type']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Process file immediately and cache result
        file_bytes = uploaded_resume.read()
        file_hash = get_text_hash(file_bytes.decode('utf-8', errors='ignore') if uploaded_resume.type == 'text/plain' else str(file_bytes))
        
        # Only reprocess if file changed
        if st.session_state.last_resume_hash != file_hash:
            with st.spinner("📖 Processing resume..."):
                # Enhanced progress tracking
                progress_container = st.container()
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("🔍 Reading file...")
                    progress_bar.progress(25)
                    
                    if uploaded_resume.type == "application/pdf":
                        resume_text = extract_text_from_pdf(file_bytes, uploaded_resume.name)
                    elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        resume_text = extract_text_from_docx(file_bytes, uploaded_resume.name)
                    else:
                        resume_text = extract_text_from_txt(file_bytes, uploaded_resume.name)
                    
                    status_text.text("🧠 Analyzing content...")
                    progress_bar.progress(75)
                    
                    st.session_state.processed_resume = resume_text
                    st.session_state.last_resume_hash = file_hash
                    
                    status_text.text("✅ Processing complete!")
                    progress_bar.progress(100)
                    
                # Clear progress indicators after a moment
                import time
                time.sleep(0.5)
                progress_container.empty()
                
                st.success("✅ Resume processed successfully!")
        else:
            st.info("📋 Resume already processed - using cached result.")
        
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

# Job Description Section
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
        placeholder="""Copy and paste the complete job posting here...

Example job posting structure:
• Job Title: Software Engineer
• Required Skills: Python, JavaScript, SQL
• Experience: 2+ years with web frameworks
• Education: Bachelor's in Computer Science
• Responsibilities: Build web applications, collaborate with team
• Nice to have: Cloud experience, Docker, Git

The more detailed the job posting, the better your analysis results!""",
        label_visibility="collapsed",
        key="job_description_input"
    )
    
    if job_description:
        word_count = len(job_description.split())
        char_count = len(job_description)
        
        # Enhanced validation with better feedback
        if word_count < 10:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                        padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                        border-left: 4px solid #ffc107;'>
                <strong>⚠️ Job description seems short</strong><br>
                <span style='color: #856404;'>Consider adding more details about required skills, responsibilities, and qualifications for better analysis.</span>
            </div>
            """, unsafe_allow_html=True)
        elif word_count > 2000:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); 
                        padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                        border-left: 4px solid #17a2b8;'>
                <strong>📝 Comprehensive job description!</strong><br>
                <span style='color: #0c5460;'>Great detail! This will provide excellent analysis results.</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
                        padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                        border-left: 4px solid #28a745;'>
                <strong>✅ Perfect length for analysis!</strong><br>
                <span style='color: #155724;'>This job description provides good detail for accurate matching.</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Enhanced stats display
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                    border: 1px solid #dee2e6;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='color: #495057;'><strong>📊 Content Analysis:</strong></span>
                <div>
                    <span style='background: #007bff; color: white; padding: 0.2rem 0.5rem; border-radius: 10px; margin: 0 0.2rem; font-size: 0.8rem;'>
                        {word_count} words
                    </span>
                    <span style='background: #6c757d; color: white; padding: 0.2rem 0.5rem; border-radius: 10px; margin: 0 0.2rem; font-size: 0.8rem;'>
                        {char_count} chars
                    </span>
                </div>
            </div>
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

# Quick start guide for first-time users
if not uploaded_resume and not job_description:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                padding: 2rem; border-radius: 20px; margin: 2rem 0; text-align: center;
                border: 1px solid #bbdefb; box-shadow: 0 4px 15px rgba(33,150,243,0.1);'>
        <h3 style='color: #1565c0; margin: 0 0 1rem 0; font-size: 1.4rem;'>🚀 Quick Start Guide</h3>
        <div style='display: flex; justify-content: space-around; margin: 1rem 0;'>
            <div style='flex: 1; margin: 0 1rem;'>
                <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                    <span style='font-size: 2rem;'>📄</span>
                </div>
                <strong style='color: #1976d2;'>1. Upload Resume</strong>
                <p style='color: #1976d2; margin: 0.5rem 0 0 0; font-size: 0.9rem;'>PDF, DOCX, or TXT format</p>
            </div>
            <div style='flex: 1; margin: 0 1rem;'>
                <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                    <span style='font-size: 2rem;'>💼</span>
                </div>
                <strong style='color: #1976d2;'>2. Paste Job Description</strong>
                <p style='color: #1976d2; margin: 0.5rem 0 0 0; font-size: 0.9rem;'>Complete job posting text</p>
            </div>
            <div style='flex: 1; margin: 0 1rem;'>
                <div style='background: white; padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
                    <span style='font-size: 2rem;'>🎯</span>
                </div>
                <strong style='color: #1976d2;'>3. Get Results</strong>
                <p style='color: #1976d2; margin: 0.5rem 0 0 0; font-size: 0.9rem;'>Instant skill match analysis</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
            # Enhanced analysis progress
            analysis_container = st.container()
            with analysis_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🔍 Extracting resume keywords...")
                progress_bar.progress(20)
                resume_keywords = extract_keywords_cached(resume_text, min_keyword_length)
                
                status_text.text("🎯 Processing job requirements...")
                progress_bar.progress(40)
                jd_keywords = extract_keywords_cached(job_desc_text, min_keyword_length)
                
                status_text.text("🤝 Finding skill matches...")
                progress_bar.progress(60)
                matched_keywords = resume_keywords.intersection(jd_keywords)
                missing_keywords = jd_keywords - resume_keywords
                
                status_text.text("📊 Calculating match score...")
                progress_bar.progress(80)
                match_score = round(len(matched_keywords) / len(jd_keywords) * 100, 2) if jd_keywords else 0.0
                
                status_text.text("🎓 Analyzing skill gaps...")
                progress_bar.progress(90)
                skill_gap_analysis = analyze_skill_gaps(resume_keywords, jd_keywords, career_level)
                
                status_text.text("✅ Analysis complete!")
                progress_bar.progress(100)
                
            # Clear progress after completion
            import time
            time.sleep(0.3)
            analysis_container.empty()
        
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
                # Keywords overview with expand/collapse control
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, rgba(40, 167, 69, 0.15) 0%, rgba(40, 167, 69, 0.05) 100%); 
                            padding: 1.5rem; border-radius: 15px; margin: 1.5rem 0; 
                            border: 1px solid rgba(40, 167, 69, 0.2);'>
                    <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                        <h3 style='color: #28a745; margin: 0; font-size: 1.3rem; font-weight: 600;'>
                            ✅ Matched Skills & Keywords
                        </h3>
                        <span style='margin-left: auto; background: #28a745; color: white; 
                                    padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500;'>
                            {len(matched_keywords)} matches
                        </span>
                    </div>
                    <p style='color: #155724; margin: 0; font-size: 0.95rem; line-height: 1.4;'>
                        Skills from your resume that align with job requirements
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                matched_list = sorted(list(matched_keywords))
                
                # Expandable keywords display
                with st.expander("🔍 View All Matched Keywords", expanded=True):
                    if matched_keywords:
                        # Display as organized grid of chips
                        cols = st.columns(4)
                        for i, keyword in enumerate(matched_list):
                            with cols[i % 4]:
                                st.markdown(f"""
                                <div style='background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                                            color: white; padding: 0.5rem 1rem; border-radius: 25px; 
                                            margin: 0.25rem 0; text-align: center; font-size: 0.85rem; 
                                            font-weight: 500; box-shadow: 0 2px 4px rgba(40, 167, 69, 0.2);'>
                                    {keyword}
                                </div>
                                """, unsafe_allow_html=True)
                
                # Enhanced Export Toolbar
                st.markdown("""
                <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                            padding: 1rem; border-radius: 12px; margin: 1.5rem 0; 
                            border: 1px solid #dee2e6;'>
                    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;'>
                        <h4 style='color: #495057; margin: 0; font-size: 1rem; font-weight: 600;'>
                            📥 Export Analysis
                        </h4>
                    </div>
                    <p style='color: #6c757d; margin: 0; font-size: 0.85rem;'>
                        Download your results for future reference
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Export buttons in columns
                export_col1, export_col2 = st.columns(2)
                
                with export_col1:
                    if st.button("� Matched Keywords", help="Download matched keywords as CSV", use_container_width=True):
                        matched_df = pd.DataFrame(matched_list, columns=["Matched Keywords"])
                        csv = matched_df.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv,
                            file_name=f"matched_keywords_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                with export_col2:
                    if st.button("📊 Full Report", help="Download complete analysis report", use_container_width=True):
                        # Create analysis summary
                        analysis_summary = f"""AI Resume Grader Analysis Report
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
                            label="⬇️ Download Report",
                            data=analysis_summary,
                            file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
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
                # Missing keywords overview with expand/collapse control
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, rgba(220, 53, 69, 0.15) 0%, rgba(220, 53, 69, 0.05) 100%); 
                            padding: 1.5rem; border-radius: 15px; margin: 1.5rem 0; 
                            border: 1px solid rgba(220, 53, 69, 0.2);'>
                    <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                        <h3 style='color: #dc3545; margin: 0; font-size: 1.3rem; font-weight: 600;'>
                            ⚠️ Skill Gaps to Address
                        </h3>
                        <span style='margin-left: auto; background: #dc3545; color: white; 
                                    padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500;'>
                            {len(missing_keywords)} gaps
                        </span>
                    </div>
                    <p style='color: #721c24; margin: 0; font-size: 0.95rem; line-height: 1.4;'>
                        Consider strengthening these skills to improve your match score
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                missing_list = sorted(list(missing_keywords))
                
                # Expandable missing keywords display
                with st.expander(f"🎯 View Missing Skills ({len(missing_list)} total)", expanded=False):
                    if missing_list:
                        # Display as organized grid of chips
                        cols = st.columns(4)
                        for i, keyword in enumerate(missing_list):
                            with cols[i % 4]:
                                st.markdown(f"""
                                <div style='background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); 
                                            color: white; padding: 0.5rem 1rem; border-radius: 25px; 
                                            margin: 0.25rem 0; text-align: center; font-size: 0.85rem; 
                                            font-weight: 500; box-shadow: 0 2px 4px rgba(220, 53, 69, 0.2);'>
                                    {keyword}
                                </div>
                                """, unsafe_allow_html=True)
                
                st.markdown("""
                <div style='background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%); 
                            padding: 1rem; border-radius: 10px; margin: 1rem 0; 
                            border-left: 4px solid #17a2b8;'>
                    <p style='color: #0c5460; margin: 0; font-weight: 500;'>
                        💡 Consider adding these keywords to improve your match score!
                    </p>
                </div>
                """, unsafe_allow_html=True)
        
        # Enhanced Primary CTA Section
        if matched_keywords or missing_keywords:
            st.markdown("---")
            st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 20px; margin: 2rem 0; text-align: center; 
                        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);'>
                <h2 style='color: white; margin: 0 0 1rem 0; font-size: 1.5rem; font-weight: 700;'>
                    🚀 Ready to Optimize Your Resume?
                </h2>
                <p style='color: rgba(255, 255, 255, 0.9); margin: 0 0 1.5rem 0; font-size: 1.1rem; line-height: 1.5;'>
                    Use the insights above to strengthen your resume and increase your chances of landing interviews
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            cta_col1, cta_col2, cta_col3 = st.columns(3)
            
            with cta_col1:
                if st.button("📝 Update Resume", help="Revise your resume based on recommendations", use_container_width=True):
                    st.balloons()
                    st.success("💡 **Next Steps:**\n- Add missing keywords naturally\n- Highlight matched skills prominently\n- Tailor language to job requirements")
            
            with cta_col2:
                if st.button("🎯 Try Another Job", help="Analyze against a different job description", use_container_width=True):
                    st.rerun()
            
            with cta_col3:
                if st.button("📊 Get Full Report", help="Download comprehensive analysis", use_container_width=True):
                    st.info("📥 Use the Export Analysis section above to download your results!")
        
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
    # Enhanced status indicator
    if uploaded_resume and not job_description:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                    padding: 1.5rem; border-radius: 15px; margin: 2rem 0; text-align: center;
                    border: 1px solid #ffeaa7;'>
            <h3 style='color: #856404; margin: 0 0 0.5rem 0;'>📋 Almost Ready!</h3>
            <p style='color: #856404; margin: 0; font-size: 1.1rem;'>
                ✅ Resume uploaded successfully<br>
                ⏳ Please enter a job description to start the analysis
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif job_description and not uploaded_resume:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
                    padding: 1.5rem; border-radius: 15px; margin: 2rem 0; text-align: center;
                    border: 1px solid #ffeaa7;'>
            <h3 style='color: #856404; margin: 0 0 0.5rem 0;'>📋 Almost Ready!</h3>
            <p style='color: #856404; margin: 0; font-size: 1.1rem;'>
                ✅ Job description entered<br>
                ⏳ Please upload your resume to start the analysis
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("📋 Please upload both a resume and enter a job description to see the analysis.")

# Enhanced Footer
st.markdown("---")

# Create footer using native Streamlit components for better reliability
st.markdown("### 🧾 AI Resume Grader")
st.markdown("*Helping job seekers optimize their resumes with AI-powered analysis*")

# Features grid using columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("📊")
    st.markdown("**Smart Analysis**")
    st.markdown("*AI-powered keyword matching*")

with col2:
    st.markdown("🎓")
    st.markdown("**Student Friendly**")
    st.markdown("*Special features for freshers*")

with col3:
    st.markdown("🚀")
    st.markdown("**Career Growth**")
    st.markdown("*Learning recommendations*")

with col4:
    st.markdown("📥")
    st.markdown("**Export Results**")
    st.markdown("*Download analysis reports*")

st.markdown("---")
st.markdown("Made with ❤️ using Streamlit, spaCy, and Plotly | [View on GitHub](https://github.com/jainamshah2028/ai-resume-grader) | Version 2.0")
