"""CivicPulse dual-theme design system supporting Light and Dark modes.

Matches the reference visual directions:
- Light Theme: Bright white surfaces, clean spacing, blue and teal accents, warm streetlight hero.
- Dark Theme: Deep navy surfaces, glowing cyan accents, subtle glow, nighttime streetlight scene.
"""
from __future__ import annotations

import streamlit as st


def inject_theme(theme_mode: str = "light") -> None:
    """Apply the chosen theme (light or dark) to Streamlit components."""
    is_dark = str(theme_mode).strip().lower() == "dark"

    if is_dark:
        # DARK THEME (Reference Screenshot 2)
        css = """
        <style>
        :root {
          --theme-mode: dark;
          --canvas: #030b14;
          --button-secondary-bg: #142b45;
          --button-secondary-ink: #f8fafc;
          --surface: #071526;
          --surface-raised: #0b1e36;
          --surface-card: rgba(11, 30, 54, 0.78);
          --surface-border: rgba(56, 189, 248, 0.22);
          --line: rgba(56, 189, 248, 0.16);
          --ink: #f1f5f9;
          --ink-bright: #ffffff;
          --muted: #94a3b8;
          --muted-dark: #64748b;

          /* Accents: Glowing Cyan & Electric Amber */
          --primary: #00f2fe;
          --primary-bright: #38bdf8;
          --primary-dim: rgba(6, 182, 212, 0.16);
          --primary-glow: 0 0 20px rgba(6, 182, 212, 0.35);

          --accent: #38bdf8;
          --amber: #f59e0b;
          --amber-dim: rgba(245, 158, 11, 0.16);

          --success: #10b981;
          --success-bg: rgba(16, 185, 129, 0.14);
          --success-border: rgba(16, 185, 129, 0.35);
          --success-text: #6ee7b7;

          --warning: #f59e0b;
          --critical: #ef4444;
          --info: #38bdf8;

          --card-shadow: 0 8px 32px rgba(0, 0, 0, 0.55), 0 0 15px rgba(6, 182, 212, 0.12);
          --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.65);
        }

        html, body, [class*="css"] {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          color: var(--ink);
        }

        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          color: var(--ink);
          background: radial-gradient(ellipse at 20% -10%, #081d36 0%, transparent 45%),
                      radial-gradient(ellipse at 80% 20%, #06192e 0%, transparent 40%),
                      var(--canvas);
        }

        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
        [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
        [data-testid="stMainBlockContainer"] { max-width: 1540px; padding: 1.15rem 2.2rem 5rem; }
        .block-container { padding-top: 0.5rem; }

        h1, h2, h3, h4 {
          color: var(--ink-bright) !important;
          letter-spacing: -0.025em;
          font-weight: 750 !important;
        }
        h1 { font-size: 1.95rem !important; }
        h2 { font-size: 1.38rem !important; }
        h3 { font-size: 1.08rem !important; }
        p, [data-testid="stMarkdownContainer"] { color: #cbd5e1; }
        [data-testid="stCaptionContainer"], .case-meta, .brand-subtitle { color: var(--muted) !important; }

        /* App Branding */
        .app-brand { display: flex; align-items: center; gap: 14px; min-height: 68px; }
        .brand-seal {
          width: 48px; height: 48px; border-radius: 14px;
          display: flex; align-items: center; justify-content: center;
          background: linear-gradient(135deg, #0b2545, #071526);
          color: var(--primary);
          border: 1px solid rgba(0, 242, 254, 0.4);
          font-size: 24px;
          box-shadow: 0 0 20px rgba(0, 242, 254, 0.25);
        }
        .brand-name { font-size: 21px; line-height: 1.2; font-weight: 800; color: var(--ink-bright); letter-spacing: -0.02em; }
        .brand-subtitle { font-size: 11px; margin-top: 4px; letter-spacing: 0.12em; font-weight: 700; color: var(--primary-bright); }
        .brand-utility { text-align: right; color: var(--muted); font-size: 12px; line-height: 1.65; }
        .brand-utility strong { color: var(--ink-bright); }
        .live-dot { color: #10b981; font-size: 14px; vertical-align: -1px; text-shadow: 0 0 10px #10b981; }

        /* Utility Pills */
        .utility-pill, .role-pill, .theme-pill {
          display: inline-flex; align-items: center; border: 1px solid var(--line);
          border-radius: 999px; padding: 0.2rem 0.65rem;
          background: rgba(11, 30, 54, 0.6); color: #cbd5e1;
          font-size: 0.69rem; font-weight: 750; letter-spacing: 0.04em;
        }
        .role-pill { margin-left: 0.3rem; background: var(--primary-dim); color: var(--primary); border-color: rgba(6, 182, 212, 0.3); }
        .avatar-chip {
          display: inline-flex; vertical-align: middle; align-items: center; justify-content: center;
          width: 25px; height: 25px; border-radius: 50%;
          background: linear-gradient(145deg, #0c2d54, #1e3a8a);
          color: white; font-weight: 750; font-size: 11px;
        }
        .top-rule { height: 1px; background: var(--line); margin: 0.55rem 0 0.5rem; }

        /* Operations Banner */
        .portal-banner, .hero-panel {
          position: relative; overflow: hidden; border-radius: 16px;
          padding: 1.6rem 2rem;
          background: linear-gradient(135deg, rgba(11, 30, 54, 0.85), rgba(7, 21, 38, 0.95));
          border: 1px solid var(--surface-border);
          box-shadow: var(--card-shadow); margin: 0.3rem 0 1.2rem;
        }
        .hero-kicker, .eyebrow, .section-kicker {
          color: var(--primary); font-size: 0.72rem;
          font-weight: 760; letter-spacing: 0.12em; text-transform: uppercase;
        }
        .section-heading { display: flex; align-items: center; gap: 10px; margin: 0.65rem 0 0.95rem; }
        .section-heading h2 { margin: 0; }

        /* Containers & Cards */
        .glass-card, .case-card, .empty-state, [data-testid="stForm"], [data-testid="stMetric"], [data-testid="stPlotlyChart"] {
          background: var(--surface-card);
          border: 1px solid var(--surface-border);
          border-radius: 14px;
          box-shadow: var(--card-shadow);
          backdrop-filter: blur(16px);
        }
        .case-card { padding: 1.1rem 1.25rem; margin: 0.55rem 0; position: relative; }
        .case-id { color: var(--primary); font-weight: 760; font-size: 0.88rem; font-family: ui-monospace, monospace; }
        .case-title { color: var(--ink-bright); font-weight: 700; font-size: 1.02rem; margin: 0.35rem 0; }
        .case-meta { font-size: 0.82rem; line-height: 1.6; color: var(--muted) !important; }

        /* Form Controls */
        [data-testid="stTextInput"] input:not(:disabled), [data-testid="stTextArea"] textarea:not(:disabled),
        [data-testid="stDateInput"] input:not(:disabled), [data-testid="stTimeInput"] input:not(:disabled),
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
          color: var(--ink-bright) !important; -webkit-text-fill-color: var(--ink-bright) !important;
          background-color: #061528 !important; border-color: #173559 !important; border-radius: 10px !important;
        }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stSelectbox"] input::placeholder { color: #64748b !important; -webkit-text-fill-color: #64748b !important; opacity: 1 !important; }
        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within, [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
        [data-testid="stDateInput"] [data-baseweb="input"]:focus-within, [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within {
          border-color: var(--primary) !important; box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.3) !important;
        }

        /* Metrics */
        [data-testid="stMetric"] {
          padding: 14px 18px; min-height: 88px; transition: transform 0.18s, border-color 0.18s;
          background: rgba(11, 30, 54, 0.82); border: 1px solid var(--surface-border);
        }
        [data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: var(--primary); }
        [data-testid="stMetricLabel"] p { color: var(--muted) !important; font-weight: 650 !important; font-size: 0.79rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
        [data-testid="stMetricLabel"]:before { content: "◈ "; color: var(--primary); font-size: 0.75rem; }
        [data-testid="stMetricValue"] { color: var(--ink-bright) !important; font-weight: 800; font-size: 1.6rem !important; font-family: ui-monospace, monospace; }

        /* Buttons & CTAs */
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button, [data-testid="stLinkButton"] a {
          border-radius: 10px; min-height: 42px; font-weight: 700;
          transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
        }
        [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
          color: #ffffff;
          background: linear-gradient(110deg, #0284c7, #06b6d4);
          border-color: #06b6d4;
          box-shadow: 0 4px 18px rgba(6, 182, 212, 0.35);
        }
        [data-testid="stButton"] button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 24px rgba(6, 182, 212, 0.5);
        }
        [data-testid="stButton"] button:not([kind="primary"]):hover {
          border-color: var(--primary); color: #ffffff;
        }

        /* Radio Navigation */
        [data-testid="stRadio"] [role="radiogroup"] { gap: 6px; flex-wrap: wrap; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] {
          border: 1px solid transparent; border-radius: 9px; background: transparent;
          padding: 8px 14px; transition: all 0.16s; min-height: 38px;
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:hover {
          background: rgba(255, 255, 255, 0.06); border-color: var(--line);
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child { display: none; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div { display: flex; align-items: center; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] p {
          margin: 0; color: #cbd5e1; font-size: 13px; font-weight: 650; white-space: nowrap;
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) {
          background: linear-gradient(110deg, #0b2545, #0d3663);
          border-color: var(--primary);
          box-shadow: 0 3px 12px rgba(0, 242, 254, 0.2);
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) p {
          color: #ffffff; font-weight: 750;
        }

        /* Status & Priority Badges */
        .priority-critical, .priority-high, .priority-medium, .priority-low, .status-badge {
          display: inline-flex; align-items: center; border-radius: 999px;
          padding: 0.28rem 0.68rem; font-size: 0.76rem; font-weight: 750;
          line-height: 1.2; white-space: nowrap; letter-spacing: 0.03em;
        }
        .priority-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
        .priority-high { background: rgba(249, 115, 22, 0.2); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.4); }
        .priority-medium { background: rgba(245, 158, 11, 0.2); color: #fde047; border: 1px solid rgba(245, 158, 11, 0.45); }
        .priority-low { background: rgba(16, 185, 129, 0.18); color: #86efac; border: 1px solid rgba(16, 185, 129, 0.35); }

        .status-open, .status-new { background: rgba(56, 189, 248, 0.18); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.4); }
        .status-assigned { background: rgba(168, 85, 247, 0.2); color: #e9d5ff; border: 1px solid rgba(168, 85, 247, 0.4); }
        .status-progress { background: rgba(245, 158, 11, 0.2); color: #fde047; border: 1px solid rgba(245, 158, 11, 0.4); }
        .status-resolved, .status-closed { background: rgba(16, 185, 129, 0.2); color: #86efac; border: 1px solid rgba(16, 185, 129, 0.4); }

        /* Floating Actions */
        .civic-fab {
          position: fixed; z-index: 999; right: max(20px, env(safe-area-inset-right));
          bottom: max(20px, env(safe-area-inset-bottom));
          display: flex; align-items: flex-end; flex-direction: column; gap: 9px;
        }
        .fab-secondary {
          display: flex; flex-direction: column; align-items: flex-end; gap: 8px;
          max-height: 0; opacity: 0; overflow: hidden; pointer-events: none; transform: translateY(8px);
          transition: max-height 0.2s ease, opacity 0.16s ease, transform 0.2s ease;
        }
        .civic-fab:hover .fab-secondary, .civic-fab:focus-within .fab-secondary {
          max-height: 200px; opacity: 1; overflow: visible; pointer-events: auto; transform: translateY(0);
        }
        .fab-action {
          position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 9px;
          min-height: 46px; padding: 0.7rem 1.05rem; border: 1px solid var(--surface-border);
          border-radius: 12px; background: rgba(7, 21, 38, 0.96); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
          backdrop-filter: blur(14px); color: var(--ink-bright) !important; font-size: 0.88rem; font-weight: 750;
          text-decoration: none; white-space: nowrap;
        }
        .fab-action:hover { border-color: var(--primary); transform: translateY(-2px); }
        .fab-primary {
          min-height: 50px; padding: 0.75rem 1.15rem; border-color: #06b6d4;
          background: linear-gradient(115deg, #0284c7, #06b6d4); color: #fff !important;
          box-shadow: 0 8px 24px rgba(6, 182, 212, 0.4);
        }
        .fab-icon { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(255, 255, 255, 0.15); font-size: 1rem; }
        .fab-badge {
          position: absolute; top: -6px; right: -6px; display: grid; place-items: center;
          min-width: 22px; height: 22px; padding: 0 5px; border: 2px solid var(--canvas);
          border-radius: 999px; background: #ef4444; color: white; font-size: 0.65rem; font-weight: 800;
        }

        /* Success Banner (matches screenshot) */
        .conf-banner {
          display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
          background: linear-gradient(135deg, rgba(6, 78, 59, 0.35), rgba(7, 21, 38, 0.85));
          border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 14px; padding: 1.15rem 1.4rem;
          margin: 0.5rem 0 1rem; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }
        .conf-banner-left { display: flex; align-items: center; gap: 14px; }
        .conf-icon-circle {
          width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
          background: rgba(16, 185, 129, 0.25); color: #6ee7b7; font-size: 1.25rem; font-weight: 800;
          border: 1px solid rgba(16, 185, 129, 0.5);
        }
        .conf-title { color: #f0fdf4; font-size: 1.12rem; font-weight: 750; margin-bottom: 2px; }
        .conf-sub { color: #a7f3d0; font-size: 0.86rem; }

        /* Detail Stat Tile */
        .conf-tile {
          background: rgba(11, 30, 54, 0.82); border: 1px solid var(--surface-border);
          border-radius: 12px; padding: 0.95rem 1.1rem; height: 100%; min-height: 98px;
        }
        .conf-tile-label { color: var(--muted); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
        .conf-tile-val { color: #ffffff; font-size: 1.22rem; font-weight: 800; font-family: ui-monospace, monospace; }

        /* Civic Hero Container */
        .civic-hero-wrap {
          position: relative; overflow: hidden; border-radius: 18px; margin: 0.3rem 0 1.2rem;
          border: 1px solid var(--surface-border); box-shadow: var(--card-shadow);
          background: linear-gradient(135deg, #071526, #030b14);
        }
        .civic-hero-img { width: 100%; height: 380px; object-fit: cover; display: block; opacity: 0.55; }
        .civic-hero-scrim {
          position: absolute; inset: 0;
          background: linear-gradient(90deg, rgba(3, 11, 20, 0.96) 0%, rgba(7, 21, 38, 0.82) 48%, rgba(7, 21, 38, 0.4) 100%);
        }
        .civic-hero-content {
          position: absolute; inset: 0; z-index: 1; display: flex; flex-direction: column;
          justify-content: center; padding: clamp(1.4rem, 4vw, 3rem);
        }
        .civic-hero-script {
          position: absolute; right: 28px; top: 24px; z-index: 1;
          font-family: "Brush Script MT", cursive, sans-serif; font-size: 1.55rem;
          color: #38bdf8; text-shadow: 0 0 16px rgba(56, 189, 248, 0.5);
          transform: rotate(-4deg);
        }
        </style>
        """
    else:
        # LIGHT THEME (Reference Screenshot 1)
        css = """
        <style>
        :root {
          --theme-mode: light;
          --canvas: #f8fafc;
          --button-secondary-bg: #e2e8f0;
          --button-secondary-ink: #0f172a;
          --surface: #ffffff;
          --surface-raised: #ffffff;
          --surface-card: #ffffff;
          --surface-border: #e2e8f0;
          --line: #e2e8f0;
          --ink: #0f172a;
          --ink-bright: #0f172a;
          --muted: #64748b;
          --muted-dark: #94a3b8;

          /* Accents: Crisp Cyan & Teal */
          --primary: #0d9488;
          --primary-bright: #0284c7;
          --primary-dim: rgba(13, 148, 136, 0.1);
          --primary-glow: 0 4px 14px rgba(13, 148, 136, 0.2);

          --accent: #0284c7;
          --amber: #d97706;
          --amber-dim: rgba(245, 158, 11, 0.12);

          --success: #10b981;
          --success-bg: #ecfdf5;
          --success-border: #a7f3d0;
          --success-text: #065f46;

          --warning: #f59e0b;
          --critical: #ef4444;
          --info: #0284c7;

          --card-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
          --glass-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        }

        html, body, [class*="css"] {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          color: var(--ink);
        }

        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          color: var(--ink);
          background: #f8fafc;
        }

        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
        [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
        [data-testid="stMainBlockContainer"] { max-width: 1540px; padding: 1.15rem 2.2rem 5rem; }
        .block-container { padding-top: 0.5rem; }

        h1, h2, h3, h4 {
          color: var(--ink-bright) !important;
          letter-spacing: -0.025em;
          font-weight: 750 !important;
        }
        h1 { font-size: 1.95rem !important; }
        h2 { font-size: 1.38rem !important; }
        h3 { font-size: 1.08rem !important; }
        p, [data-testid="stMarkdownContainer"] { color: #334155; }
        [data-testid="stCaptionContainer"], .case-meta, .brand-subtitle { color: var(--muted) !important; }

        /* App Branding */
        .app-brand { display: flex; align-items: center; gap: 14px; min-height: 68px; }
        .brand-seal {
          width: 48px; height: 48px; border-radius: 14px;
          display: flex; align-items: center; justify-content: center;
          background: linear-gradient(135deg, #0d9488, #0284c7);
          color: #ffffff;
          font-size: 24px;
          box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
        }
        .brand-name { font-size: 21px; line-height: 1.2; font-weight: 800; color: var(--ink-bright); letter-spacing: -0.02em; }
        .brand-subtitle { font-size: 11px; margin-top: 4px; letter-spacing: 0.12em; font-weight: 700; color: var(--primary); }
        .brand-utility { text-align: right; color: var(--muted); font-size: 12px; line-height: 1.65; }
        .brand-utility strong { color: var(--ink-bright); }
        .live-dot { color: #10b981; font-size: 14px; vertical-align: -1px; text-shadow: 0 0 6px #10b981; }

        /* Utility Pills */
        .utility-pill, .role-pill, .theme-pill {
          display: inline-flex; align-items: center; border: 1px solid #cbd5e1;
          border-radius: 999px; padding: 0.2rem 0.65rem;
          background: #ffffff; color: #475569;
          font-size: 0.69rem; font-weight: 750; letter-spacing: 0.04em;
          box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .role-pill { margin-left: 0.3rem; background: #e0f2fe; color: #0369a1; border-color: #bae6fd; }
        .avatar-chip {
          display: inline-flex; vertical-align: middle; align-items: center; justify-content: center;
          width: 25px; height: 25px; border-radius: 50%;
          background: linear-gradient(145deg, #0f766e, #0284c7);
          color: white; font-weight: 750; font-size: 11px;
        }
        .top-rule { height: 1px; background: #e2e8f0; margin: 0.55rem 0 0.5rem; }

        /* Operations Banner */
        .portal-banner, .hero-panel {
          position: relative; overflow: hidden; border-radius: 16px;
          padding: 1.6rem 2rem;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          box-shadow: var(--card-shadow); margin: 0.3rem 0 1.2rem;
        }
        .hero-kicker, .eyebrow, .section-kicker {
          color: var(--primary); font-size: 0.72rem;
          font-weight: 760; letter-spacing: 0.12em; text-transform: uppercase;
        }
        .section-heading { display: flex; align-items: center; gap: 10px; margin: 0.65rem 0 0.95rem; }
        .section-heading h2 { margin: 0; }

        /* Containers & Cards */
        .glass-card, .case-card, .empty-state, [data-testid="stForm"], [data-testid="stMetric"], [data-testid="stPlotlyChart"] {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          box-shadow: var(--card-shadow);
        }
        .case-card { padding: 1.1rem 1.25rem; margin: 0.55rem 0; position: relative; }
        .case-id { color: #0284c7; font-weight: 760; font-size: 0.88rem; font-family: ui-monospace, monospace; }
        .case-title { color: var(--ink-bright); font-weight: 700; font-size: 1.02rem; margin: 0.35rem 0; }
        .case-meta { font-size: 0.82rem; line-height: 1.6; color: var(--muted) !important; }

        /* Form Controls */
        [data-testid="stTextInput"] input:not(:disabled), [data-testid="stTextArea"] textarea:not(:disabled),
        [data-testid="stDateInput"] input:not(:disabled), [data-testid="stTimeInput"] input:not(:disabled),
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
          color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
          background-color: #f8fafc !important; border-color: #cbd5e1 !important; border-radius: 10px !important;
        }
        [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stSelectbox"] input::placeholder { color: #94a3b8 !important; -webkit-text-fill-color: #94a3b8 !important; opacity: 1 !important; }
        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within, [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
        [data-testid="stDateInput"] [data-baseweb="input"]:focus-within, [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within {
          border-color: var(--primary) !important; box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.2) !important;
        }

        /* Metrics */
        [data-testid="stMetric"] {
          padding: 14px 18px; min-height: 88px; transition: transform 0.18s, border-color 0.18s;
          background: #ffffff; border: 1px solid #e2e8f0;
        }
        [data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: var(--primary); }
        [data-testid="stMetricLabel"] p { color: var(--muted) !important; font-weight: 650 !important; font-size: 0.79rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
        [data-testid="stMetricLabel"]:before { content: "◈ "; color: var(--primary); font-size: 0.75rem; }
        [data-testid="stMetricValue"] { color: var(--ink-bright) !important; font-weight: 800; font-size: 1.6rem !important; font-family: ui-monospace, monospace; }

        /* Buttons & CTAs */
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button, [data-testid="stLinkButton"] a {
          border-radius: 10px; min-height: 42px; font-weight: 700;
          transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
        }
        [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
          color: #ffffff;
          background: linear-gradient(110deg, #0d9488, #0284c7);
          border-color: #0d9488;
          box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
        }
        [data-testid="stButton"] button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(13, 148, 136, 0.35);
        }
        [data-testid="stButton"] button:not([kind="primary"]):hover {
          border-color: var(--primary); color: var(--primary);
        }

        /* Radio Navigation */
        [data-testid="stRadio"] [role="radiogroup"] { gap: 6px; flex-wrap: wrap; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] {
          border: 1px solid transparent; border-radius: 9px; background: transparent;
          padding: 8px 14px; transition: all 0.16s; min-height: 38px;
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:hover {
          background: #f1f5f9; border-color: #cbd5e1;
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child { display: none; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div { display: flex; align-items: center; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] p {
          margin: 0; color: #475569; font-size: 13px; font-weight: 650; white-space: nowrap;
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) {
          background: #ffffff;
          border-color: var(--primary);
          box-shadow: 0 2px 8px rgba(13, 148, 136, 0.2);
        }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) p {
          color: var(--primary); font-weight: 750;
        }

        /* Status & Priority Badges */
        .priority-critical, .priority-high, .priority-medium, .priority-low, .status-badge {
          display: inline-flex; align-items: center; border-radius: 999px;
          padding: 0.28rem 0.68rem; font-size: 0.76rem; font-weight: 750;
          line-height: 1.2; white-space: nowrap; letter-spacing: 0.03em;
        }
        .priority-critical { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .priority-high { background: #ffedd5; color: #c2410c; border: 1px solid #fdba74; }
        .priority-medium { background: #fef3c7; color: #b45309; border: 1px solid #fde047; }
        .priority-low { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }

        .status-open, .status-new { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
        .status-assigned { background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; }
        .status-progress { background: #fef3c7; color: #b45309; border: 1px solid #fde047; }
        .status-resolved, .status-closed { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }

        /* Floating Actions */
        .civic-fab {
          position: fixed; z-index: 999; right: max(20px, env(safe-area-inset-right));
          bottom: max(20px, env(safe-area-inset-bottom));
          display: flex; align-items: flex-end; flex-direction: column; gap: 9px;
        }
        .fab-secondary {
          display: flex; flex-direction: column; align-items: flex-end; gap: 8px;
          max-height: 0; opacity: 0; overflow: hidden; pointer-events: none; transform: translateY(8px);
          transition: max-height 0.2s ease, opacity 0.16s ease, transform 0.2s ease;
        }
        .civic-fab:hover .fab-secondary, .civic-fab:focus-within .fab-secondary {
          max-height: 200px; opacity: 1; overflow: visible; pointer-events: auto; transform: translateY(0);
        }
        .fab-action {
          position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 9px;
          min-height: 46px; padding: 0.7rem 1.05rem; border: 1px solid #cbd5e1;
          border-radius: 12px; background: #ffffff; box-shadow: 0 4px 18px rgba(0, 0, 0, 0.1);
          color: #0f172a !important; font-size: 0.88rem; font-weight: 750;
          text-decoration: none; white-space: nowrap;
        }
        .fab-action:hover { border-color: var(--primary); transform: translateY(-2px); }
        .fab-primary {
          min-height: 50px; padding: 0.75rem 1.15rem; border-color: #0d9488;
          background: linear-gradient(115deg, #0d9488, #0284c7); color: #fff !important;
          box-shadow: 0 6px 20px rgba(13, 148, 136, 0.3);
        }
        .fab-icon { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; background: rgba(255, 255, 255, 0.2); font-size: 1rem; }
        .fab-badge {
          position: absolute; top: -6px; right: -6px; display: grid; place-items: center;
          min-width: 22px; height: 22px; padding: 0 5px; border: 2px solid #ffffff;
          border-radius: 999px; background: #ef4444; color: white; font-size: 0.65rem; font-weight: 800;
        }

        /* Success Banner (matches screenshot 1) */
        .conf-banner {
          display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
          background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 14px; padding: 1.15rem 1.4rem;
          margin: 0.5rem 0 1rem; box-shadow: 0 2px 10px rgba(16, 185, 129, 0.08);
        }
        .conf-banner-left { display: flex; align-items: center; gap: 14px; }
        .conf-icon-circle {
          width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
          background: #d1fae5; color: #059669; font-size: 1.25rem; font-weight: 800;
          border: 1px solid #a7f3d0;
        }
        .conf-title { color: #065f46; font-size: 1.12rem; font-weight: 750; margin-bottom: 2px; }
        .conf-sub { color: #047857; font-size: 0.86rem; }

        /* Detail Stat Tile */
        .conf-tile {
          background: #ffffff; border: 1px solid #e2e8f0;
          border-radius: 12px; padding: 0.95rem 1.1rem; height: 100%; min-height: 98px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .conf-tile-label { color: var(--muted); font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
        .conf-tile-val { color: #0f172a; font-size: 1.22rem; font-weight: 800; font-family: ui-monospace, monospace; }

        /* Civic Hero Container */
        .civic-hero-wrap {
          position: relative; overflow: hidden; border-radius: 18px; margin: 0.3rem 0 1.2rem;
          border: 1px solid #e2e8f0; box-shadow: var(--card-shadow);
          background: linear-gradient(135deg, #f0fdf4 0%, #f0f9ff 50%, #eff6ff 100%);
        }
        .civic-hero-img { width: 100%; height: 380px; object-fit: cover; display: block; }
        .civic-hero-scrim {
          position: absolute; inset: 0;
          background: linear-gradient(90deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.85) 45%, rgba(255, 255, 255, 0.2) 100%);
        }
        .civic-hero-content {
          position: absolute; inset: 0; z-index: 1; display: flex; flex-direction: column;
          justify-content: center; padding: clamp(1.4rem, 4vw, 3rem);
        }
        .civic-hero-script {
          position: absolute; right: 28px; top: 24px; z-index: 1;
          font-family: "Brush Script MT", cursive, sans-serif; font-size: 1.55rem;
          color: #0284c7; text-shadow: 0 1px 4px rgba(255, 255, 255, 0.8);
          transform: rotate(-4deg);
        }
        </style>
        """

    # Common responsive styles for both themes
    common_css = """
    <style>
    /* Explicit button colors work across Streamlit's changing button markup. */
    [data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"] {
      color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
      background: #0f766e !important;
      border: 1px solid #0f766e !important;
    }
    [data-testid="stButton"] button[data-testid="stBaseButton-secondary"],
    [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-secondary"] {
      color: var(--button-secondary-ink) !important;
      -webkit-text-fill-color: var(--button-secondary-ink) !important;
      background: var(--button-secondary-bg) !important;
      border: 1px solid var(--surface-border) !important;
    }
    [data-testid="stButton"] button:focus-visible,
    [data-testid="stFormSubmitButton"] button:focus-visible {
      outline: 3px solid #0e7490 !important; outline-offset: 2px !important;
    }

    /* Road Watch sample display */
    .road-watch-header { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin:0.6rem 0; color:var(--ink-bright); }
    .rw-title { margin:0.35rem 0; color:var(--ink-bright); font-size:1.25rem; font-weight:800; }
    .rw-sub, .rw-quick-copy { color:var(--ink) !important; font-size:0.9rem; line-height:1.55; }
    .rw-header-status { display:flex; flex-wrap:wrap; gap:.5rem; }
    .rw-chip, .rw-hud-tag, .rw-card-tag { display:inline-flex; padding:.35rem .6rem; border-radius:999px; font-size:.72rem; font-weight:750; }
    .rw-chip-urgent { background:#fff7ed; color:#9a3412; border:1px solid #fdba74; }
    .rw-chip-meta { background:#e0f2fe; color:#075985; border:1px solid #7dd3fc; }
    .rw-viewport { position:relative; overflow:hidden; min-height:390px; border-radius:16px; background:#071526; color:#fff; }
    .rw-image { position:absolute; inset:0; width:100%; height:100%; min-height:390px; object-fit:cover; }
    .rw-overlay-scrim { position:absolute; inset:0; background:linear-gradient(180deg,rgba(2,6,23,.35),transparent 34%,rgba(2,6,23,.88)); }
    .rw-hud-top { position:absolute; top:14px; left:14px; right:14px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.5rem; }
    .rw-hud-tag, .rw-hud-telemetry { background:rgba(2,6,23,.88); border:1px solid rgba(255,255,255,.65); color:#fff; padding:.45rem .65rem; border-radius:8px; font-size:.75rem; }
    .rw-target-box { position:absolute; left:50%; top:48%; width:140px; height:90px; transform:translate(-50%,-50%); border:1px solid rgba(34,211,238,.9); }
    .rw-target-label { position:absolute; left:0; top:-1.7rem; padding:.2rem .4rem; color:#fff; background:#0e7490; font-size:.68rem; font-weight:750; }
    .rw-hud-bottom { position:absolute; left:0; right:0; bottom:0; padding:1rem; color:#fff; background:rgba(2,6,23,.88); }
    .rw-meta-row { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; }
    .rw-meta-item { display:flex; flex-direction:column; gap:.25rem; min-width:0; }
    .rw-meta-label { color:#cbd5e1; font-size:.68rem; font-weight:750; letter-spacing:.04em; }
    .rw-meta-val { color:#fff; font-size:.8rem; overflow-wrap:anywhere; }
    .rw-disclaimer-bar { margin-top:.75rem; color:#fff; font-size:.76rem; }
    .rw-quick-copy { padding:.35rem 0; }
    .rw-card { overflow:hidden; border:1px solid var(--surface-border); border-radius:12px; background:var(--surface-card); color:var(--ink-bright); }
    .rw-card-thumb-wrap { position:relative; height:120px; background:#071526; }
    .rw-card-thumb { width:100%; height:100%; object-fit:cover; }
    .rw-card-body { padding:.75rem; }
    .rw-card-title { color:var(--ink-bright); font-weight:750; }
    .rw-card-desc, .rw-card-meta { color:var(--ink); font-size:.78rem; line-height:1.45; margin-top:.35rem; }
    .rw-card-tag { margin-top:.5rem; background:#e0f2fe; color:#075985; }

    /* Responsive Breakpoints */
    @media (max-width: 900px) {
      [data-testid="stMainBlockContainer"] { padding: 0.6rem 1rem 8rem; }
      .civic-hero-img { height: 320px; }
      .civic-hero-script { display: none; }
    }
    @media (max-width: 640px) {
      [data-testid="stMainBlockContainer"] { padding: 0.4rem 0.7rem 9rem; }
      .brand-name { font-size: 17px; }
      .brand-seal { width: 40px; height: 40px; }
      .civic-hero-img { height: 260px; }
      .conf-banner-left { flex-direction: column; align-items: flex-start; }
      .rw-meta-row { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .rw-viewport, .rw-image { min-height:460px; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
      }
    }
    </style>
    """

    st.markdown(css + common_css, unsafe_allow_html=True)
