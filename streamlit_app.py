"""Public PRism portfolio entrypoint.

Streamlit Community Cloud deploys this file. It enables public demo mode,
keeps app.py rerun-safe, upgrades the CSV picker so one Bundle CSV or multiple
separate CSV files can be imported in one pass, uses India date/time, keeps the
simple two-step private cloud login, and restores that login across normal
browser refreshes with Streamlit Components v2 + browser localStorage.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
import os
import runpy
import time
from pathlib import Path

# Streamlit Community Cloud runs on Linux and otherwise uses the server clock.
# PRism's workout day, meal/sleep/weight defaults, completion logic and
# dashboard all need to agree with the owner's local India calendar day.
os.environ["TZ"] = "Asia/Kolkata"
if hasattr(time, "tzset"):
    time.tzset()

import pandas as pd
import streamlit as st

# We render browser auth + cloud login before app.py, so page configuration must
# happen first. app.py repeats these same settings; Streamlit 1.66 supports this.
st.set_page_config(
    page_title="PRism | Train with intent",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _apply_mobile_polish() -> None:
    """Keep desktop motion intact while making Community Cloud clean on phones."""
    st.markdown(
        """
        <style>
        /* Hide Streamlit Community Cloud chrome, not PRism's own controls. */
        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stToolbarActions"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"] {
            display: none !important;
            visibility: hidden !important;
        }
        [data-testid="stHeader"] {
            min-height: 0 !important;
            height: 0 !important;
            background: transparent !important;
            border: 0 !important;
        }

        /* Three-card Streamlit rows containing PRism cards should line up by
           their tallest card. This keeps the existing desktop grid intact. */
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

        /* Touch charts can leave a black Vega tooltip floating while scrolling. */
        @media (hover: none) and (pointer: coarse) {
            .vg-tooltip,
            .vega-tooltip {
                display: none !important;
                visibility: hidden !important;
            }
        }

        @media (max-width: 600px) {
            .block-container {
                padding-top: .45rem !important;
                padding-left: .72rem !important;
                padding-right: .72rem !important;
                padding-bottom: 3rem !important;
            }

            .prism-hero {
                min-height: 56vh !important;
                border-radius: 22px !important;
            }
            .prism-hero-copy {
                width: 100% !important;
                padding: 4.5rem 1.15rem 3.5rem !important;
            }
            .prism-hero-title {
                font-size: clamp(2.75rem, 15vw, 4.6rem) !important;
                line-height: .92 !important;
            }
            .prism-hero-sub {
                font-size: .98rem !important;
            }

            .prism-scroll-nav {
                width: 100% !important;
                max-width: 100% !important;
                justify-content: flex-start !important;
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                border-radius: 16px !important;
                scrollbar-width: none;
                -webkit-overflow-scrolling: touch;
            }
            .prism-scroll-nav::-webkit-scrollbar { display: none; }
            .prism-scroll-nav a {
                flex: 0 0 auto !important;
                white-space: nowrap !important;
                padding: .48rem .72rem !important;
                font-size: .76rem !important;
            }

            .prism-section {
                min-height: 0 !important;
                padding: 3rem 0 2.2rem !important;
            }
            .prism-section-title {
                font-size: clamp(2rem, 10vw, 3rem) !important;
            }

            /* app.py now creates actual Monday->Sunday rows. On phones simply
               stack each row naturally, full width, and hide unused columns. */
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

            /* The desktop system map uses absolute nodes. On phones use a real
               responsive grid so nothing overlaps the PRism core. */
            .prism-system {
                min-height: 0 !important;
                height: auto !important;
                margin: 2rem 0 3rem !important;
                padding: 1.7rem .8rem 1rem !important;
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
                gap: .75rem !important;
                align-items: stretch !important;
                border-radius: 22px !important;
                overflow: hidden !important;
            }
            .prism-system .system-title {
                position: relative !important;
                left: auto !important;
                top: auto !important;
                transform: none !important;
                width: 100% !important;
                max-width: none !important;
                grid-column: 1 / -1 !important;
                padding: .15rem .25rem .9rem !important;
                margin: 0 auto !important;
                font-size: clamp(1.9rem, 9vw, 2.75rem) !important;
                line-height: 1.02 !important;
            }
            .prism-system .system-svg {
                display: none !important;
            }
            .prism-system .system-center {
                position: relative !important;
                left: auto !important;
                top: auto !important;
                transform: none !important;
                grid-column: 1 / -1 !important;
                justify-self: center !important;
                width: 126px !important;
                height: 126px !important;
                margin: .15rem auto .9rem !important;
                border-radius: 32px !important;
                animation: prismMobileCoreFloat 5.8s ease-in-out infinite !important;
            }
            @keyframes prismMobileCoreFloat {
                0%, 100% { transform: translateY(0) rotate(-1deg); }
                50% { transform: translateY(-8px) rotate(1deg); }
            }
            .prism-system .system-node,
            .prism-system .node-a,
            .prism-system .node-b,
            .prism-system .node-c,
            .prism-system .node-d,
            .prism-system .node-e,
            .prism-system .node-f {
                position: relative !important;
                left: auto !important;
                right: auto !important;
                top: auto !important;
                min-width: 0 !important;
                max-width: none !important;
                width: auto !important;
                padding: 11px 10px !important;
                border-radius: 14px !important;
                font-size: .61rem !important;
                grid-template-columns: 30px minmax(0, 1fr) !important;
                gap: 8px !important;
                align-self: stretch !important;
            }
            .prism-system .system-node small {
                font-size: .68rem !important;
                line-height: 1.32 !important;
            }
            .prism-system .system-icon {
                width: 30px !important;
                height: 30px !important;
            }

            .prism-feature-grid {
                grid-template-columns: 1fr !important;
                gap: .8rem !important;
                margin: 2.2rem 0 3rem !important;
            }
            .prism-feature {
                min-height: 280px !important;
            }
            .prism-footer-wave {
                min-height: 40vh !important;
                padding: 3rem 1rem 1.5rem !important;
            }
        }

        @media (max-width: 380px) {
            .prism-system {
                grid-template-columns: 1fr !important;
            }
            .prism-system .system-title,
            .prism-system .system-center {
                grid-column: 1 !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_apply_mobile_polish()

import cloud_sync
import csv_tools

os.environ["PRISM_PUBLIC_DEMO"] = "1"


# -----------------------------------------------------------------------------
# REFRESH-SAFE BROWSER SESSION (STREAMLIT COMPONENTS V2)
# -----------------------------------------------------------------------------

_BROWSER_STORAGE_KEY = "prism_private_refresh_v3"
_BROWSER_SESSION_JS = r"""
export default function(component) {
  const { data, setStateValue } = component;
  const storageKey = data?.storage_key || "prism_private_refresh_v3";
  const action = data?.action || "read";
  const incomingToken = data?.refresh_token || "";

  let token = "";
  try {
    // Remove tokens left by the two abandoned cookie experiments. PRism no
    // longer stores its auth session in browser cookies.
    document.cookie = "prism_private_refresh_v1=; Max-Age=0; Path=/; Secure; SameSite=Lax";
    document.cookie = "prism_private_refresh_v2=; Max-Age=0; Path=/; Secure; SameSite=Lax";

    if (action === "clear") {
      window.localStorage.removeItem(storageKey);
      token = "";
    } else if (action === "write" && incomingToken) {
      window.localStorage.setItem(storageKey, incomingToken);
      token = incomingToken;
    } else {
      token = window.localStorage.getItem(storageKey) || "";
    }
  } catch (error) {
    token = "";
  }

  // State values rerun Streamlit only when their value actually changes.
  setStateValue("refresh_token", token);
  setStateValue("ready", true);
}
"""

_browser_session_component = st.components.v2.component(
    "prism_browser_session",
    js=_BROWSER_SESSION_JS,
)


def _reset_private_load_state() -> None:
    """Make a restored Supabase session load its private database cleanly."""
    for key in (
        "_prism_cloud_loaded",
        "_prism_cloud_revision",
        "_prism_cloud_last_hash",
        "_prism_cloud_conflict",
        "active_person_id",
        "demo_return_person_id",
    ):
        st.session_state.pop(key, None)
    st.session_state["mode"] = "Explore"
    st.session_state["mode_widget"] = "Explore"


# Imported modules survive Streamlit reruns, so preserve the real sign-out
# function once and restore it after app.py finishes this run.
if not hasattr(cloud_sync, "_prism_original_sign_out_local"):
    cloud_sync._prism_original_sign_out_local = cloud_sync.sign_out_local
_original_sign_out_local = cloud_sync._prism_original_sign_out_local


def _sign_out_and_forget_browser() -> None:
    """Sign out locally and remove this browser's saved refresh session."""
    _original_sign_out_local()
    st.session_state["_prism_browser_clear_auth"] = True
    st.session_state["_prism_skip_browser_restore_once"] = True


cloud_sync.sign_out_local = _sign_out_and_forget_browser

_clear_browser_auth = bool(st.session_state.pop("_prism_browser_clear_auth", False))
_skip_browser_restore = bool(st.session_state.pop("_prism_skip_browser_restore_once", False))
_current_refresh_token = str(st.session_state.get("_prism_cloud_refresh_token", "") or "").strip()

if _clear_browser_auth:
    _browser_action = "clear"
    _browser_write_token = ""
elif cloud_sync.signed_in() and _current_refresh_token:
    _browser_action = "write"
    _browser_write_token = _current_refresh_token
else:
    _browser_action = "read"
    _browser_write_token = ""

_browser_result = _browser_session_component(
    data={
        "action": _browser_action,
        "storage_key": _BROWSER_STORAGE_KEY,
        "refresh_token": _browser_write_token,
    },
    default={"refresh_token": "", "ready": False},
    on_refresh_token_change=lambda: None,
    on_ready_change=lambda: None,
    key="prism_browser_auth",
)

_browser_ready = bool(getattr(_browser_result, "ready", False))
_saved_refresh_token = str(getattr(_browser_result, "refresh_token", "") or "").strip()

# On a brand-new browser/WebSocket session, let the browser component read
# localStorage before PRism decides whether this run is Demo or Private Cloud.
if not _browser_ready:
    st.stop()

# After sign-out, wait until the browser confirms the saved token is cleared.
if _clear_browser_auth and _saved_refresh_token:
    st.stop()

# Restore the private Supabase session before app.py chooses its SQLite storage.
if (
    not cloud_sync.signed_in()
    and not _skip_browser_restore
    and _saved_refresh_token
    and cloud_sync.configured()
):
    try:
        client = cloud_sync._new_client()
        response = client.auth.refresh_session(_saved_refresh_token)
        if response.session is None or response.user is None:
            raise RuntimeError("Supabase did not return a valid saved session.")

        cloud_sync._remember_session(client, response.session, response.user)
        _reset_private_load_state()
        # Supabase rotates refresh tokens. Rerun once so the fresh token is
        # immediately written back to localStorage before normal app rendering.
        st.rerun()
    except Exception:
        st.session_state["_prism_browser_clear_auth"] = True
        st.session_state["_prism_skip_browser_restore_once"] = True
        st.session_state["_prism_restore_notice"] = "Saved login expired. Please sign in again."
        st.rerun()

# After a normal login or a restored session, do not show Private PRism until
# the browser has safely persisted the newest rotating refresh token.
_current_refresh_token = str(st.session_state.get("_prism_cloud_refresh_token", "") or "").strip()
if cloud_sync.signed_in() and _current_refresh_token and _saved_refresh_token != _current_refresh_token:
    st.stop()


# -----------------------------------------------------------------------------
# SIMPLE TWO-STEP CLOUD LOGIN
# -----------------------------------------------------------------------------

# Preserve the true functions because imported modules survive Streamlit reruns.
if not hasattr(cloud_sync, "_prism_original_configured"):
    cloud_sync._prism_original_configured = cloud_sync.configured
if not hasattr(st, "_prism_original_caption"):
    st._prism_original_caption = st.caption

_original_configured = cloud_sync._prism_original_configured
_original_caption = st._prism_original_caption


def _render_private_cloud_login() -> None:
    """Email first, then password. Enter submits only the visible step."""
    if cloud_sync.signed_in() or not _original_configured():
        return

    with st.container(border=True):
        st.markdown("**🔐 Personal PRism · Private Cloud**")

        restore_notice = str(st.session_state.pop("_prism_restore_notice", "") or "")
        if restore_notice:
            st.info(restore_notice)

        stage = str(st.session_state.get("_prism_login_stage", "email"))

        if stage == "email":
            st.caption("Enter your email and press Enter or Continue.")
            with st.form("prism_cloud_email_step", clear_on_submit=False, enter_to_submit=True):
                email = st.text_input(
                    "Email",
                    value=str(st.session_state.get("_prism_login_email", "")),
                    placeholder="your@email.com",
                )
                continue_login = st.form_submit_button(
                    "Continue",
                    type="primary",
                    use_container_width=True,
                )

            if continue_login:
                clean_email = email.strip()
                if not clean_email:
                    st.error("Enter your email first.")
                else:
                    st.session_state["_prism_login_email"] = clean_email
                    st.session_state["_prism_login_stage"] = "password"
                    st.rerun()
            return

        email = str(st.session_state.get("_prism_login_email", "")).strip()
        if not email:
            st.session_state["_prism_login_stage"] = "email"
            st.rerun()

        st.caption(f"Email: {email}")
        st.caption("Enter your password and press Enter to open Private PRism.")

        with st.form("prism_cloud_password_step", clear_on_submit=True, enter_to_submit=True):
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button(
                "Open my private PRism",
                type="primary",
                use_container_width=True,
            )

        if submit_login:
            ok, message = cloud_sync.sign_in(email, password)
            if ok:
                st.session_state.pop("_prism_login_stage", None)
                st.session_state.pop("_prism_login_email", None)
                st.rerun()
            else:
                st.error(message)

        if st.button("← Change email", key="prism_change_login_email"):
            st.session_state.pop("_prism_login_email", None)
            st.session_state["_prism_login_stage"] = "email"
            st.rerun()


_render_private_cloud_login()


def _configured_for_app() -> bool:
    """Hide app.py's older one-form login while this two-step login is shown."""
    if not cloud_sync.signed_in() and _original_configured():
        return False
    return bool(_original_configured())


def _caption_for_app(body, *args, **kwargs):
    """Replace the old cloud-not-configured note with the correct instruction."""
    if (
        body == "Private cloud login will appear here after Supabase is connected. Demo Mode is fully usable now."
        and not cloud_sync.signed_in()
        and _original_configured()
    ):
        body = "Use the Personal PRism login above to open your private cloud data."
    return _original_caption(body, *args, **kwargs)


cloud_sync.configured = _configured_for_app
st.caption = _caption_for_app


# -----------------------------------------------------------------------------
# INDIA DAY ROLLOVER
# -----------------------------------------------------------------------------

_today_marker = date.today().isoformat()
_previous_marker = st.session_state.get("_prism_live_day_calendar_marker")
if _previous_marker != _today_marker:
    st.session_state.pop("live_day", None)
    st.session_state["_prism_live_day_calendar_marker"] = _today_marker


# -----------------------------------------------------------------------------
# MULTI-CSV IMPORT WRAPPER
# -----------------------------------------------------------------------------

class _NamedCSV(BytesIO):
    """BytesIO with the small file attributes Streamlit/Pandas expect."""

    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.type = "text/csv"


def _combine_selected_csvs(files):
    """Turn several supported CSV uploads into one temporary PRism Bundle."""
    frames = []

    for uploaded in files:
        uploaded.seek(0)
        raw = pd.read_csv(uploaded)
        data_type = csv_tools.detect_csv_type(raw)

        if data_type is None:
            raise ValueError(f"{uploaded.name}: PRism could not identify this CSV")

        frame = csv_tools.normalise_dataframe(raw)
        if data_type != "bundle":
            frame = frame.copy()
            frame.insert(0, "record_type", data_type)

        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    return _NamedCSV(
        combined.to_csv(index=False).encode("utf-8"),
        "PRism_Selected_CSVs_Bundle.csv",
    )


if not hasattr(st, "_prism_original_file_uploader"):
    st._prism_original_file_uploader = st.file_uploader

_original_file_uploader = st._prism_original_file_uploader


def _prism_file_uploader(label, *args, **kwargs):
    """Allow multi-select only for PRism's CSV import pickers."""
    key = kwargs.get("key")
    if key not in {"manage_csv", "public_demo_csv"}:
        return _original_file_uploader(label, *args, **kwargs)

    kwargs["accept_multiple_files"] = True
    files = _original_file_uploader(
        "Choose one Bundle CSV or select multiple CSV files",
        *args,
        **kwargs,
    )

    if not files:
        return None
    if len(files) == 1:
        return files[0]

    try:
        merged = _combine_selected_csvs(files)
        st.caption(f"{len(files)} CSV files selected. PRism will import them together in one pass.")
        return merged
    except Exception as exc:
        st.error(f"Could not combine selected CSV files: {exc}")
        return None


st.file_uploader = _prism_file_uploader


# -----------------------------------------------------------------------------
# RUN THE REAL APP ON EVERY STREAMLIT RERUN
# -----------------------------------------------------------------------------

APP_PATH = Path(__file__).with_name("app.py")
try:
    runpy.run_path(str(APP_PATH), run_name="__main__")
finally:
    # Do not leak these wrappers into another Streamlit session.
    cloud_sync.configured = _original_configured
    cloud_sync.sign_out_local = _original_sign_out_local
    st.caption = _original_caption
