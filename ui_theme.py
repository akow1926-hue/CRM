import os
import base64
import streamlit as st

def get_dark_theme_css():
    # Blue & Yellow Palette Tokens
    bg_color = "#070d1e"          # Deep Midnight Blue
    sidebar_bg = "#050914"        # Ultra Dark Navy Sidebar
    card_bg = "#0f1a34"           # Deep Royal Blue-Navy Surface
    card_border = "#1d3566"       # Royal Blue Border
    card_glow_yellow = "rgba(250, 204, 21, 0.25)" # Radiant Yellow Glow
    card_glow_blue = "rgba(37, 99, 235, 0.25)"   # Radiant Blue Glow

    text_color = "#f8fafc"        # Crisp White Text
    subtext_color = "#94a3b8"     # Light Slate Subtext

    input_bg = "#152347"          # Dark Blue Input Background
    input_border = "#2563eb"      # Electric Blue Border

    yellow_primary = "#facc15"    # Bright Radiant Yellow/Gold
    yellow_hover = "#fde047"      # Electric Yellow Hover
    yellow_dark = "#eab308"       # Deep Amber Gold

    blue_primary = "#2563eb"      # Vibrant Royal Blue
    blue_light = "#60a5fa"        # Light Sky Blue Accent
    blue_hover = "#3b82f6"        # Hover Blue

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');

    /* Global Root Styling - Modern Mobile First */
    html, body, [class*="css"], .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stToolbar"], 
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    .main, .block-container {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    /* Top Navigation Header Bar */
    [data-testid="stHeader"] {{
        background: rgba(7, 13, 30, 0.95) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-bottom: 1.5px solid {card_border} !important;
    }}

    .main .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 1320px !important;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 2px solid {card_border} !important;
    }}
    
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: #e2e8f0 !important;
    }}

    /* Custom Header Banner - Vibrant Blue & Yellow Header */
    .cosmo-header {{
        background: linear-gradient(135deg, #101f42 0%, #0a1128 100%);
        border: 2px solid {blue_primary};
        border-bottom: 4px solid {yellow_primary};
        border-radius: 18px;
        padding: 16px 22px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px {card_glow_yellow};
    }}

    .cosmo-header-left {{
        display: flex;
        align-items: center;
        gap: 16px;
    }}

    .cosmo-logo-img {{
        width: 50px;
        height: 50px;
        border-radius: 14px;
        object-fit: cover;
        border: 2.5px solid {yellow_primary};
        box-shadow: 0 0 16px {card_glow_yellow};
    }}

    .cosmo-title {{
        font-size: 22px;
        font-weight: 900;
        color: #ffffff !important;
        margin: 0;
        letter-spacing: -0.3px;
    }}
    
    .cosmo-title-highlight {{
        color: {yellow_primary} !important;
        text-shadow: 0 0 12px rgba(250, 204, 21, 0.5);
    }}

    .cosmo-sub {{
        font-size: 13px;
        color: {blue_light} !important;
        font-weight: 600;
        margin-top: 2px;
    }}

    .user-badge {{
        background: rgba(250, 204, 21, 0.12);
        border: 1.5px solid {yellow_primary};
        color: {yellow_primary} !important;
        padding: 8px 16px;
        border-radius: 30px;
        font-size: 13px;
        font-weight: 800;
        box-shadow: 0 4px 14px rgba(250, 204, 21, 0.25);
        white-space: nowrap;
    }}

    /* Card & Container Blocks */
    div[data-testid="stForm"], div.stForm, div[data-testid="stExpander"] {{
        background-color: {card_bg} !important;
        border: 1.5px solid {card_border} !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.5) !important;
    }}

    /* Inputs & Form Controls */
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
        border-radius: 14px !important;
        border: 1.5px solid {input_border} !important;
        min-height: 50px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }}
    
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    div[data-baseweb="select"] > div:focus-within {{
        border-color: {yellow_primary} !important;
        box-shadow: 0 0 14px {card_glow_yellow} !important;
    }}
    
    /* Popover & Select Dropdown Menus */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    div[data-baseweb="tooltip"],
    ul[role="listbox"] {{
        background-color: {card_bg} !important;
        border: 2px solid {yellow_primary} !important;
        color: {text_color} !important;
        border-radius: 16px !important;
        box-shadow: 0 12px 36px rgba(0,0,0,0.8) !important;
    }}
    
    li[role="option"] {{
        color: {text_color} !important;
        background-color: {card_bg} !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
        padding-left: 14px !important;
        font-weight: 600 !important;
    }}
    
    li[role="option"]:hover, li[aria-selected="true"] {{
        background-color: {yellow_primary} !important;
        color: #050914 !important;
        font-weight: 800 !important;
    }}

    /* Buttons Styling - Touch Friendly Yellow Primary Buttons */
    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {{
        border-radius: 14px !important;
        font-weight: 800 !important;
        min-height: 52px !important;
        font-size: 15px !important;
        border: 1.5px solid {yellow_hover} !important;
        background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important;
        color: #070d1e !important;
        box-shadow: 0 6px 20px {card_glow_yellow} !important;
        transition: all 0.2s ease-in-out !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        letter-spacing: 0.3px !important;
        cursor: pointer !important;
    }}

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton > a:hover {{
        background: linear-gradient(135deg, #fde047 0%, #facc15 100%) !important;
        border-color: #ffffff !important;
        color: #000000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(250, 204, 21, 0.5) !important;
    }}

    .stButton > button:active,
    .stDownloadButton > button:active {{
        transform: scale(0.98) !important;
    }}

    /* Secondary Action Button Styling */
    button[kind="secondary"] {{
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: 1.5px solid {yellow_primary} !important;
        box-shadow: 0 4px 16px {card_glow_blue} !important;
    }}

    button[kind="secondary"]:hover {{
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
        color: {yellow_primary} !important;
    }}

    /* Horizontal Mobile Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: #0c1630 !important;
        padding: 6px !important;
        border-radius: 16px !important;
        border: 1.5px solid {blue_primary} !important;
        overflow-x: auto !important;
        scroll-behavior: smooth !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.4) !important;
    }}

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {{
        display: none !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 46px !important;
        white-space: nowrap !important;
        border-radius: 12px !important;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 0 16px !important;
        background-color: transparent !important;
        flex-shrink: 0 !important;
        border: 1px solid transparent !important;
        transition: all 0.2s ease !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important;
        color: #070d1e !important;
        border: 1.5px solid #fde047 !important;
        box-shadow: 0 4px 14px rgba(250, 204, 21, 0.4) !important;
        font-weight: 900 !important;
    }}

    /* Metrics Cards - Navy Blue with Glowing Yellow Numbers */
    div[data-testid="stMetric"] {{
        background: linear-gradient(135deg, #0f1a34 0%, #0a1128 100%) !important;
        border: 1.5px solid {card_border} !important;
        border-top: 3.5px solid {yellow_primary} !important;
        padding: 16px 18px !important;
        border-radius: 16px !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5), 0 0 12px {card_glow_yellow} !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: #cbd5e1 !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: {yellow_primary} !important;
        font-weight: 900 !important;
        font-size: 24px !important;
        text-shadow: 0 0 10px rgba(250, 204, 21, 0.4) !important;
    }}

    /* Radio Buttons & Checkboxes */
    div[role="radiogroup"] label, div[data-testid="stCheckbox"] label {{
        color: {text_color} !important;
        font-weight: 700 !important;
        padding: 6px 10px !important;
    }}

    /* Dividers */
    hr {{
        border-color: {card_border} !important;
        border-top-width: 2px !important;
        margin: 1.2rem 0 !important;
    }}

    /* Badges */
    .badge-yellow {{
        background: rgba(250, 204, 21, 0.18);
        border: 1.5px solid #facc15;
        color: #facc15 !important;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 12px;
    }}

    .badge-blue {{
        background: rgba(37, 99, 235, 0.25);
        border: 1.5px solid #3b82f6;
        color: #60a5fa !important;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 12px;
    }}

    /* ==================== RESPONSIVE MOBILE MEDIA QUERIES ==================== */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.4rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
        }}

        .cosmo-header {{
            padding: 10px 14px !important;
            margin-bottom: 14px !important;
            border-radius: 14px !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
        }}

        .cosmo-logo-img {{
            width: 38px !important;
            height: 38px !important;
        }}

        .cosmo-title {{
            font-size: 16px !important;
            margin: 0 !important;
        }}

        .cosmo-sub {{
            font-size: 11px !important;
        }}

        .user-badge {{
            padding: 4px 10px !important;
            font-size: 11px !important;
            border-radius: 20px !important;
        }}

        /* Force columns to stack vertically on mobile screens */
        div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 6px !important;
        }}

        div[data-testid="stMetric"] {{
            padding: 10px 14px !important;
            border-radius: 12px !important;
            margin-bottom: 8px !important;
        }}

        div[data-testid="stMetricValue"] {{
            font-size: 20px !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto !important;
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            padding: 4px !important;
            -webkit-overflow-scrolling: touch !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 40px !important;
            font-size: 13px !important;
            padding: 0 12px !important;
            flex-shrink: 0 !important;
            white-space: nowrap !important;
        }}

        .stButton > button, 
        .stDownloadButton > button, 
        .stLinkButton > a {{
            min-height: 48px !important;
            font-size: 14px !important;
            border-radius: 12px !important;
        }}

        div[data-testid="stForm"], div.stForm {{
            padding: 14px !important;
            border-radius: 14px !important;
        }}
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
        <meta name="theme-color" content="#070d1e">
        <link rel="manifest" href="/manifest.json">
        <link rel="apple-touch-icon" href="/cosmo_logo.jpg">
    """, unsafe_allow_html=True)


def get_logo_base64():
    if os.path.exists("cosmo_logo.jpg"):
        try:
            with open("cosmo_logo.jpg", "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return ""


def render_top_header(title="Cosmo CRM", subtitle="", user_name="", user_role="", user_email=""):
    b64_logo = get_logo_base64()
    logo_html = f'<img src="data:image/jpeg;base64,{b64_logo}" class="cosmo-logo-img" alt="Logo">' if b64_logo else ""
    
    st.markdown(f"""
        <div class="cosmo-header">
            <div class="cosmo-header-left">
                {logo_html}
                <div>
                    <h2 class="cosmo-title">🧼 <span class="cosmo-title-highlight">{title}</span></h2>
                    <div class="cosmo-sub">{subtitle}</div>
                </div>
            </div>
            <div class="user-badge">
                👤 <b>{user_name}</b> ({user_role})
            </div>
        </div>
    """, unsafe_allow_html=True)
