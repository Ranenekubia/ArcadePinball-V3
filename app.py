# =============================================================================
# app.py - MAIN ENTRY POINT
# =============================================================================
# PURPOSE:
#   This is the main entry point for the Streamlit application.
#   When you run `streamlit run app.py`, this file executes first.
#
# WHAT IT DOES:
#   1. Configures the Streamlit page (title, icon, layout)
#   2. Redirects to the Dashboard page
#
# HOW STREAMLIT MULTI-PAGE APPS WORK:
#   - app.py is the "home" page
#   - Files in the "pages/" folder become additional pages
#   - Streamlit automatically creates a sidebar menu
#   - Page order is determined by filename (numbers/emojis first)
#
# TO RUN THE APP:
#   Open terminal in this folder and run:
#   streamlit run app.py
# =============================================================================

import streamlit as st
from utils.sidebar_nav import inject_sidebar_collapsed

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
# This MUST be the first Streamlit command in the script!
# It sets up the browser tab title, favicon, and layout.

st.set_page_config(
    page_title="Arcade Pinball V3",  # Browser tab title
    page_icon="🎱",                   # Favicon (emoji or image path)
    layout="wide"                     # Use full width of browser
)

# Sidebar style (collapsed icon bar) so it applies on every load
inject_sidebar_collapsed()

# -----------------------------------------------------------------------------
# REDIRECT TO DASHBOARD
# -----------------------------------------------------------------------------
# We want users to land on the Dashboard, not this blank page.
# st.switch_page() navigates to another page in the app.

st.switch_page("pages/1_Dashboard.py")

# =============================================================================
# LEARNING NOTES: STREAMLIT BASICS
# =============================================================================
#
# WHAT IS STREAMLIT?
#   Streamlit is a Python library for building web apps quickly.
#   You write Python code, and Streamlit turns it into a web interface.
#   No HTML, CSS, or JavaScript needed!
#
# HOW IT WORKS:
#   1. You write Python code with Streamlit commands
#   2. Streamlit runs your code top-to-bottom
#   3. Each st.xxx() command creates a UI element
#   4. When user interacts, the whole script re-runs
#
# COMMON COMMANDS:
#   st.title("Hello")        → Big title
#   st.write("Text")         → Text/markdown
#   st.button("Click me")    → Button
#   st.text_input("Name")    → Text input field
#   st.dataframe(df)         → Display a DataFrame as table
#   st.metric("Sales", 100)  → Display a metric with optional delta
#
# LAYOUT:
#   col1, col2 = st.columns(2)  → Create 2 columns
#   with col1:
#       st.write("Left side")
#   with col2:
#       st.write("Right side")
#
# STATE:
#   Streamlit re-runs the whole script on each interaction.
#   To persist data between runs, use st.session_state:
#   st.session_state['my_var'] = "value"
#
# =============================================================================


