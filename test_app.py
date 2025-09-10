import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import io
import hashlib
import re
import time

st.set_page_config(
    page_title="AI Resume Grader - Test",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 AI Resume Grader - Test Version")
st.write("Testing basic functionality...")

# Test basic imports
try:
    import fitz
    st.success("✅ PyMuPDF (fitz) imported successfully")
except ImportError as e:
    st.error(f"❌ PyMuPDF import failed: {e}")

try:
    import spacy
    st.success("✅ spaCy imported successfully")
except ImportError as e:
    st.error(f"❌ spaCy import failed: {e}")

try:
    import docx
    st.success("✅ python-docx imported successfully")
except ImportError as e:
    st.error(f"❌ python-docx import failed: {e}")

# Test spaCy model loading
try:
    nlp = spacy.load("en_core_web_sm")
    st.success("✅ spaCy English model loaded successfully")
except Exception as e:
    st.error(f"❌ spaCy model loading failed: {e}")

# Test file upload
uploaded_file = st.file_uploader("Test file upload", type=["pdf", "txt", "docx"])
if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name}")

# Test text area
text_input = st.text_area("Test text input", "This is a test...")
if text_input:
    st.success(f"✅ Text input received: {len(text_input)} characters")

st.write("If you can see this page, Streamlit is working correctly!")
