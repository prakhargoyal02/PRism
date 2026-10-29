"""Private cloud sync for PRism.

PRism keeps its existing SQLite model because it is simple, portable and works
well offline/local. For the live app, an authenticated user's complete SQLite
state is compressed and stored in ONE RLS-protected Supabase row.

Why this design works for PRism:
- the public demo never touches Supabase;
- the owner's phone and desktop load the same private state;
- CSV import/export keeps working without rewriting the app;
- GitHub never contains personal data or credentials.

The cloud row is protected by Supabase Auth + Row Level Security. The app uses
only the publishable/anon key. Never put a service-role/secret key in Streamlit.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import os
from pathlib import Path
import sqlite3
from typing import Any

import streamlit as st

import database as db

STATE_TABLE = "prism_state"


def _secret(name: str, *aliases: str) -> str:
    """Read a Streamlit secret or environment variable without crashing locally."""
    names = (name, *aliases)
    for key in names:
        value = os.getenv(key)
        if value:
            return str(value).strip()
    try:
        for key in names:
            if key in st.secrets and st.secrets[key]:
                return str(st.secrets[key]).strip()
    except Exception:
        pass
    return ""


def configured() -> bool:
    return bool(
        _secret("SUPABASE_URL")
        and _secret("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_KEY")
    )


def _new_client():
    if not configured():
        raise RuntimeError("Supabase is not configured yet.")
    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - only happens before requirements install
        raise RuntimeError("Install the 'supabase' package from requirements.txt first.") from exc

    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_KEY")
    return create_client(url, key)


def signed_in() -> bool:
    return bool(st.session_state.get("_prism_cloud_user_id"))


def user_email() -> str:
    return str(st.session_state.get("_prism_cloud_email", ""))


def user_id() -> str:
    return str(st.session_state.get("_prism_cloud_user_id", ""))


def _remember_session(client: Any, session: Any, user: Any) -> None:
    st.session_state["_prism_supabase_client"] = client
    st.session_state["_prism_cloud_user_id"] = str(user.id)
    st.session_state["_prism_cloud_email"] = str(getattr(user, "email", "") or "")
    st.session_state["_prism_cloud_access_token"] = str(session.access_token)
    st.session_state["_prism_cloud_refresh_token"] = str(session.refresh_token)


def sign_in(email: str, password: str) -> tuple[bool, str]:
    """Sign in an existing Supabase Auth user. PRism does not expose public sign-up."""
    if not configured():
        return False, "Cloud login is not configured on this deployment yet."
    if not email.strip() or not password:
        return False, "Enter your email and password."

    try:
        client = _new_client()
        response = client.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        if response.session is None or response.user is None:
            return False, "Supabase did not return a valid session."
        _remember_session(client, response.session, response.user)

        # A new login must load the private cloud database, never reuse demo state.
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
        return True, "Private cloud connected."
    except Exception as exc:
        text = str(exc).strip() or exc.__class__.__name__
        return False, f"Could not sign in: {text}"


def current_client():
    """Return the authenticated client, rebuilding its in-memory session if needed."""
    client = st.session_state.get("_prism_supabase_client")
    if client is not None:
        return client

    access = str(st.session_state.get("_prism_cloud_access_token", ""))
    refresh = str(st.session_state.get("_prism_cloud_refresh_token", ""))
    if not access or not refresh:
        raise RuntimeError("Cloud session is not available. Please sign in again.")

    client = _new_client()
    response = client.auth.set_session(access, refresh)
    if response.session is not None:
        st.session_state["_prism_cloud_access_token"] = str(response.session.access_token)
        st.session_state["_prism_cloud_refresh_token"] = str(response.session.refresh_token)
    st.session_state["_prism_supabase_client"] = client
    return client


def sign_out_local() -> None:
    """Forget this browser's PRism login without signing out the user's other devices."""
    for key in list(st.session_state.keys()):
        if key.startswith("_prism_cloud_") or key == "_prism_supabase_client":
            st.session_state.pop(key, None)
    st.session_state.pop("active_person_id", None)
    st.session_state.pop("demo_return_person_id", None)
    st.session_state["_prism_public_demo_ready"] = False
    st.session_state["mode"] = "Explore"
    st.session_state["mode_widget"] = "Explore"


def _db_hash(path: Path | None = None) -> str:
    path = path or db.current_db_path()
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encode_database(path: Path | None = None) -> str:
    """Create a compressed, portable SQLite SQL dump."""
    path = path or db.current_db_path()
    if not path.exists():
        return ""
    con = sqlite3.connect(path)
    try:
        dump = "\n".join(con.iterdump()).encode("utf-8")
    finally:
        con.close()
    compressed = gzip.compress(dump, compresslevel=9)
    return base64.b64encode(compressed).decode("ascii")


def _decode_database(blob: str, destination: Path | None = None) -> None:
    """Restore a cloud state into a new SQLite file, then atomically replace it."""
    destination = destination or db.current_db_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = gzip.decompress(base64.b64decode(blob.encode("ascii"))).decode("utf-8")
    temp_path = destination.with_name(destination.name + ".restore")
    if temp_path.exists():
        temp_path.unlink()
    con = sqlite3.connect(temp_path)
    try:
        con.executescript(raw)
        con.commit()
    finally:
        con.close()
    temp_path.replace(destination)


def _fetch_remote() -> dict | None:
    response = (
        current_client()
        .table(STATE_TABLE)
        .select("state_blob,revision,updated_at")
        .eq("user_id", user_id())
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _insert_initial_state() -> int:
    payload = {
        "user_id": user_id(),
        "state_blob": _encode_database(),
        "revision": 1,
    }
    response = current_client().table(STATE_TABLE).insert(payload).execute()
    if not response.data:
        raise RuntimeError("Could not create the private PRism cloud state.")
    return int(response.data[0].get("revision", 1))


def _push_state(expected_revision: int | None = None, force: bool = False) -> tuple[bool, int | None]:
    """Upload the current SQLite state. Revision checking prevents silent overwrites."""
    client = current_client()
    remote = _fetch_remote()
    if remote is None:
        revision = _insert_initial_state()
        st.session_state["_prism_cloud_revision"] = revision
        st.session_state["_prism_cloud_last_hash"] = _db_hash()
        return True, revision

    remote_revision = int(remote.get("revision", 0) or 0)
    if expected_revision is None:
        expected_revision = int(st.session_state.get("_prism_cloud_revision", remote_revision))

    if not force and remote_revision != int(expected_revision):
        st.session_state["_prism_cloud_conflict"] = (
            "Cloud data changed on another device before this device finished saving. "
            "Reload the newest cloud copy before continuing."
        )
        return False, remote_revision

    next_revision = remote_revision + 1
    query = (
        client.table(STATE_TABLE)
        .update({"state_blob": _encode_database(), "revision": next_revision})
        .eq("user_id", user_id())
    )
    if not force:
        query = query.eq("revision", remote_revision)
    response = query.execute()
    if not response.data:
        st.session_state["_prism_cloud_conflict"] = (
            "Cloud data changed while PRism was saving. Reload the newest cloud copy."
        )
        return False, remote_revision

    st.session_state["_prism_cloud_revision"] = next_revision
    st.session_state["_prism_cloud_last_hash"] = _db_hash()
    st.session_state.pop("_prism_cloud_conflict", None)
    return True, next_revision


def _pull_state(remote: dict | None = None) -> bool:
    remote = remote or _fetch_remote()
    if remote is None:
        return False
    blob = str(remote.get("state_blob", "") or "")
    if not blob:
        return False
    _decode_database(blob)
    st.session_state["_prism_cloud_revision"] = int(remote.get("revision", 0) or 0)
    st.session_state["_prism_cloud_last_hash"] = _db_hash()
    st.session_state.pop("_prism_cloud_conflict", None)
    return True


def prepare_private_database(session_root: Path) -> None:
    """Select and synchronize the signed-in user's private working database."""
    uid = user_id()
    if not uid:
        raise RuntimeError("No private PRism user is signed in.")

    safe_uid = "".join(ch for ch in uid if ch.isalnum() or ch in "-_")
    root = session_root / "private" / safe_uid
    db.configure_storage(root / "prism.db", root / "csv_backups")

    if not st.session_state.get("_prism_cloud_loaded"):
        remote = _fetch_remote()
        if remote and remote.get("state_blob"):
            _pull_state(remote)
        else:
            # Never seed a new private account from the public demo database.
            path = db.current_db_path()
            if path.exists():
                path.unlink()
            db.init_db()
            _insert_initial_state()
        st.session_state["_prism_cloud_loaded"] = True
        st.session_state["_prism_cloud_last_hash"] = _db_hash()
        return

    # If the previous Streamlit run changed SQLite and reran before reaching the
    # bottom of app.py, save that local change FIRST.
    current_hash = _db_hash()
    last_hash = str(st.session_state.get("_prism_cloud_last_hash", ""))
    if current_hash and last_hash and current_hash != last_hash:
        ok, _ = _push_state()
        if not ok:
            return

    # Pull changes made from another device when this device is clean.
    remote = _fetch_remote()
    if remote is not None:
        remote_revision = int(remote.get("revision", 0) or 0)
        local_revision = int(st.session_state.get("_prism_cloud_revision", 0) or 0)
        if remote_revision > local_revision:
            _pull_state(remote)


def sync_if_needed() -> bool:
    """Push local changes after the current Streamlit run."""
    if not signed_in() or not st.session_state.get("_prism_cloud_loaded"):
        return False
    if st.session_state.get("_prism_cloud_conflict"):
        return False
    current_hash = _db_hash()
    last_hash = str(st.session_state.get("_prism_cloud_last_hash", ""))
    if current_hash and current_hash != last_hash:
        ok, _ = _push_state()
        return ok
    return False


def reload_from_cloud() -> bool:
    """Discard this session's unsynced copy and load the newest cloud revision."""
    remote = _fetch_remote()
    if remote is None:
        return False
    ok = _pull_state(remote)
    if ok:
        st.session_state.pop("active_person_id", None)
    return ok


def force_upload_current() -> bool:
    """Explicit conflict override. Only exposed after a sync conflict."""
    ok, _ = _push_state(force=True)
    return ok


def sync_status_text() -> str:
    if not signed_in():
        return "Demo sandbox"
    if st.session_state.get("_prism_cloud_conflict"):
        return "Sync needs attention"
    revision = st.session_state.get("_prism_cloud_revision")
    return f"Private cloud synced · revision {revision}" if revision else "Private cloud connected"
