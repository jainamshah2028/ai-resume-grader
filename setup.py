#!/usr/bin/env python3
"""
Post-install script to download spaCy model for Streamlit Cloud deployment
"""
import subprocess
import sys

def install_spacy_model():
    """Download and install spaCy English model"""
    try:
        print("Installing spaCy English model...")
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        print("spaCy model installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not install spaCy model: {e}")
        print("App will use fallback text processing.")
    except Exception as e:
        print(f"Error during spaCy model installation: {e}")

if __name__ == "__main__":
    install_spacy_model()
