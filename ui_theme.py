import os
import streamlit as st
import locales

def get_dark_theme_css():
    bg_color = "#090d16"
    card_bg = "#111827"
    card_border = "#1f2937"
    text_color = "#f9fafb"
    subtext_color = "#9ca3af"
    input_bg = "#1f2937"
    input_border = "#374151"

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Force Dark Theme on Root and All Containers */
    html, body, [class*="css"], .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stToolbar"], 
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    .main, .block-container {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    /* Hide transparent header artifacts */
    [data-testid="stHeader"] {{
        background-color: rgba(9, 13, 22, 0.95) !important;
        backdrop-filter: blur(10px) !important;
    }}

    .main .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1280px !important;
    }}

    /* Global Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: #0d1117 !important;
        border-right: 1px solid #161b22 !important;
    }}
    
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: #c9d1d9 !important;
    }}

    /* Custom App Header Banner */
    .cosmo-header {{
        background: linear-gradient(135deg, #1e1e38 0%, #111827 100%);
        border: 1px solid #2d3748;
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }}

    .cosmo-header-left {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}

    .cosmo-logo-img {{
        width: 48px;
        height: 48px;
        border-radius: 12px;
        object-fit: cover;
        border: 2px solid #3b82f6;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.5);
    }}

    .cosmo-title {{
        font-size: 22px;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
        letter-spacing: -0.5px;
    }}

    .cosmo-sub {{
        font-size: 13px;
        color: #9ca3af !important;
        margin-top: 2px;
    }}

    .user-badge {{
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
        color: #60a5fa !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }}

    /* Forms, Cards & Content Sections */
    div[data-testid="stForm"], div.stForm {{
        background-color: {card_bg} !important;
        border: 1px solid {card_border} !important;
        border-radius: 14px !important;
        padding: 20px !important;
    }}

    /* Inputs, Selectboxes, Textareas, Date/Time Inputs */
    .stTextInput input,
    .stSelectbox div[role="button"],
    .stMultiSelect div[role="button"],
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] {{
        background-color: {input_bg} !important;
        color: {text_color} !important;
        border-radius: 10px !important;
        border: 1px solid {input_border} !important;
    }}
    
    /* Popovers, Dropdown Menus & Modals */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    div[data-baseweb="tooltip"],
    ul[role="listbox"] {{
        background-color: {card_bg} !important;
        border: 1px solid {card_border} !important;
        color: {text_color} !important;
        border-radius: 10px !important;
    }}
    
    li[role="option"] {{
        color: {text_color} !important;
        background-color: {card_bg} !important;
    }}
    
    li[role="option"]:hover, li[aria-selected="true"] {{
        background-color: #2563eb !important;
        color: #ffffff !important;
    }}

    /* Buttons */
    .stButton > button {{
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        border: 1px solid #3b82f6 !important;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.2s ease !important;
    }}

    .stButton > button:hover {{
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        border-color: #60a5fa !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4) !important;
    }}

    /* Expanders & Accordions */
    .streamlit-expanderHeader, div[data-testid="stExpander"] {{
        background-color: {card_bg} !important;
        border-radius: 10px !important;
        color: {text_color} !important;
        border: 1px solid {card_border} !important;
    }}
    
    div[data-testid="stExpanderDetails"] {{
        background-color: #0d121f !important;
        border-top: 1px solid {card_border} !important;
    }}
    
    /* Dataframes & Tables */
    .stDataFrame, div[data-testid="stTable"], div[data-testid="stDataFrame"] {{
        background-color: {card_bg} !important;
        border-radius: 12px !important;
        border: 1px solid {card_border} !important;
    }}

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: #111827 !important;
        padding: 6px !important;
        border-radius: 12px !important;
        border: 1px solid #1f2937 !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 42px !important;
        white-space: pre !important;
        border-radius: 8px !important;
        color: #9ca3af !important;
        font-weight: 600 !important;
        padding: 0 16px !important;
        background-color: transparent !important;
    }}

    .stTabs [aria-selected="true"] {{
        background-color: #2563eb !important;
        color: #ffffff !important;
    }}

    /* Metrics Cards */
    div[data-testid="stMetric"] {{
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        padding: 14px 18px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: #9ca3af !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: #ffffff !important;
        font-weight: 800 !important;
    }}
    
    /* Alerts & Notifications Dark Mode Overrides */
    div[data-testid="stNotification"], .stAlert {{
        background-color: #111827 !important;
        border-radius: 10px !important;
        border: 1px solid #1f2937 !important;
        color: {text_color} !important;
    }}
    </style>
    """


def inject_theme():
    st.session_state["dark_mode"] = True
    st.markdown(get_dark_theme_css(), unsafe_allow_html=True)
    st.markdown("""
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#090d16">
        <link rel="manifest" href="/manifest.json">
        <link rel="apple-touch-icon" href="/cosmo_logo.jpg">
    """, unsafe_allow_html=True)


def render_top_header(title="Cosmo CRM", subtitle="", user_name="", user_role="", user_email=""):
    logo_html = ""
    if os.path.exists("cosmo_logo.jpg"):
        logo_html = '<img src="app/static/cosmo_logo.jpg" class="cosmo-logo-img" alt="Logo" onerror="this.style.display=\'none\'">'
    
    st.markdown(f"""
        <div class="cosmo-header">
            <div class="cosmo-header-left">
                {logo_html}
                <div>
                    <h2 class="cosmo-title">🧼 {title}</h2>
                    <div class="cosmo-sub">{subtitle}</div>
                </div>
            </div>
            <div class="user-badge">
                👤 <b>{user_name}</b> ({user_role})
            </div>
        </div>
    """, unsafe_allow_html=True)


