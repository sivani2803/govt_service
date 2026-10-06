"""CivicPulse dark civic-tech design system."""
from __future__ import annotations

import streamlit as st


def inject_theme() -> None:
    """Apply shared, responsive styling to Streamlit's native components."""
    st.markdown(
        """
        <style>
        :root {
          --canvas:#071311; --surface:#0e1c1a; --surface-raised:#132321;
          --navy:#0f172a; --slate:#1e293b; --teal:#0f766e; --teal-bright:#0d9488;
          --accent:#f59e0b; --coral:#fb7185; --resolved:#10b981; --surface-border:rgba(255,255,255,.12);
          --ink:#ecf5f3; --muted:#9aadaa; --line:rgba(255,255,255,.09);
          --critical:#ef4444; --warning:#f59e0b; --success:#10b981; --info:#38bdf8;
          --glass-shadow:0 8px 32px rgba(0,0,0,.37);
        }
        html, body, [class*="css"] { font-family:Inter,"Segoe UI",Arial,sans-serif; color:var(--ink); }
        .stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] {
          color:var(--ink); background:radial-gradient(ellipse at 14% -15%,#123b35 0,transparent 36%),
          radial-gradient(ellipse at 93% 4%,#172a3e 0,transparent 30%),var(--canvas);
        }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"] { display:none; }
        [data-testid="stToolbar"],#MainMenu,footer { visibility:hidden; }
        [data-testid="stMainBlockContainer"] { max-width:1480px; padding:1.15rem 2rem 4rem; }
        .block-container { padding-top:.6rem; }
        h1,h2,h3,h4 { color:var(--ink) !important; letter-spacing:-.025em; }
        h1 { font-size:1.9rem !important; font-weight:760 !important; }
        h2 { font-size:1.34rem !important; font-weight:720 !important; }
        h3 { font-size:1.04rem !important; font-weight:690 !important; }
        p,[data-testid="stMarkdownContainer"] { color:#d1dfdc; }
        [data-testid="stCaptionContainer"],.case-meta,.brand-subtitle { color:var(--muted) !important; }
        .app-brand { display:flex; align-items:center; gap:14px; min-height:68px; }
        .brand-seal { width:50px;height:50px;border-radius:16px;display:flex;align-items:center;justify-content:center;
          background:linear-gradient(145deg,#0d9488,#0f766e);color:white;border:1px solid rgba(153,246,228,.32);
          font-size:24px;box-shadow:0 0 26px rgba(13,148,136,.27); }
        .brand-name { font-size:19px;line-height:1.2;font-weight:780;color:var(--ink); }
        .brand-subtitle { font-size:11px;margin-top:5px;letter-spacing:.1em; }
        .brand-utility { text-align:right;color:var(--muted);font-size:12px;line-height:1.65; }
        .brand-utility strong { color:var(--ink); }
        .live-dot { color:#10b981;font-size:15px;vertical-align:-1px;text-shadow:0 0 12px #10b981; }
        .utility-pill,.role-pill { display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:.2rem .55rem;background:rgba(13,148,136,.1);color:#a7f3e6;font-size:.68rem;font-weight:750;letter-spacing:.035em; }
        .role-pill { margin-left:.3rem;background:rgba(56,189,248,.1);color:#bae6fd; }
        .avatar-chip { display:inline-flex;vertical-align:middle;align-items:center;justify-content:center;width:25px;height:25px;border-radius:50%;background:linear-gradient(145deg,#0d9488,#0f766e);color:white;font-weight:750; }
        .top-rule { height:1px;background:var(--line);margin:.55rem 0 .4rem; }
        .portal-banner,.hero-panel { position:relative;overflow:hidden;border-radius:20px;padding:1.7rem 1.9rem;
          background:linear-gradient(118deg,rgba(15,118,110,.34),rgba(15,23,42,.78) 75%);
          border:1px solid rgba(94,234,212,.18);box-shadow:var(--glass-shadow);margin:.3rem 0 1.3rem; }
        .portal-banner:after,.hero-panel:after { content:"";position:absolute;width:280px;height:280px;right:-80px;top:-180px;
          border:1px solid rgba(153,246,228,.18);border-radius:50%;box-shadow:0 0 0 35px rgba(153,246,228,.035),0 0 0 72px rgba(153,246,228,.025); }
        .portal-banner h1 { margin:0 0 .4rem;font-size:1.72rem !important; }
        .portal-banner p { color:#c5ded9;max-width:780px;margin:0; }
        .hero-kicker,.eyebrow,.section-kicker { color:#82d8ca;font-size:.72rem;font-weight:760;letter-spacing:.12em;text-transform:uppercase; }
        .hero-title { color:#f4fffc;font-size:2rem;line-height:1.18;font-weight:780;letter-spacing:-.035em;margin:.45rem 0 .55rem; }
        .hero-copy { color:#c5ded9;font-size:.96rem;max-width:680px;line-height:1.6; }
        .section-heading { display:flex;align-items:center;gap:10px;margin:.45rem 0 .85rem; }
        .section-heading h2 { margin:0; }
        .flow-strip { display:flex;gap:10px;margin:.8rem 0 1.6rem;flex-wrap:wrap; }
        .flow-step { flex:1 1 140px;background:rgba(15,28,26,.77);border:1px solid var(--line);border-radius:13px;padding:13px 15px;backdrop-filter:blur(14px); }
        .flow-step strong { display:block;color:#dff7f1;font-size:.79rem;letter-spacing:.07em;text-transform:uppercase; }
        .flow-step span { display:block;color:var(--muted);font-size:.78rem;margin-top:5px;line-height:1.45; }
        .glass-card,.case-card,.empty-state,[data-testid="stForm"],[data-testid="stMetric"],[data-testid="stPlotlyChart"] {
          background:rgba(14,28,26,.74);border:1px solid var(--line);border-radius:12px;
          box-shadow:var(--glass-shadow),inset 0 1px rgba(255,255,255,.025);backdrop-filter:blur(16px);
        }
        .case-card { padding:1rem 1.15rem;margin:.55rem 0; }
        .case-id { color:#5eead4;font-weight:760;font-size:.87rem; }
        .case-title { color:var(--ink);font-weight:710;font-size:1rem;margin:.34rem 0; }
        .case-meta { font-size:.81rem;line-height:1.6; }
        .empty-state { text-align:center;border-style:dashed;padding:2.3rem 1.4rem;margin:.8rem 0; }
        .empty-icon { font-size:2rem;margin-bottom:.4rem; }
        .empty-title { color:var(--ink);font-weight:730;font-size:1.05rem; }
        .empty-copy { color:var(--muted);max-width:470px;margin:.35rem auto 0;line-height:1.55;font-size:.9rem; }
        [data-testid="stMetric"] { padding:15px 17px;min-height:88px;transition:transform .18s,border-color .18s; }
        [data-testid="stMetric"]:hover { transform:translateY(-2px);border-color:rgba(45,212,191,.42); }
        [data-testid="stMetricLabel"] p { color:var(--muted) !important;font-weight:630 !important;font-size:.79rem !important; }
        [data-testid="stMetricLabel"]:before { content:"◈";color:#5eead4;font-size:.78rem;margin-right:.4rem; }
        [data-testid="stMetricValue"] { color:#edfffb !important;font-weight:770;font-size:1.55rem !important; }
        [data-testid="stPlotlyChart"] { padding:8px;margin:.15rem 0 .8rem; }
        [data-testid="stForm"] { padding:1.15rem 1.3rem 1.25rem; }
        [data-testid="stTextInput"] input:not(:disabled),[data-testid="stTextArea"] textarea:not(:disabled),
        [data-testid="stDateInput"] input:not(:disabled),[data-testid="stTimeInput"] input:not(:disabled),
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
          color:var(--ink) !important;-webkit-text-fill-color:var(--ink) !important;background-color:#10201e !important;
          border-color:#304440 !important;border-radius:11px !important; }
        [data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder,
        [data-testid="stSelectbox"] input::placeholder { color:#91a7a2 !important;-webkit-text-fill-color:#91a7a2 !important;opacity:1 !important; }
        [data-testid="stSelectbox"] [data-baseweb="select"] div,[data-testid="stSelectbox"] input { color:var(--ink) !important;-webkit-text-fill-color:var(--ink) !important; }
        [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,[data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within,
        [data-testid="stDateInput"] [data-baseweb="input"]:focus-within,[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within {
          border-color:var(--teal-bright) !important;box-shadow:0 0 0 2px rgba(13,148,136,.25) !important; }
        [data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button,[data-testid="stLinkButton"] a {
          border-radius:11px;min-height:42px;font-weight:680;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease; }
        [data-testid="stButton"] button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"] {
          color:white;background:linear-gradient(110deg,#0f766e,#0d9488);border-color:#0d9488;box-shadow:0 5px 17px rgba(13,148,136,.23); }
        [data-testid="stButton"] button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
          transform:translateY(-2px);box-shadow:0 8px 24px rgba(13,148,136,.34); }
        @keyframes civicPulse { 0%,100%{opacity:.65;} 50%{opacity:1;} }
        [data-testid="stSpinner"] { animation:civicPulse 1.2s ease-in-out infinite; }
        [data-testid="stButton"] button:not([kind="primary"]):hover { border-color:rgba(45,212,191,.55);color:#bffaf0; }
        [data-testid="stRadio"] [role="radiogroup"] { gap:7px;flex-wrap:wrap; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] { border:1px solid transparent;border-radius:10px;background:transparent;padding:8px 13px;transition:all .16s;min-height:39px; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:hover { background:rgba(13,148,136,.13);border-color:var(--line); }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child { display:none; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] > div { display:flex;align-items:center; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"] p { margin:0;color:#bdcfcb;font-size:13px;font-weight:660;white-space:nowrap; }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) { background:linear-gradient(110deg,#0f766e,#0d9488);border-color:#14b8a6;box-shadow:0 3px 12px rgba(13,148,136,.2); }
        [data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) p { color:white; }
        [data-testid="stFileUploader"] section { background:rgba(13,148,136,.055);border:1px dashed rgba(94,234,212,.4);border-radius:14px;transition:background .16s,border-color .16s; }
        [data-testid="stFileUploader"] section:hover { background:rgba(13,148,136,.11);border-color:#0d9488; }
        [data-testid="stFileUploader"] button { border-radius:9px; }
        [data-testid="stCustomComponentV1"]:has(iframe[title*="streamlit_folium"]) { overflow:hidden;border:1px solid var(--line);border-radius:16px;box-shadow:var(--glass-shadow); }
        [data-testid="stCustomComponentV1"]:has(iframe[title*="streamlit_folium"]) iframe { border-radius:16px; }
        [data-testid="stDataFrame"],[data-testid="stTable"] { border:1px solid var(--line);border-radius:12px;overflow:hidden; }
        .priority-high,.priority-medium,.priority-low,.status-badge { display:inline-flex;align-items:center;border-radius:999px;padding:.3rem .7rem;font-size:.77rem;font-weight:750;line-height:1.2;white-space:nowrap; }
        .priority-high { background:rgba(239,68,68,.16);color:#fca5a5; }
        .priority-medium { background:rgba(245,158,11,.16);color:#fcd34d; }
        .priority-low { background:rgba(16,185,129,.16);color:#6ee7b7; }
        .status-open { background:rgba(56,189,248,.14);color:#7dd3fc; }
        .status-progress { background:rgba(245,158,11,.16);color:#fcd34d; }
        .status-resolved,.status-closed { background:rgba(16,185,129,.16);color:#6ee7b7; }
        .location-callout,.helper-panel { background:rgba(13,148,136,.09);border:1px solid rgba(94,234,212,.18);border-left:3px solid var(--teal-bright);border-radius:12px;padding:.95rem 1.05rem;color:#c8dfda;margin:.55rem 0 .9rem; }
        .location-callout strong { color:#99f6e4; }
        .timeline { display:flex;align-items:flex-start;width:100%;margin:1.35rem 0 1.6rem; }
        .timeline-step { position:relative;flex:1;text-align:center;padding:0 3px;color:#8da29d;font-size:.75rem;font-weight:620; }
        .timeline-step:not(:last-child):after { content:"";position:absolute;left:calc(50% + 15px);right:calc(-50% + 15px);top:13px;height:2px;background:#344741; }
        .timeline-step.complete:not(:last-child):after { background:#10b981; }
        .timeline-dot { position:relative;z-index:1;width:27px;height:27px;border:2px solid #425651;border-radius:50%;background:#10201e;margin:0 auto 8px;display:flex;align-items:center;justify-content:center;font-size:.69rem; }
        .timeline-step.complete { color:#6ee7b7; }.timeline-step.complete .timeline-dot { border-color:#10b981;background:#123c30;color:#6ee7b7; }
        .timeline-step.current { color:#99f6e4;font-weight:750; }.timeline-step.current .timeline-dot { border-color:#0d9488;background:#0f766e;color:#fff;box-shadow:0 0 0 4px rgba(13,148,136,.2); }
        .success-panel { background:linear-gradient(135deg,rgba(16,185,129,.14),rgba(14,28,26,.8));border:1px solid rgba(16,185,129,.3);border-radius:17px;padding:1.4rem 1.5rem;margin:.8rem 0 1rem; }
        .success-title { color:#6ee7b7;font-size:1.35rem;font-weight:760; }
        [data-testid="stAlert"] { background:#10201e;border-color:#304440;color:#d8e8e4;border-radius:11px; }
        .media-attribution { color:#98aaa6;font-size:.72rem;line-height:1.4;margin-top:-.3rem; }
        .media-attribution a { color:#5eead4;text-decoration:none; }
        .auth-card { max-width:780px;margin:1.2rem auto;padding:clamp(1.3rem,4vw,2.5rem); }
        .category-visual { position:relative;isolation:isolate;overflow:hidden;aspect-ratio:16/9;min-height:120px;
          width:100%;border:1px solid var(--surface-border);border-radius:14px;background:linear-gradient(125deg,#0f766e,#0f172a 76%);
          box-shadow:0 10px 26px rgba(0,0,0,.28);transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease; }
        .category-visual-card { min-height:150px;border-radius:15px; }
        .category-visual-thumbnail { min-height:102px; }
        .category-visual img { display:block;width:100%;height:100%;min-height:inherit;position:absolute;inset:0;object-fit:cover; }
        .category-visual-card:hover,.category-visual-card:focus-within { transform:translateY(-3px);border-color:rgba(94,234,212,.55);box-shadow:0 15px 32px rgba(0,0,0,.36),0 0 20px rgba(13,148,136,.15); }
        .category-image-overlay { position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,19,17,.04) 15%,rgba(6,19,17,.26) 46%,rgba(5,18,17,.92) 100%);pointer-events:none; }
        .category-visual-title { position:absolute;left:14px;right:12px;bottom:12px;display:flex;align-items:center;gap:9px;color:#fff;pointer-events:none; }
        .category-visual-title span { width:31px;height:31px;display:grid;place-items:center;border-radius:10px;background:rgba(13,148,136,.82);border:1px solid rgba(204,251,241,.32);font-size:1.05rem; }
        .category-visual-title strong { color:#fff;font-size:.96rem;text-shadow:0 1px 8px rgba(0,0,0,.7); }
        .category-attribution { display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin:.34rem 0 .65rem;color:#c1d2ce;font-size:.68rem;line-height:1.4; }
        .category-attribution a,.media-attribution a { color:#7de8d7;text-decoration:underline;text-underline-offset:2px; }
        .category-attribution span { color:#b5c7c2; }
        .category-skeleton { display:flex;align-items:center;justify-content:center;gap:9px;min-height:120px;color:#e5f3ef;font-size:.78rem; }
        .category-skeleton .skeleton-shimmer { position:absolute;inset:0;z-index:0;background:linear-gradient(105deg,#102a27 20%,#1a3b37 38%,#102a27 56%);background-size:220% 100%;animation:civicShimmer 1.5s linear infinite; }
        .category-skeleton > span:not(.skeleton-shimmer),.category-skeleton > strong,.category-skeleton > small { position:relative;z-index:1; }
        .category-skeleton strong { color:#fff; }
        @keyframes civicShimmer { to { background-position-x:-220%; } }
        .category-card-details { min-height:106px;margin-top:.1rem; }
        .citizen-hero { position:relative;isolation:isolate;overflow:hidden;min-height:330px;margin:.3rem 0 0;border:1px solid rgba(94,234,212,.27);
          border-radius:20px;background:linear-gradient(130deg,#0d4b44,#0f172a);box-shadow:var(--glass-shadow); }
        .citizen-hero-image { position:absolute;inset:0;z-index:0;width:100%;height:100%;object-fit:cover; }
        .citizen-hero-overlay { position:absolute;z-index:1;inset:0;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;padding:clamp(1.5rem,5vw,3.2rem);
          background:linear-gradient(90deg,rgba(4,26,24,.96) 0%,rgba(6,35,32,.84) 48%,rgba(7,20,32,.36) 100%); }
        .citizen-hero h1 { max-width:720px;margin:.45rem 0 .55rem;color:#fff !important;font-size:clamp(1.9rem,4vw,3rem) !important;line-height:1.1; }
        .citizen-hero p { max-width:640px;margin:0;color:#e0f2ed;font-size:1rem;line-height:1.65; }
        .hero-cta { display:inline-flex;align-items:center;gap:9px;min-height:46px;margin-top:1.2rem;padding:.72rem 1.05rem;border:1px solid rgba(204,251,241,.34);
          border-radius:12px;background:linear-gradient(110deg,#0f766e,#0d9488);box-shadow:0 7px 22px rgba(13,148,136,.3);
          color:#fff !important;font-weight:760;text-decoration:none;transition:transform .18s ease,box-shadow .18s ease; }
        .hero-cta:hover { transform:translateY(-2px);box-shadow:0 10px 28px rgba(13,148,136,.43); }
        .hero-cta:focus-visible,.civic-fab a:focus-visible { outline:3px solid #fbbf24;outline-offset:3px; }
        .civic-fab { position:fixed;z-index:999;right:max(20px,env(safe-area-inset-right));bottom:max(20px,env(safe-area-inset-bottom));display:flex;align-items:flex-end;flex-direction:column;gap:9px; }
        .fab-secondary { display:flex;flex-direction:column;align-items:flex-end;gap:8px;max-height:0;opacity:0;overflow:hidden;pointer-events:none;transform:translateY(8px);
          transition:max-height .2s ease,opacity .16s ease,transform .2s ease; }
        .civic-fab:hover .fab-secondary,.civic-fab:focus-within .fab-secondary { max-height:190px;opacity:1;overflow:visible;pointer-events:auto;transform:translateY(0); }
        .fab-action { position:relative;display:inline-flex;align-items:center;justify-content:center;gap:9px;min-height:46px;padding:.7rem 1rem;border:1px solid rgba(153,246,228,.28);border-radius:14px;
          background:rgba(13,33,30,.97);box-shadow:0 8px 24px rgba(0,0,0,.38);backdrop-filter:blur(14px);color:#effcf8 !important;font-size:.87rem;font-weight:730;text-decoration:none;white-space:nowrap; }
        .fab-action:hover { border-color:#5eead4;transform:translateY(-2px); }
        .fab-primary { min-height:52px;padding:.78rem 1.1rem;border-color:#43cbb9;background:linear-gradient(115deg,#0f766e,#0d9488);color:#fff !important; }
        .fab-icon { display:inline-grid;place-items:center;width:23px;height:23px;border-radius:8px;background:rgba(255,255,255,.12);font-size:1.05rem; }
        .fab-badge { position:absolute;top:-7px;right:-7px;display:grid;place-items:center;min-width:22px;height:22px;padding:0 5px;border:2px solid #071311;border-radius:999px;background:#ef4444;color:white;font-size:.65rem;font-weight:800; }
        .help-card { height:100%;min-height:180px;padding:1.15rem;border:1px solid var(--line);border-radius:15px;background:linear-gradient(145deg,rgba(19,35,33,.96),rgba(15,23,42,.78));box-shadow:var(--glass-shadow); }
        .help-number { color:#5eead4;font-size:.75rem;font-weight:800;letter-spacing:.11em; }
        .help-card h3 { color:#f1faf7;margin:.55rem 0; }
        .help-card p { color:#d1dfdc;font-size:.88rem;line-height:1.55; }
        .status-new { background:rgba(56,189,248,.16);color:#bae6fd; }
        .status-assigned { background:rgba(167,139,250,.19);color:#ddd6fe; }
        .status-rejected { background:rgba(251,113,133,.17);color:#fecdd3; }
        .priority-critical { background:rgba(239,68,68,.2);color:#fecaca; }
        .priority-high { background:rgba(251,113,133,.17);color:#fecdd3; }
        .priority-medium { background:rgba(245,158,11,.17);color:#fde68a; }
        .priority-low { background:rgba(16,185,129,.17);color:#a7f3d0; }
        [data-testid="stMainBlockContainer"] { padding-bottom:7rem; }
        @media(max-width:768px) {
          [data-testid="stMainBlockContainer"] { padding-left:.8rem;padding-right:.8rem;padding-bottom:9rem; }
          .stHorizontalBlock { flex-wrap:wrap !important;gap:.65rem !important; }
          .stHorizontalBlock > [data-testid="column"] { min-width:min(100%, 20rem) !important;flex:1 1 100% !important; }
          .citizen-hero { min-height:310px; }
          .citizen-hero-overlay { background:linear-gradient(90deg,rgba(4,26,24,.96),rgba(6,35,32,.78)); }
          .civic-fab { right:max(12px,env(safe-area-inset-right));bottom:max(12px,env(safe-area-inset-bottom)); }
          .fab-action { min-height:44px;padding:.65rem .82rem; }
        }
        @media(prefers-reduced-motion:reduce) {
          *,*::before,*::after { scroll-behavior:auto !important;animation-duration:.01ms !important;animation-iteration-count:1 !important;transition-duration:.01ms !important; }
        }
        @media(max-width:900px) { [data-testid="stMainBlockContainer"]{padding:.6rem 1rem 8rem;} [data-testid="stRadio"] label[data-testid="stRadioOption"]{padding:7px 8px;} [data-testid="stRadio"] label[data-testid="stRadioOption"] p{font-size:11px;} .hero-title{font-size:1.65rem;} }
        @media(max-width:620px) { [data-testid="stMainBlockContainer"]{padding:.4rem .75rem 9rem;} .brand-name{font-size:16px;} .brand-seal{width:43px;height:43px;} .brand-utility{font-size:10px;} .portal-banner{padding:1.2rem 1.25rem;} .timeline-step{font-size:.62rem;} .timeline-dot{width:23px;height:23px;} }
        </style>
        """,
        unsafe_allow_html=True,
    )
