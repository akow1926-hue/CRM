import os
import base64
import streamlit as st

def get_dark_theme_css():
    # Premium Indigo-Slate & Warm Amber Gold Palette Tokens (Compact Sizing)
    bg_color = "#0b1120"          # Soft Deep Slate Navy
    sidebar_bg = "#080e1b"        # Deep Midnight Slate Sidebar
    card_bg = "#121b2d"           # Elegant Slate Surface
    card_border = "#1e2c46"       # Subtle Slate Border
    card_glow_gold = "rgba(245, 158, 11, 0.18)"  # Soft Amber Gold Glow
    card_glow_blue = "rgba(59, 130, 246, 0.15)"  # Soft Indigo Glow

    text_color = "#f8fafc"        # Crisp Readable White Text
    subtext_color = "#94a3b8"     # Soft Slate Subtext

    input_bg = "#172339"          # Dark Slate Input Fill
    input_border = "#2b3d5e"      # Soft Slate Blue Border

    amber_gold = "#f59e0b"        # Warm Amber Gold
    amber_light = "#fbbf24"       # Light Champagne Gold Accent
    amber_dark = "#d97706"        # Rich Amber Gold

    blue_primary = "#3b82f6"      # Soft Royal Blue Accent
    blue_light = "#60a5fa"        # Sky Blue Accent

    css_template = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Root Styling - Compact & Proportional Sizing */
    html, body, [class*="css"], .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stToolbar"], 
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"],
    .main, .block-container {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: __BG_COLOR__ !important;
        color: __TEXT_COLOR__ !important;
        font-size: 13.5px !important;
    }

    /* Top Navigation Header Bar */
    [data-testid="stHeader"] {
        background: rgba(11, 17, 32, 0.92) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border-bottom: 1px solid __CARD_BORDER__ !important;
        height: 48px !important;
    }

    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 1240px !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: __SIDEBAR_BG__ !important;
        border-right: 1px solid __CARD_BORDER__ !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #e2e8f0 !important;
        font-size: 13px !important;
    }

    /* Compact Header Banner */
    .cosmo-header {
        background: linear-gradient(135deg, #152238 0%, #0d1526 100%);
        border: 1px solid __CARD_BORDER__;
        border-bottom: 2.5px solid __AMBER_GOLD__;
        border-radius: 12px;
        padding: 10px 16px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
    }

    .cosmo-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .cosmo-logo-img {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        object-fit: cover;
        border: 1.5px solid __AMBER_GOLD__;
    }

    .cosmo-title {
        font-size: 17px;
        font-weight: 800;
        color: #ffffff !important;
        margin: 0;
        letter-spacing: -0.2px;
    }
    
    .cosmo-title-highlight {
        color: __AMBER_LIGHT__ !important;
    }

    .cosmo-sub {
        font-size: 11px;
        color: __BLUE_LIGHT__ !important;
        font-weight: 500;
        margin-top: 1px;
    }

    .user-badge {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid __AMBER_GOLD__;
        color: __AMBER_LIGHT__ !important;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 700;
        white-space: nowrap;
    }

    /* Card & Container Blocks */
    div[data-testid="stForm"], div.stForm, div[data-testid="stExpander"] {
        background-color: __CARD_BG__ !important;
        border: 1px solid __CARD_BORDER__ !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
    }

    /* Compact Inputs & Form Controls */
    .stTextInput input,
    .stSelectbox div[role="button"],
    .stMultiSelect div[role="button"],
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] {
        background-color: __INPUT_BG__ !important;
        color: __TEXT_COLOR__ !important;
        border-radius: 10px !important;
        border: 1px solid __INPUT_BORDER__ !important;
        min-height: 38px !important;
        height: 38px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
    }
    
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    div[data-baseweb="select"] > div:focus-within {
        border-color: __AMBER_GOLD__ !important;
        box-shadow: 0 0 8px __CARD_GLOW_GOLD__ !important;
    }
    
    /* Popover & Select Dropdown Menus */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    div[data-baseweb="tooltip"],
    ul[role="listbox"] {
        background-color: __CARD_BG__ !important;
        border: 1px solid __AMBER_GOLD__ !important;
        color: __TEXT_COLOR__ !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
    }
    
    li[role="option"] {
        color: __TEXT_COLOR__ !important;
        background-color: __CARD_BG__ !important;
        min-height: 36px !important;
        height: 36px !important;
        font-size: 13px !important;
        display: flex !important;
        align-items: center !important;
        padding-left: 10px !important;
        font-weight: 600 !important;
    }
    
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: __AMBER_GOLD__ !important;
        color: #080e1b !important;
        font-weight: 700 !important;
    }

    /* Compact Primary Action Buttons */
    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {
        border-radius: 10px !important;
        font-weight: 700 !important;
        min-height: 38px !important;
        height: 38px !important;
        font-size: 13px !important;
        border: 1px solid #fde047 !important;
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #080e1b !important;
        box-shadow: 0 2px 10px __CARD_GLOW_GOLD__ !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        letter-spacing: 0.2px !important;
        cursor: pointer !important;
        padding: 0 12px !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton > a:hover {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        border-color: #ffffff !important;
        color: #000000 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35) !important;
    }

    .stButton > button:active,
    .stDownloadButton > button:active {
        transform: scale(0.98) !important;
    }

    /* Compact Secondary Buttons */
    button[kind="secondary"] {
        background: linear-gradient(135deg, #1b263b 0%, #0f172a 100%) !important;
        color: #e2e8f0 !important;
        border: 1px solid __INPUT_BORDER__ !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }

    button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #25334d 0%, #172339 100%) !important;
        color: __AMBER_LIGHT__ !important;
        border-color: __AMBER_GOLD__ !important;
    }

    /* Compact Sidebar Buttons */
    section[data-testid="stSidebar"] .stButton > button {
        min-height: 36px !important;
        height: 36px !important;
        font-size: 12.5px !important;
        border-radius: 8px !important;
        margin-bottom: 2px !important;
    }

    /* Horizontal Mobile Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #0d1526 !important;
        padding: 4px !important;
        border-radius: 12px !important;
        border: 1px solid __CARD_BORDER__ !important;
        overflow-x: auto !important;
        scroll-behavior: smooth !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
    }

    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none !important;
    }

    /* Action Row for Courier Order Cards - 4 Buttons Side-by-Side in 1 Row (as in Photo 2) */
    .cour-action-row {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        margin-top: 8px !important;
        width: 100% !important;
    }

    .cour-action-row div[data-testid="column"] {
        width: 23% !important;
        flex: 1 1 23% !important;
        min-width: 23% !important;
        margin-bottom: 0 !important;
    }

    /* Button 1: Transfer (Grey) */
    .cour-action-row div[data-testid="column"]:nth-child(1) button {
        background: #334155 !important;
        color: #ffffff !important;
        border: 1px solid #475569 !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 !important;
    }
    .cour-action-row div[data-testid="column"]:nth-child(1) button:hover {
        background: #475569 !important;
        color: #ffffff !important;
    }

    /* Button 2: Accept/Deliver (Vibrant Green) */
    .cour-action-row div[data-testid="column"]:nth-child(2) button {
        background: #22c55e !important;
        color: #000000 !important;
        border: 1px solid #4ade80 !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 !important;
    }
    .cour-action-row div[data-testid="column"]:nth-child(2) button:hover {
        background: #16a34a !important;
        color: #ffffff !important;
    }

    /* Button 3: Edit (Warm Yellow) */
    .cour-action-row div[data-testid="column"]:nth-child(3) button {
        background: #eab308 !important;
        color: #000000 !important;
        border: 1px solid #fde047 !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 !important;
    }
    .cour-action-row div[data-testid="column"]:nth-child(3) button:hover {
        background: #ca8a04 !important;
        color: #ffffff !important;
    }

    /* Button 4: Cancel (Vibrant Red) */
    .cour-action-row div[data-testid="column"]:nth-child(4) button {
        background: #ef4444 !important;
        color: #ffffff !important;
        border: 1px solid #f87171 !important;
        border-radius: 12px !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 !important;
    }
    .cour-action-row div[data-testid="column"]:nth-child(4) button:hover {
        background: #dc2626 !important;
        color: #ffffff !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 36px !important;
        white-space: nowrap !important;
        border-radius: 10px !important;
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        font-size: 12.5px !important;
        padding: 0 12px !important;
        background-color: transparent !important;
        flex-shrink: 0 !important;
        border: 1px solid transparent !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #080e1b !important;
        border: 1px solid #fde047 !important;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3) !important;
        font-weight: 800 !important;
    }

    /* Compact Metrics Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #121b2d 0%, #0b1120 100%) !important;
        border: 1px solid __CARD_BORDER__ !important;
        border-top: 2.5px solid __AMBER_GOLD__ !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.3px !important;
    }
    div[data-testid="stMetricValue"] {
        color: __AMBER_LIGHT__ !important;
        font-weight: 800 !important;
        font-size: 18px !important;
    }

    /* Radio Buttons & Checkboxes */
    div[role="radiogroup"] label, div[data-testid="stCheckbox"] label {
        color: __TEXT_COLOR__ !important;
        font-weight: 600 !important;
        font-size: 12.5px !important;
        padding: 4px 8px !important;
    }

    /* Headings */
    h1 { font-size: 20px !important; font-weight: 800 !important; }
    h2 { font-size: 18px !important; font-weight: 800 !important; }
    h3 { font-size: 16px !important; font-weight: 700 !important; }
    h4 { font-size: 14.5px !important; font-weight: 700 !important; }
    h5 { font-size: 13.5px !important; font-weight: 700 !important; }

    /* Dividers */
    hr {
        border-color: __CARD_BORDER__ !important;
        border-top-width: 1px !important;
        margin: 0.8rem 0 !important;
    }

    /* Badges */
    .badge-yellow {
        background: rgba(245, 158, 11, 0.16);
        border: 1px solid #f59e0b;
        color: #fbbf24 !important;
        padding: 2px 8px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 11px;
    }

    .badge-blue {
        background: rgba(59, 130, 246, 0.2);
        border: 1px solid #3b82f6;
        color: #60a5fa !important;
        padding: 2px 8px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 11px;
    }

    /* Responsive Mobile Queries */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
            padding-top: 0.3rem !important;
            padding-bottom: 1.5rem !important;
            max-width: 100% !important;
        }

        .cosmo-header {
            padding: 8px 12px !important;
            margin-bottom: 10px !important;
            border-radius: 10px !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
        }

        .cosmo-logo-img {
            width: 32px !important;
            height: 32px !important;
        }

        .cosmo-title {
            font-size: 14.5px !important;
            margin: 0 !important;
        }

        .cosmo-sub {
            font-size: 10px !important;
        }

        .user-badge {
            padding: 3px 8px !important;
            font-size: 10px !important;
            border-radius: 14px !important;
        }

        div[data-testid="stMetric"] {
            padding: 8px 10px !important;
            border-radius: 10px !important;
            margin-bottom: 6px !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 16px !important;
        }

        .stButton > button, 
        .stDownloadButton > button, 
        .stLinkButton > a {
            min-height: 36px !important;
            height: 36px !important;
            font-size: 12.5px !important;
            border-radius: 8px !important;
        }

        div[data-testid="stForm"], div.stForm {
            padding: 10px 12px !important;
            border-radius: 10px !important;
        }
    }
    </style>
    """

    return (css_template
        .replace("__BG_COLOR__", bg_color)
        .replace("__SIDEBAR_BG__", sidebar_bg)
        .replace("__CARD_BG__", card_bg)
        .replace("__CARD_BORDER__", card_border)
        .replace("__CARD_GLOW_GOLD__", card_glow_gold)
        .replace("__CARD_GLOW_BLUE__", card_glow_blue)
        .replace("__TEXT_COLOR__", text_color)
        .replace("__SUBTEXT_COLOR__", subtext_color)
        .replace("__INPUT_BG__", input_bg)
        .replace("__INPUT_BORDER__", input_border)
        .replace("__AMBER_GOLD__", amber_gold)
        .replace("__AMBER_LIGHT__", amber_light)
        .replace("__AMBER_DARK__", amber_dark)
        .replace("__BLUE_PRIMARY__", blue_primary)
        .replace("__BLUE_LIGHT__", blue_light)
    )

def inject_theme():
    st.session_state["dark_mode"] = True
    st.markdown(get_dark_theme_css(), unsafe_allow_html=True)
    st.markdown("""
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#0b1120">
        <link rel="manifest" href="/manifest.json">
        <link rel="apple-touch-icon" href="/cosmo_logo.jpg">
        <script>
        if ('serviceWorker' in navigator) {
          window.addEventListener('load', function() {
            navigator.serviceWorker.register('/sw.js').then(function(reg) {
              console.log('PWA SW Registered!', reg.scope);
            }).catch(function(err) {
              console.log('PWA SW Fail:', err);
            });
          });
        }
        </script>
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
