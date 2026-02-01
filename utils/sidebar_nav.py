"""
Collapsed sidebar with hover expansion.
Uses outline/stroke SVG icons (Lucide-style) and custom nav with st.switch_page for navigation.
"""
import streamlit as st

SIDEBAR_BG = "#6B2D3C"

# Lucide-style outline SVG icons (24x24, stroke 2, no fill)
ICONS_SVG = {
    "layout-grid": '<path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>',
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "dollar-sign": '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "handshake": '<path d="M11 12h2a2 2 0 1 0 0-4h-3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h1"/><path d="M12 12v10"/><path d="M12 12a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-5"/><path d="M12 12a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h5"/>',
    "bug": '<path d="m8 2 1.88 1.88"/><path d="M14.12 3.88 16 2"/><path d="M9 7.13v-1a3.003 3.003 0 1 1 6 0v1"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6"/><path d="M12 20v-9"/><path d="M6 13h12"/>',
}

# Page definitions: (icon key, label, path) - ASCII paths for reliable navigation
PAGES = [
    ("home", "Dashboard", "pages/1_Dashboard.py"),
    ("upload", "Import", "pages/2_Import.py"),
    ("link", "Match", "pages/3_Match.py"),
    ("music", "Shows", "pages/4_Shows.py"),
    ("send", "Outgoing", "pages/5_Outgoing.py"),
    ("dollar-sign", "Settlement", "pages/6_Settlement.py"),
    ("handshake", "Handshakes", "pages/7_Handshakes.py"),
    ("bug", "Debug", "pages/8_Debug.py"),
]


def svg_icon(name: str, size: int = 24, stroke_width: float = 2) -> str:
    """Return inline SVG for a Lucide-style outline icon."""
    path = ICONS_SVG.get(name, ICONS_SVG["layout-grid"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'''


def get_sidebar_css():
    """CSS for collapsed sidebar (70px) that expands on hover/focus; delay collapse to avoid glitch on click."""
    return f"""
<style>
    /* Collapsed: 70px. Delay collapse so click doesn't trigger immediate shrink. */
    [data-testid="stSidebar"] {{
        width: 70px !important;
        min-width: 70px !important;
        transition: width 0.25s ease 0.35s, min-width 0.25s ease 0.35s;
        background-color: {SIDEBAR_BG} !important;
        overflow-x: hidden !important;
    }}
    
    /* Expanded: on hover OR when any child has focus (keeps expanded during/after click) */
    [data-testid="stSidebar"]:hover,
    [data-testid="stSidebar"]:focus-within {{
        width: 250px !important;
        min-width: 250px !important;
        transition: width 0.25s ease 0s, min-width 0.25s ease 0s;
    }}
    
    /* Sidebar content: left/right padding so icons are not cut off */
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
        padding-left: 14px !important;
        padding-right: 14px !important;
    }}
    
    /* Hide default Streamlit nav */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="column"] {{
        padding: 0 !important;
    }}
    
    [data-testid="stSidebar"] .nav-icon-wrap {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 4px 0 !important;
    }}
    
    [data-testid="stSidebar"] .nav-icon-wrap svg {{
        color: rgba(255,255,255,0.9) !important;
    }}
    
    /* Nav button styling */
    [data-testid="stSidebar"] .stButton {{
        width: 100% !important;
        margin: 0 !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button {{
        width: 100% !important;
        padding: 12px 8px !important;
        margin: 0 !important;
        border-radius: 8px !important;
        min-height: 48px !important;
        background: transparent !important;
        border: none !important;
        color: rgba(255,255,255,0.9) !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: rgba(255,255,255,0.12) !important;
    }}
    
    /* When collapsed only: hide button text (expanded = hover OR focus-within) */
    [data-testid="stSidebar"]:not(:hover):not(:focus-within) .stButton > button {{
        color: transparent !important;
        overflow: hidden !important;
    }}
    
    [data-testid="stSidebar"]:not(:hover):not(:focus-within) .stButton > button > div {{
        opacity: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
    }}
    
    [data-testid="stSidebar"]:hover .stButton > button > div,
    [data-testid="stSidebar"]:focus-within .stButton > button > div {{
        opacity: 1 !important;
        width: auto !important;
    }}
</style>
"""


# Session key for deferred navigation (avoids "st.rerun/switch_page in callback is a no-op")
NAV_TARGET_KEY = "nav_target"


def _go(path: str) -> None:
    """Callback: set target page in session state. Actual switch happens on next run (top-level)."""
    st.session_state[NAV_TARGET_KEY] = path


def inject_sidebar_collapsed():
    """Inject CSS and render custom nav with outline SVG icons + buttons. Uses session state for nav (callbacks cannot call st.switch_page)."""
    # Top-level switch: if a nav button was clicked last run, switch now (not inside callback)
    target = st.session_state.pop(NAV_TARGET_KEY, None)
    if target:
        st.switch_page(target)
        return

    st.markdown(get_sidebar_css(), unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
        for i, (icon_key, label, path) in enumerate(PAGES):
            col_icon, col_link = st.columns([1, 3], gap="small")
            with col_icon:
                icon_svg = svg_icon(icon_key, size=24, stroke_width=2)
                st.markdown(f'<div class="nav-icon-wrap">{icon_svg}</div>', unsafe_allow_html=True)
            with col_link:
                st.button(label, key=f"nav_{i}", use_container_width=True, on_click=_go, args=(path,))
