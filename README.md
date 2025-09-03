
# 🧾 AI Resume Grader

Upload your resume and job description to get an intelligent skill match score using advanced NLP analysis.

## 🚀 Features
- **Multi-format Resume Upload**: Support for PDF, TXT, and DOCX files
- **Interactive Job Description Input**: Paste or type job descriptions
- **Advanced Keyword Extraction**: Intelligent keyword extraction using spaCy NLP
- **Real-time Match Scoring**: Calculate percentage match between resume and job requirements
- **Visual Analytics**: Interactive gauge charts and data visualizations
- **Keyword Analysis**: View matched, missing, and frequency analysis of keywords
- **File Preview**: Preview uploaded resume content before processing
- **Optimized Performance**: Cached processing for faster analysis

## 📦 Tech Stack
- **Python** - Core programming language
- **Streamlit** - Web application framework
- **spaCy** - Natural Language Processing
- **Plotly** - Interactive data visualizations
- **PyMuPDF** - PDF text extraction
- **python-docx** - Word document processing
- **Pandas** - Data analysis and manipulation

## 🛠️ How to Run

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Download spaCy Model**
```bash
python -m spacy download en_core_web_sm
```

3. **Run the Application**
```bash
streamlit run app.py
```

4. **Access the App**
   - Open your browser to `http://localhost:8501`
   - Upload your resume (PDF, TXT, or DOCX)
   - Paste the job description
   - View your skill match analysis!

## 🎯 How It Works
1. **Document Processing**: Extracts text from uploaded resume files
2. **NLP Analysis**: Uses spaCy to tokenize and extract meaningful keywords
3. **Keyword Matching**: Compares resume keywords with job description requirements
4. **Score Calculation**: Generates a percentage match score based on keyword overlap
5. **Visual Results**: Displays results with interactive charts and detailed breakdowns

## 📸 Demo
The application provides an intuitive web interface with:
- Clean file upload section with drag-and-drop support
- Real-time text area for job description input
- Interactive gauge chart showing match percentage
- Detailed keyword analysis tables
- Statistics dashboard with key metrics

## 🔍 Key Metrics Displayed
- **Match Score**: Percentage of job requirements met by resume
- **Resume Keywords**: Total unique keywords found in resume
- **Job Requirements**: Total keywords in job description
- **Matched Keywords**: Keywords present in both documents
- **Missing Keywords**: Important skills/requirements not found in resume

## 📚 Technical Learnings
- **Advanced NLP Processing**: Implemented spaCy for tokenization, lemmatization, and intelligent keyword extraction
- **Multi-format Document Handling**: Built robust text extraction for PDF, DOCX, and TXT files
- **Performance Optimization**: Used Streamlit caching for improved response times
- **Interactive Data Visualization**: Created dynamic charts with Plotly for better user experience
- **Scalable Architecture**: Designed modular code structure for easy maintenance and extension
