
# 🧾 AI Resume Grader

An advanced AI-powered resume analysis tool that helps job seekers optimize their resumes for specific job postings. Upload your resume and paste a job description to get detailed insights, match scores, and actionable recommendations.

## ✨ Latest Updates (August 2025)

### 🎨 Enhanced UI/UX
- **Modern Design**: Glassmorphism effects with gradient backgrounds
- **Colorful Upload Sections**: 
  - Resume upload: Blue-purple gradient
  - Job description: Pink-red gradient
- **Responsive Layout**: Mobile-friendly design with improved typography
- **Native Streamlit Components**: Replaced heavy HTML/CSS with optimized Streamlit widgets

### 🐛 Bug Fixes
- Fixed `KeyError: 'len(matched_keywords)'` in analysis display
- Corrected malformed f-string expressions
- Improved error handling and validation

### ⚡ Performance Improvements
- Lazy loading of heavy libraries (spaCy, FAISS)
- Intelligent caching system
- Optimized NLP processing pipeline

## 🚀 Features

### Core Functionality
- **Multi-format Support**: Upload PDF, DOCX, or TXT resume files (up to 10MB)
- **Smart Text Extraction**: Advanced parsing for different file formats
- **AI-Powered Analysis**: NLP-based keyword extraction and matching
- **Real-time Scoring**: Instant match percentage calculation
- **Career Level Detection**: Automatic identification of experience level

### Advanced Analytics
- **Keyword Visualization**: Interactive display of matched and missing skills
- **Detailed Reports**: Comprehensive analysis summaries
- **Export Functionality**: Download analysis reports as text files
- **Skill Gap Analysis**: Identify areas for resume improvement
- **Industry-specific Insights**: Tailored recommendations based on job requirements

### User Experience
- **Progress Indicators**: Real-time processing feedback
- **Interactive UI**: Expandable sections and intuitive navigation
- **File Upload Validation**: Size and format checking
- **Error Recovery**: Graceful handling of edge cases
- **Mobile Responsive**: Works seamlessly on all devices

## 📦 Tech Stack

### Core Technologies
- **Python 3.8+**: Primary programming language
- **Streamlit**: Web application framework
- **spaCy**: Natural language processing
- **PyMuPDF (fitz)**: PDF text extraction
- **python-docx**: Word document processing

### AI/ML Libraries
- **FAISS**: Vector similarity search
- **OpenAI**: Advanced language models (optional)
- **LangChain**: LLM orchestration
- **Pandas**: Data manipulation
- **Plotly**: Interactive visualizations

### UI/UX
- **Custom CSS**: Modern glassmorphism design
- **Responsive Design**: Mobile-first approach
- **Interactive Components**: Streamlit native widgets

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/jainamshah2028/ai-resume-grader.git
cd ai-resume-grader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run the application
streamlit run app.py
```

### Alternative Setup
```bash
# Direct installation
pip install streamlit spacy pandas python-docx PyMuPDF plotly faiss-cpu

# Download language model
python -m spacy download en_core_web_sm

# Run app
streamlit run app.py
```

## 🎯 How to Use

1. **Upload Resume**: Drag and drop or browse for your PDF/DOCX/TXT resume
2. **Paste Job Description**: Copy the complete job posting into the text area
3. **Analyze**: Click analyze to get instant results
4. **Review Insights**: Explore match scores, keyword analysis, and recommendations
5. **Export Report**: Download detailed analysis for future reference

## � What You Get

### Match Score
- Percentage-based compatibility rating
- Keyword density analysis
- Industry relevance scoring

### Detailed Analytics
- **Matched Skills**: Keywords found in both resume and job description
- **Missing Skills**: Important keywords absent from your resume
- **Career Level**: Automatic detection of experience level
- **Recommendations**: Actionable suggestions for improvement

### Visual Reports
- Interactive keyword clouds
- Progress bars and metrics
- Color-coded skill categories
- Export-ready summaries

## 🔧 Configuration

### Environment Variables (Optional)
```bash
# For advanced AI features
OPENAI_API_KEY=your_openai_key_here
LANGCHAIN_API_KEY=your_langchain_key_here
```

### Customization
- Modify CSS in the app for custom themes
- Adjust scoring algorithms in `utils/text_analysis.py`
- Configure file size limits and supported formats

## 🏗️ Project Structure
```
ai_resume_grader/
├── app.py                 # Main Streamlit application
├── app_backup.py          # Backup version
├── app_simple.py          # Simplified testing version
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── utils/
│   └── text_analysis.py  # NLP processing utilities
├── assets/               # Static files and resources
└── __pycache__/         # Python cache files
```

## 🔍 Technical Details

### NLP Pipeline
1. **Text Extraction**: Multi-format document parsing
2. **Preprocessing**: Cleaning and normalization
3. **Tokenization**: spaCy-based linguistic analysis
4. **Keyword Extraction**: Named entity recognition and skill identification
5. **Similarity Matching**: Vector-based comparison algorithms

### Performance Optimizations
- **Lazy Loading**: Import heavy libraries only when needed
- **Caching**: Streamlit's built-in caching for repeated operations
- **Efficient Processing**: Optimized NLP pipeline for speed
- **Memory Management**: Proper resource cleanup and garbage collection

## 🚀 Recent Improvements

### v2.1.0 (August 2025)
- ✅ Fixed critical KeyError bug
- ✅ Enhanced UI with gradient backgrounds
- ✅ Improved file upload experience
- ✅ Better error handling
- ✅ Performance optimizations

### v2.0.0 (Previous)
- Modern glassmorphism design
- Mobile-responsive layout
- Enhanced analytics dashboard
- Multi-format file support

## 📈 Future Roadmap

- [ ] AI-powered resume suggestions
- [ ] Multiple job comparison
- [ ] Industry-specific templates
- [ ] Resume builder integration
- [ ] API endpoint development
- [ ] Advanced analytics dashboard

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- spaCy team for excellent NLP tools
- Streamlit for the amazing web framework
- Open source community for inspiration and support

## 📞 Support

For questions, suggestions, or issues:
- Create an issue on GitHub
- Contact: [jainamshah2028@gmail.com]
- LinkedIn: [Your LinkedIn Profile]

---

**Made with ❤️ for job seekers worldwide**
