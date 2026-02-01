"""
Shared styling for minimal clean design across all pages
"""
import streamlit as st
from utils.sidebar_nav import inject_sidebar_collapsed


def apply_minimal_style():
    """Apply minimal clean design CSS and collapsed icon-only sidebar."""
    inject_sidebar_collapsed()
    st.markdown("""
    <style>
        .main {
            padding: 4rem 6rem;
            max-width: 1400px;
        }
        
        h1 {
            font-size: 3.5rem;
            font-weight: 700;
            color: #1a1a1a;
            letter-spacing: -0.03em;
            margin-bottom: 0.25rem;
        }
        
        h3 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 3rem;
            margin-bottom: 1.5rem;
        }
        
        .stCaption {
            color: #6b6b6b;
            font-size: 0.9rem;
        }
        
        .stButton > button {
            background-color: #1a1a1a;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.6rem 1.5rem;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #000;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 4rem 0;
        }
        
        .stProgress > div > div > div {
            background-color: #22c55e;
        }
    </style>
    """, unsafe_allow_html=True)
