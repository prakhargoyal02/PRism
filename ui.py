"""PRism visual helpers.

This file controls colours, motion and reusable visual blocks.
The goal is to keep app.py focused on app logic instead of CSS.
"""

from __future__ import annotations

from html import escape
import streamlit as st
import streamlit.components.v1 as components


def apply_theme() -> None:
    """Apply the full-page PRism visual system."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --bg: #05070c;
            --bg-2: #090d16;
            --panel: rgba(15, 20, 31, .72);
            --panel-strong: rgba(17, 23, 36, .92);
            --line: rgba(205, 214, 255, .14);
            --text: #f7f6fb;
            --muted: #9da3b4;
            --lav: #b9a7ff;
            --violet: #8f6dff;
            --mint: #79ead6;
            --blue: #77a8ff;
            --pink: #df9dff;
        }

        html { scroll-behavior: smooth; background: var(--bg); }
        body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .block-container { max-width: 1320px; padding-top: .8rem; padding-bottom: 5rem; }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 74% 8%, rgba(152, 102, 255, .12), transparent 27%),
                radial-gradient(circle at 18% 46%, rgba(105, 232, 214, .07), transparent 26%),
                linear-gradient(180deg, #05070c 0%, #080b13 47%, #05070c 100%);
            overflow-x: hidden;
        }

        /* Continuous moving light field behind the WHOLE page. */
        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: -28vh -20vw;
            pointer-events: none;
            z-index: 0;
            opacity: .44;
            filter: blur(42px) saturate(120%);
            background:
                radial-gradient(ellipse at 15% 26%, rgba(180, 149, 255, .18), transparent 24%),
                radial-gradient(ellipse at 63% 18%, rgba(102, 126, 255, .14), transparent 26%),
                radial-gradient(ellipse at 88% 60%, rgba(121, 234, 214, .09), transparent 22%),
                conic-gradient(from 230deg at 52% 48%, transparent 0 20%, rgba(177,135,255,.11) 28%, transparent 37% 66%, rgba(91,165,255,.08) 74%, transparent 83%);
            animation: prismField 18s ease-in-out infinite alternate;
        }

        [data-testid="stAppViewContainer"]::after {
            content: "";
            position: fixed;
            left: -10vw;
            right: -10vw;
            top: 34vh;
            height: 34vh;
            pointer-events: none;
            z-index: 0;
            opacity: .22;
            filter: blur(34px);
            background: linear-gradient(100deg, transparent 4%, rgba(130,93,255,.28) 29%, rgba(223,157,255,.19) 50%, rgba(108,196,255,.16) 69%, transparent 96%);
            transform: rotate(-8deg) skewY(-4deg);
            animation: ribbonMove 12s ease-in-out infinite alternate;
        }

        @keyframes prismField {
            from { transform: translate3d(-2vw,-1vh,0) scale(1); }
            to   { transform: translate3d(4vw,3vh,0) scale(1.08) rotate(2deg); }
        }
        @keyframes ribbonMove {
            from { transform: translateX(-4vw) rotate(-8deg) skewY(-4deg) scaleY(.82); }
            to   { transform: translateX(5vw) rotate(-4deg) skewY(2deg) scaleY(1.1); }
        }

        /* Keep Streamlit content above the ambient background. */
        [data-testid="stMainBlockContainer"], [data-testid="stHeader"] { position: relative; z-index: 2; }
        [data-testid="stHeader"] { background: rgba(5,7,12,.30); backdrop-filter: blur(14px); }

        /* Streamlit widgets */
        div[data-testid="stMetric"] {
            animation: smallReveal linear both;
            animation-timeline: view();
            animation-range: entry 0% cover 24%;
            background: linear-gradient(145deg, rgba(22,27,41,.76), rgba(10,14,23,.80));
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 14px 16px;
            box-shadow: 0 18px 50px rgba(0,0,0,.12);
            transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            border-color: rgba(185,167,255,.40);
            box-shadow: 0 26px 70px rgba(0,0,0,.24);
        }
        .stButton>button, .stFormSubmitButton>button, .stDownloadButton>button {
            border-radius: 999px;
            font-weight: 700;
            border-color: rgba(205,214,255,.18);
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }
        .stButton>button:hover, .stFormSubmitButton>button:hover, .stDownloadButton>button:hover {
            transform: translateY(-2px);
            border-color: rgba(185,167,255,.50);
            box-shadow: 0 14px 34px rgba(0,0,0,.24);
        }
        .stButton>button:active, .stFormSubmitButton>button:active, .stDownloadButton>button:active { transform: scale(.985); }

        /* Big scroll-led hero. */
        .prism-hero {
            min-height: 72vh;
            display: flex;
            align-items: center;
            position: relative;
            overflow: hidden;
            border-radius: 30px;
            border: 1px solid rgba(215,221,255,.13);
            background:
                radial-gradient(circle at 73% 45%, rgba(187,158,255,.17), transparent 20%),
                radial-gradient(circle at 78% 46%, rgba(115,92,255,.18), transparent 34%),
                linear-gradient(145deg, rgba(9,12,20,.84), rgba(12,15,25,.58));
            box-shadow: 0 45px 120px rgba(0,0,0,.28);
            isolation: isolate;
        }
        .prism-hero::before {
            content: "";
            position: absolute;
            width: 65%;
            aspect-ratio: 1.7/1;
            right: -4%;
            top: 12%;
            border-radius: 48% 52% 56% 44% / 52% 43% 57% 48%;
            background:
                radial-gradient(circle at 35% 38%, rgba(246,240,255,.88), rgba(190,162,255,.58) 23%, rgba(123,90,255,.28) 52%, transparent 70%);
            filter: blur(3px) drop-shadow(0 0 75px rgba(153,112,255,.28));
            transform: rotate(-8deg);
            animation: heroBlob 9s ease-in-out infinite alternate;
            z-index: -1;
        }
        .prism-hero::after {
            content: "";
            position: absolute;
            width: 58%;
            height: 110%;
            right: 2%;
            top: -5%;
            opacity: .36;
            background: repeating-linear-gradient(98deg, transparent 0 10px, rgba(255,255,255,.08) 11px, transparent 12px 28px);
            mask-image: radial-gradient(ellipse at 55% 50%, #000 15%, transparent 66%);
            animation: lineDrift 14s linear infinite;
            z-index: -1;
        }
        @keyframes heroBlob {
            0%   { transform: rotate(-8deg) scale(.96) translate3d(0,0,0); border-radius: 48% 52% 56% 44% / 52% 43% 57% 48%; }
            50%  { transform: rotate(-2deg) scale(1.04) translate3d(-3%,2%,0); border-radius: 57% 43% 44% 56% / 43% 59% 41% 57%; }
            100% { transform: rotate(5deg) scale(.98) translate3d(2%,-2%,0); border-radius: 41% 59% 51% 49% / 62% 39% 61% 38%; }
        }
        @keyframes lineDrift { to { transform: translateX(70px); } }

        .prism-hero-copy { width: min(720px, 63%); padding: 8vh 6vw; }
        .prism-kicker { color: var(--lav); font-size: .76rem; letter-spacing: .20em; font-weight: 800; text-transform: uppercase; }
        .prism-hero-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(3.2rem, 7.3vw, 7.8rem);
            line-height: .88;
            letter-spacing: -.065em;
            font-weight: 650;
            margin: 1.2rem 0 1.4rem;
            max-width: 850px;
        }
        .prism-hero-title span {
            background: linear-gradient(90deg,#ffffff 0%,#d8cfff 32%,#a989ff 62%,#86d6ff 100%);
            -webkit-background-clip: text; background-clip: text; color: transparent;
            background-size: 220% 100%; animation: titleFlow 8s linear infinite;
        }
        @keyframes titleFlow { to { background-position: 220% 0; } }
        .prism-hero-sub { color: #b8bdca; max-width: 650px; font-size: 1.08rem; line-height: 1.65; }
        .prism-scroll-cue { margin-top: 3.2rem; color: #7f8492; letter-spacing: .18em; font-size: .68rem; animation: cue 2.3s ease-in-out infinite; }
        @keyframes cue { 50% { opacity: .36; transform: translateY(4px); } }

        /* Sticky anchor navigation for the read-only Explore page. */
        .prism-scroll-nav {
            position: sticky;
            top: .55rem;
            z-index: 998;
            display: flex;
            gap: .45rem;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            margin: 1rem auto 2.2rem;
            width: fit-content;
            max-width: 96%;
            padding: .42rem;
            border: 1px solid rgba(205,214,255,.13);
            border-radius: 999px;
            background: rgba(8,11,18,.74);
            backdrop-filter: blur(18px);
            box-shadow: 0 20px 55px rgba(0,0,0,.20);
        }
        .prism-scroll-nav a {
            text-decoration: none !important;
            color: #b8bdc9 !important;
            padding: .52rem .85rem;
            border-radius: 999px;
            font-size: .82rem;
            font-weight: 700;
            transition: .2s ease;
        }
        .prism-scroll-nav a:hover { color: white !important; background: rgba(185,167,255,.12); transform: translateY(-1px); }

        .prism-anchor { scroll-margin-top: 5.5rem; height: 1px; }
        .prism-section {
            position: relative;
            padding: 5rem 0 3.6rem;
            min-height: 48vh;
            animation: sectionReveal linear both;
            animation-timeline: view();
            animation-range: entry 5% cover 34%;
        }
        @keyframes sectionReveal {
            from { opacity: .18; transform: translateY(55px) scale(.985); filter: blur(3px); }
            to   { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
        }
        .prism-section-num { color: #6f7481; font-size: .72rem; letter-spacing: .2em; font-weight: 800; }
        .prism-section-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(2rem, 4vw, 4.2rem);
            letter-spacing: -.045em;
            line-height: .96;
            margin: .55rem 0 .85rem;
            max-width: 900px;
        }
        .prism-section-copy { color: var(--muted); font-size: 1rem; line-height: 1.62; max-width: 760px; margin-bottom: 1.6rem; }

        .prism-card {
            animation: smallReveal linear both;
            animation-timeline: view();
            animation-range: entry 0% cover 25%;
            position: relative;
            overflow: hidden;
            border: 1px solid var(--line);
            background: linear-gradient(145deg, rgba(20,25,39,.74), rgba(8,12,20,.80));
            border-radius: 20px;
            padding: 1rem 1.05rem;
            transition: transform .30s cubic-bezier(.2,.72,.25,1), border-color .28s ease, box-shadow .28s ease;
        }
        .prism-card::before {
            content: ""; position: absolute; inset: 0; pointer-events: none;
            background: radial-gradient(circle at 0 0, rgba(185,167,255,.12), transparent 35%);
            opacity: 0; transition: opacity .28s ease;
        }
        .prism-card:hover { transform: translateY(-6px); border-color: rgba(185,167,255,.35); box-shadow: 0 25px 70px rgba(0,0,0,.20); }
        .prism-card:hover::before { opacity: 1; }
        .prism-pill { display:inline-block; padding:.22rem .55rem; border-radius:999px; border:1px solid rgba(185,167,255,.24); color:#cbbdff; font-size:.70rem; letter-spacing:.08em; margin-bottom:.55rem; }
        .prism-card-title { color:white; font-size:1.05rem; font-weight:700; margin-bottom:.28rem; }
        .prism-card-copy { color:#9da3b4; font-size:.91rem; line-height:1.5; }

        /* Keep PRism card rows visually aligned in both local app.py and the
           Streamlit Community Cloud entrypoint. */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card) {
            align-items: stretch !important;
            margin-bottom: .85rem !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
            > div[data-testid="stColumn"] {
            align-self: stretch !important;
            display: flex !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
            > div[data-testid="stColumn"] > div {
            width: 100% !important;
            height: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
            div[data-testid="stElementContainer"]:has(.prism-card),
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
            div[data-testid="stMarkdownContainer"]:has(.prism-card) {
            width: 100% !important;
            height: 100% !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
            .prism-card {
            width: 100% !important;
            height: 100% !important;
            box-sizing: border-box !important;
        }

        @keyframes smallReveal {
            from { opacity:.28; transform:translateY(28px) scale(.985); }
            to { opacity:1; transform:translateY(0) scale(1); }
        }
        .prism-story-line {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(185,167,255,.44), rgba(121,234,214,.22), transparent);
            transform-origin: left center;
            animation: lineGrow linear both;
            animation-timeline: view();
            animation-range: entry 20% cover 55%;
        }
        @keyframes lineGrow { from { transform: scaleX(.05); opacity:.1; } to { transform: scaleX(1); opacity:1; } }

        .prism-quote {
            font-family:'Space Grotesk',sans-serif;
            font-size: clamp(1.75rem, 3.6vw, 3.8rem);
            line-height:1.04;
            letter-spacing:-.04em;
            max-width: 980px;
            color:#eceaf5;
            margin: 1rem 0 2rem;
        }
        .prism-quote span { color:#a990ff; }

        .prism-footer-cta {
            min-height: 44vh;
            display:flex;
            flex-direction:column;
            justify-content:center;
            align-items:center;
            text-align:center;
            margin-top: 3rem;
            border-top:1px solid rgba(205,214,255,.12);
        }
        .prism-footer-cta h2 { font-family:'Space Grotesk',sans-serif;font-size:clamp(2.3rem,5vw,5rem);letter-spacing:-.05em;margin:.4rem 0; }
        .prism-footer-cta p { color:#989eab; max-width:680px; }

        /* The diagram's center PRism is the only floating object. */
        .prism-system {
            position:relative;
            min-height: 620px;
            margin: 4rem 0 6rem;
            border-radius: 28px;
            overflow:hidden;
            border:1px solid rgba(205,214,255,.12);
            background:
                radial-gradient(circle at 50% 58%, rgba(126,91,255,.17), transparent 25%),
                linear-gradient(180deg, rgba(9,12,20,.84), rgba(5,7,12,.96));
        }
        .prism-system::before {
            content:""; position:absolute; inset:0; pointer-events:none; opacity:.22;
            background:repeating-linear-gradient(100deg,transparent 0 24px,rgba(148,125,255,.08) 25px,transparent 26px 52px);
            mask-image:radial-gradient(ellipse at center,#000 8%,transparent 72%);
            animation:lineDrift 18s linear infinite;
        }
        .system-title { position:absolute; left:50%; top:8%; transform:translateX(-50%); width:min(920px,86%); text-align:center; font-family:'Space Grotesk',sans-serif; font-size:clamp(2rem,4vw,4.2rem); line-height:1; letter-spacing:-.045em; }
        .system-title .signal-word { display:inline-block; color:#a98cff; animation:signalWord 3.2s ease-in-out infinite; }
        @keyframes signalWord { 50% { transform:translateY(-4px); filter:drop-shadow(0 0 16px rgba(169,140,255,.42)); } }

        .system-center {
            position:absolute; left:50%; top:60%;
            transform:translate(-50%,-50%);
            width:150px; height:150px; border-radius:38px;
            display:grid; place-items:center;
            color:white; font-weight:800; letter-spacing:.05em;
            border:1px solid rgba(205,214,255,.26);
            background:linear-gradient(145deg,rgba(25,25,40,.96),rgba(14,10,31,.96));
            box-shadow:0 0 0 16px rgba(155,120,255,.055),0 0 82px rgba(123,86,255,.26);
            z-index:4;
            animation:systemCoreFloat 5.8s ease-in-out infinite;
        }
        .system-center::before {
            content:""; width:66px; height:66px;
            background:linear-gradient(135deg,#e1d5ff 0%,#b79cff 42%,#7959f0 100%);
            clip-path:polygon(0 0,100% 0,100% 100%,0 100%,0 58%,58% 58%);
            filter:drop-shadow(0 0 16px rgba(169,140,255,.42));
            animation:centerPulse 3s ease-in-out infinite, systemLogoTilt 7s ease-in-out infinite;
        }
        @keyframes systemCoreFloat {
            0%,100% { transform:translate(-50%,-50%) translateY(0) rotate(-1deg); }
            50% { transform:translate(-50%,-50%) translateY(-13px) rotate(1.4deg); }
        }
        @keyframes systemLogoTilt {
            0%,100% { transform:rotate(-2deg) scale(1); }
            50% { transform:rotate(3deg) scale(1.035); }
        }
        @keyframes centerPulse { 50%{transform:scale(1.08) rotate(3deg);filter:brightness(1.25)} }

        .system-node { position:absolute; min-width:178px; padding:13px 15px; border-radius:14px; border:1px solid rgba(205,214,255,.16); background:rgba(20,23,35,.90); color:#eef0f7; font-size:.74rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; box-shadow:0 16px 45px rgba(0,0,0,.18); z-index:3; display:grid; grid-template-columns:34px 1fr; gap:10px; align-items:center; }
        .system-node small { display:block; color:#8e94a4; font-weight:600; letter-spacing:0; text-transform:none; margin-top:4px; }
        .system-icon { width:32px; height:32px; border-radius:10px; display:grid; place-items:center; border:1px solid rgba(185,167,255,.22); background:linear-gradient(145deg,rgba(159,124,255,.18),rgba(121,234,214,.05)); color:#cdbfff; font-size:1.05rem; box-shadow:inset 0 0 18px rgba(167,136,255,.07); }
        .node-a{left:5%;top:34%}.node-b{left:5%;top:57%}.node-c{left:5%;top:80%}.node-d{right:5%;top:34%}.node-e{right:5%;top:57%}.node-f{right:5%;top:80%}

        .system-svg { position:absolute; inset:0; width:100%; height:100%; z-index:1; overflow:visible; pointer-events:none; }
        .signal-path { fill:none; stroke:url(#signalGradient); stroke-width:2.35; stroke-linecap:round; stroke-dasharray:8 12; opacity:.88; animation:signalDash 7s linear infinite, signalGlow 3.4s ease-in-out infinite alternate; }
        .signal-path:nth-of-type(2n) { animation-duration:8.5s,4.2s; }
        .signal-particle { fill:#b9a7ff; filter:drop-shadow(0 0 7px rgba(185,167,255,.75)); }
        @keyframes signalDash { to { stroke-dashoffset:-160; } }
        @keyframes signalGlow { from { opacity:.30; } to { opacity:.92; } }

        .prism-feature-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin:4rem 0 5rem; }
        .prism-feature { min-height:420px; border-radius:22px; padding:1.5rem; border:1px solid rgba(205,214,255,.12); display:flex; flex-direction:column; justify-content:space-between; overflow:hidden; position:relative; transition:.35s cubic-bezier(.2,.75,.2,1); }
        .prism-feature:hover { transform:translateY(-9px) scale(1.015); box-shadow:0 30px 75px rgba(0,0,0,.25); }
        .prism-feature:nth-child(1){background:linear-gradient(160deg,#6f3df2,#5931d8)}
        .prism-feature:nth-child(2){background:linear-gradient(160deg,#12151e,#090b11)}
        .prism-feature:nth-child(3){background:linear-gradient(160deg,#f3f2f8,#e8e7ef);color:#11131a}
        .prism-feature:nth-child(4){background:linear-gradient(160deg,#342849,#211b32)}
        .feature-orbit { width:108px;height:108px;border:1px solid currentColor;border-radius:50%;opacity:.42;position:relative; }
        .feature-orbit::before,.feature-orbit::after{content:"";position:absolute;border:1px solid currentColor;border-radius:50%;inset:18px;opacity:.45}.feature-orbit::after{inset:38px;opacity:.25}.feature-orbit span{position:absolute;inset:0;display:grid;place-items:center;font-size:2rem;font-weight:800;animation:featureSymbol 4s ease-in-out infinite}@keyframes featureSymbol{50%{transform:translateY(-5px) rotate(5deg);filter:drop-shadow(0 0 12px currentColor)}}
        .prism-feature h3{font-family:'Space Grotesk',sans-serif;font-size:1.65rem;margin:0 0 .6rem}.prism-feature p{margin:0;line-height:1.55;opacity:.78}

        .prism-footer-wave { position:relative; min-height:54vh; margin-top:3rem; overflow:hidden; border-top:1px solid rgba(205,214,255,.12); display:flex; align-items:flex-start; justify-content:space-between; padding:5rem 2rem 2rem; }
        .prism-footer-wave::before { content:"";position:absolute;left:-8%;right:-8%;bottom:-18%;height:58%;background:repeating-linear-gradient(6deg,rgba(116,80,255,.8) 0 2px,rgba(163,143,255,.48) 3px 5px,transparent 6px 14px);filter:blur(1px) drop-shadow(0 0 18px rgba(111,80,255,.35));transform:skewY(-7deg);mask-image:linear-gradient(to top,#000 0 62%,transparent 100%);animation:footerWave 10s ease-in-out infinite alternate; }
        .prism-footer-wave::after { content:"";position:absolute;left:-12%;right:-12%;bottom:0;height:38%;background:radial-gradient(ellipse at center,rgba(126,90,255,.35),transparent 66%);filter:blur(28px); }
        @keyframes footerWave { from{transform:translateX(-2%) skewY(-7deg) scaleY(.9)} to{transform:translateX(3%) skewY(-3deg) scaleY(1.15)} }
        .footer-big { position:relative;z-index:2;font-family:'Space Grotesk',sans-serif;font-size:clamp(2.8rem,5vw,6rem);line-height:.96;letter-spacing:-.05em;max-width:780px; }
        .footer-links { position:relative;z-index:2;display:grid;grid-template-columns:repeat(2,minmax(120px,1fr));gap:1rem 2rem;color:#c7cbd5; }
        .footer-links b{color:#757b89;font-size:.72rem;letter-spacing:.12em}.footer-links span{display:block;margin:.55rem 0;color:#eef0f6}

        /* Manage page should feel separate from the public-facing Explore page. */
        .prism-manage-banner {
            border:1px solid rgba(121,234,214,.18);
            background:linear-gradient(120deg,rgba(17,29,40,.84),rgba(14,17,29,.86));
            border-radius:20px;
            padding:1.1rem 1.2rem;
            margin:.6rem 0 1.4rem;
        }

        @media(max-width: 850px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .prism-hero { min-height: 64vh; }
            .prism-hero-copy { width: 92%; padding: 6vh 6vw; }
            .prism-hero::before { width: 92%; right: -42%; opacity: .65; }
            .prism-scroll-nav { border-radius: 18px; }
            .prism-section { padding-top: 3.5rem; }
            .prism-feature-grid { grid-template-columns:1fr 1fr; }
            .prism-system { min-height:760px; }
            .system-center { top:54%; }
            .system-node { min-width:135px; max-width:150px; font-size:.64rem; }
            .node-a,.node-b,.node-c{left:4%}.node-d,.node-e,.node-f{right:4%}
            .prism-footer-wave { flex-direction:column; gap:2rem; }
        }

        @media(max-width: 600px) {
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card) {
                flex-direction: column !important;
                gap: .72rem !important;
                align-items: stretch !important;
                margin-bottom: .72rem !important;
            }
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                > div[data-testid="stColumn"] {
                width: 100% !important;
                min-width: 0 !important;
                flex: 1 1 auto !important;
                display: block !important;
            }
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                > div[data-testid="stColumn"]:not(:has(.prism-card)) {
                display: none !important;
            }
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                > div[data-testid="stColumn"] > div,
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                div[data-testid="stElementContainer"]:has(.prism-card),
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                div[data-testid="stMarkdownContainer"]:has(.prism-card) {
                width: 100% !important;
                height: auto !important;
            }
            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(3)):has(.prism-card)
                .prism-card {
                width: 100% !important;
                height: auto !important;
                min-height: 0 !important;
                margin: 0 !important;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation:none !important; transition:none !important; scroll-behavior:auto !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def system_flow() -> None:
    """Animated system map with curved data signals and distinct visual symbols."""
    st.markdown(
        """
        <section class="prism-system">
          <div class="system-title">PRism turns daily data into one <span class="signal-word">living training flow.</span></div>

          <svg class="system-svg" viewBox="0 0 1000 620" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="signalGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#6f748c" stop-opacity=".15"/>
                <stop offset="48%" stop-color="#79ead6" stop-opacity=".78"/>
                <stop offset="100%" stop-color="#a98cff" stop-opacity=".9"/>
              </linearGradient>
            </defs>
            <!-- Each path starts/ends at the visual center of its matching card. -->
            <path id="p1" class="signal-path" d="M140 246 C300 248 365 310 500 372"/>
            <path id="p2" class="signal-path" d="M140 389 C300 389 365 380 500 372"/>
            <path id="p3" class="signal-path" d="M140 532 C300 528 365 440 500 372"/>
            <path id="p4" class="signal-path" d="M500 372 C635 310 700 248 860 246"/>
            <path id="p5" class="signal-path" d="M500 372 C635 380 700 389 860 389"/>
            <path id="p6" class="signal-path" d="M500 372 C635 440 700 528 860 532"/>
            <circle class="signal-particle" r="4"><animateMotion dur="5s" repeatCount="indefinite"><mpath href="#p1"/></animateMotion></circle>
            <circle class="signal-particle" r="4"><animateMotion dur="5.7s" begin="-2s" repeatCount="indefinite"><mpath href="#p2"/></animateMotion></circle>
            <circle class="signal-particle" r="4"><animateMotion dur="6s" begin="-1s" repeatCount="indefinite"><mpath href="#p3"/></animateMotion></circle>
            <circle class="signal-particle" r="4"><animateMotion dur="5.6s" begin="-.8s" repeatCount="indefinite"><mpath href="#p4"/></animateMotion></circle>
            <circle class="signal-particle" r="4"><animateMotion dur="6.1s" begin="-2.6s" repeatCount="indefinite"><mpath href="#p5"/></animateMotion></circle>
            <circle class="signal-particle" r="4"><animateMotion dur="6.4s" begin="-1.7s" repeatCount="indefinite"><mpath href="#p6"/></animateMotion></circle>
          </svg>

          <div class="system-node node-a"><span class="system-icon">↗</span><span>TRAINING<small>sets · reps · load</small></span></div>
          <div class="system-node node-b"><span class="system-icon">✦</span><span>NUTRITION<small>meals · protein · energy</small></span></div>
          <div class="system-node node-c"><span class="system-icon">◒</span><span>RECOVERY<small>sleep · quality · readiness</small></span></div>
          <div class="system-center">PRism</div>
          <div class="system-node node-d"><span class="system-icon">⌘</span><span>PATTERNS<small>weekly structure</small></span></div>
          <div class="system-node node-e"><span class="system-icon">⌁</span><span>PROGRESS<small>weight · PRs · trends</small></span></div>
          <div class="system-node node-f"><span class="system-icon">→</span><span>NEXT MOVE<small>what to do now</small></span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def feature_cards() -> None:
    """Large editorial cards with distinct symbols for the four PRism pillars."""
    st.markdown(
        """
        <section class="prism-feature-grid">
          <article class="prism-feature"><div class="feature-orbit"><span>↗</span></div><div><h3>Training</h3><p>Log each set, see the next movement and keep weekly structure connected to actual work.</p></div></article>
          <article class="prism-feature"><div class="feature-orbit"><span>✦</span></div><div><h3>Nutrition</h3><p>Keep meals and protein visible without turning the app into a complicated diet spreadsheet.</p></div></article>
          <article class="prism-feature"><div class="feature-orbit"><span>◒</span></div><div><h3>Recovery</h3><p>Sleep sits beside training instead of living in a separate universe, so trends make more sense.</p></div></article>
          <article class="prism-feature"><div class="feature-orbit"><span>⌁</span></div><div><h3>Progress</h3><p>Weight, personal records and consistency become a readable pattern instead of disconnected numbers.</p></div></article>
        </section>
        """,
        unsafe_allow_html=True,
    )

def hero(active_name: str) -> None:
    safe_name = escape(active_name or "your profile")
    st.markdown(
        f"""
        <section class="prism-hero">
          <div class="prism-hero-copy">
            <div class="prism-kicker">PRism · {safe_name}</div>
            <div class="prism-hero-title">Your training,<br><span>always in motion.</span></div>
            <div class="prism-hero-sub">One continuous view of today, training, nutrition, recovery and progress. Scroll to explore. Switch to Live Workout when you need to log sets. Use Manage only when you want to edit.</div>
            <div class="prism-scroll-cue">SCROLL TO EXPLORE ↓</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def scroll_nav() -> None:
    st.markdown(
        """
        <nav class="prism-scroll-nav">
          <a href="#today">Today</a>
          <a href="#training">Training</a>
          <a href="#nutrition">Nutrition</a>
          <a href="#recovery">Recovery</a>
          <a href="#progress">Progress</a>
          <a href="#people">People</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def anchor(name: str) -> None:
    st.markdown(f'<div id="{escape(name)}" class="prism-anchor"></div>', unsafe_allow_html=True)


def section_start(number: str, title: str, copy: str = "") -> None:
    # This is a complete HTML block on purpose. Streamlit renders each call in
    # its own container, so we avoid leaving an HTML tag open across widgets.
    st.markdown(
        f"""
        <div class="prism-section">
          <div class="prism-section-num">{escape(number)}</div>
          <div class="prism-section-title">{escape(title)}</div>
          <div class="prism-section-copy">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_end() -> None:
    st.markdown("<div class='prism-story-line'></div>", unsafe_allow_html=True)


def statement(text: str, accent: str) -> None:
    st.markdown(
        f'<div class="prism-quote">{escape(text)} <span>{escape(accent)}</span></div>',
        unsafe_allow_html=True,
    )


def card(title: str, copy: str, badge: str = "") -> None:
    badge_html = f'<div class="prism-pill">{escape(badge)}</div>' if badge else ""
    st.markdown(
        f"""
        <div class="prism-card">
          {badge_html}
          <div class="prism-card-title">{escape(title)}</div>
          <div class="prism-card-copy">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def manage_banner(active_name: str) -> None:
    st.markdown(
        f"""
        <div class="prism-manage-banner">
          <b>Manage mode · {escape(active_name)}</b><br>
          <span style="color:#9da3b4">Editing tools live here so the Explore page stays clean. Changes save to SQLite and refresh CSV backups automatically.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer_cta() -> None:
    st.markdown(
        """
        <section class="prism-footer-wave">
          <div class="footer-big">Build a stronger week.<br>Then understand why it worked.</div>
          <div class="footer-links">
            <div><b>EXPLORE</b><span>Training</span><span>Nutrition</span><span>Recovery</span></div>
            <div><b>PRISM</b><span>Live Workout</span><span>People</span><span>CSV Backups</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def rest_timer(seconds: int) -> None:
    """Small JavaScript rest timer for Live Workout mode."""
    seconds = max(int(seconds), 0)
    components.html(
        f"""
        <div class="timer-shell">
          <div><div class="label">REST TIMER</div><div id="timer">--:--</div></div>
          <div class="orbit"><i></i></div>
          <button onclick="startTimer()">Restart</button>
        </div>
        <style>
        *{{box-sizing:border-box}}body{{margin:0;background:transparent;font-family:Inter,Arial,sans-serif}}
        .timer-shell{{height:98px;padding:14px 17px;border-radius:20px;border:1px solid rgba(205,214,255,.15);background:linear-gradient(135deg,#0c1019,#151126);color:#fff;display:flex;align-items:center;gap:18px;overflow:hidden;position:relative}}
        .label{{font-size:10px;letter-spacing:1.8px;color:#b9a7ff;font-weight:800}}#timer{{font-size:34px;font-weight:800;margin-top:2px;min-width:100px}}
        button{{margin-left:auto;background:linear-gradient(90deg,#7f66ff,#a980ff);color:white;border:0;border-radius:999px;padding:10px 16px;font-weight:700;cursor:pointer;transition:.2s}}button:hover{{transform:translateY(-2px);box-shadow:0 8px 25px rgba(112,90,255,.3)}}
        .orbit{{position:absolute;right:104px;width:76px;height:76px;border-radius:50%;border:1px solid rgba(185,167,255,.18);animation:spin 6s linear infinite}}.orbit i{{position:absolute;left:50%;top:-3px;width:7px;height:7px;border-radius:50%;background:#79ead6;box-shadow:0 0 14px #79ead6}}
        @keyframes spin{{to{{transform:rotate(360deg)}}}}
        </style>
        <script>
        let total={seconds}, left=total, handle; const el=document.getElementById('timer');
        function draw(){{const m=Math.floor(left/60).toString().padStart(2,'0');const s=(left%60).toString().padStart(2,'0');el.textContent=m+':'+s;}}
        function startTimer(){{clearInterval(handle);left=total;el.style.color='#fff';draw();handle=setInterval(()=>{{if(left<=0){{clearInterval(handle);el.textContent='READY';el.style.color='#79ead6';return}}left-=1;draw()}},1000)}}
        startTimer();
        </script>
        """,
        height=106,
    )

