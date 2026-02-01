"""
Theme styling for app layout: maroon sidebar, top bar, welcome banner.
"""
import streamlit as st
from utils.sidebar_nav import inject_sidebar_collapsed

# Maroon/burgundy from reference
SIDEBAR_BG = "#6B2D3C"
HEADER_BG = "#6B2D3C"
BANNER_GRADIENT = "linear-gradient(135deg, #e8a0a0 0%, #d46a6a 25%, #c94c4c 50%, #a83232 100%)"


def apply_app_theme():
    """Apply maroon sidebar, top bar, and welcome banner styling."""
    inject_sidebar_collapsed()
    st.markdown(f"""
    <style>
        /* Sidebar: maroon, white text */
        [data-testid="stSidebar"] {{
            background-color: {SIDEBAR_BG};
        }}
        [data-testid="stSidebar"] .stMarkdown {{
            color: #fff;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdown"] p {{
            color: #fff;
        }}
        [data-testid="stSidebar"] label {{
            color: #fff !important;
        }}
        
        /* Top bar: first row in main gets maroon background */
        .main div[data-testid="stHorizontalBlock"]:first-of-type {{
            background-color: {HEADER_BG};
            padding: 0.75rem 1.5rem;
            margin-left: -3rem;
            margin-right: -3rem;
            margin-top: -2rem;
            margin-bottom: 1rem;
            border-radius: 0;
        }}
        .main div[data-testid="stHorizontalBlock"]:first-of-type [data-testid="stTextInput"] input {{
            background-color: #fff !important;
        }}
        .main div[data-testid="stHorizontalBlock"]:first-of-type .stMarkdown p {{
            color: #fff !important;
        }}
        
        /* Welcome banner */
        .welcome-banner {{
            background: {BANNER_GRADIENT};
            padding: 2rem 2.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .welcome-banner h2 {{
            color: #fff;
            margin: 0;
            font-size: 1.75rem;
            font-weight: 700;
        }}
        
        /* Content card */
        .content-card {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }}
        
        /* Search input in top bar */
        .top-bar .stTextInput > div > div > input {{
            background-color: #fff !important;
            border-radius: 8px;
        }}
    </style>
    """, unsafe_allow_html=True)
