"""PRism - fitness tracker + live training companion.

Beginner map:
1. Small helper functions.
2. Top controls: choose a person and choose Explore / Live Workout / Manage.
3. Explore = read-only continuous scroll story.
4. Live Workout = focused gym logging screen.
5. Manage = all edit/import/delete tools kept away from the clean Explore page.

Database code: database.py
CSV code: csv_tools.py
Design + motion: ui.py
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

import pandas as pd
import streamlit as st

import cloud_sync
import csv_tools
import database as db
import demo_data
import ui

# -----------------------------------------------------------------------------
# APP SETTINGS
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="PRism | Train with intent",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Public portfolio mode is launched through streamlit_app.py.
# Signed-out visitors get a disposable Demo sandbox. A signed-in owner gets a
# separate cloud-synced private SQLite working copy backed by Supabase.
# Running `streamlit run app.py` locally keeps the normal persistent prism.db.
PUBLIC_DEMO_MODE = os.getenv("PRISM_PUBLIC_DEMO", "0") == "1"
PUBLIC_SESSION_ROOT: Path | None = None

if PUBLIC_DEMO_MODE:
    session_id = st.session_state.setdefault("_prism_public_session_id", uuid.uuid4().hex)
    PUBLIC_SESSION_ROOT = Path(tempfile.gettempdir()) / "prism_public_sessions" / str(session_id)

    if cloud_sync.signed_in() and cloud_sync.configured():
        cloud_sync.prepare_private_database(PUBLIC_SESSION_ROOT)
    else:
        demo_root = PUBLIC_SESSION_ROOT / "demo"
        db.configure_storage(demo_root / "prism.db", demo_root / "csv_backups")
        db.init_db()

        # Every signed-out visitor receives one isolated fictional sandbox.
        if not st.session_state.get("_prism_public_demo_ready"):
            demo_id = demo_data.open_demo_profile(reset=True)
            st.session_state["_prism_public_demo_person_id"] = int(demo_id)
            st.session_state["active_person_id"] = int(demo_id)
            st.session_state["mode"] = "Explore"
            st.session_state["mode_widget"] = "Explore"
            st.session_state["_prism_public_demo_ready"] = True
else:
    db.init_db()

db.refresh_people_index()

# Keep the public sandbox visibly and structurally separate even if a visitor
# experiments with profile editing or imports a bundle containing another name.
if PUBLIC_DEMO_MODE and not cloud_sync.signed_in():
    public_demo_id = st.session_state.get("_prism_public_demo_person_id")
    if public_demo_id is not None:
        person = db.get_person(int(public_demo_id))
        if person is not None and str(person["display_name"]) != demo_data.DEMO_NAME:
            db.rename_person(int(public_demo_id), demo_data.DEMO_NAME)

ui.apply_theme()

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ACTIVITY = {
    "Mostly sitting": 1.20,
    "Light (1–3 days/week)": 1.375,
    "Moderate (3–5 days/week)": 1.55,
    "Very active (6–7 days/week)": 1.725,
}
GOALS = ["Build muscle", "Build strength", "Maintain", "Lose fat", "Improve fitness"]
DIETS = ["No preference", "Vegetarian", "Vegan", "Eggetarian", "Other"]
EQUIPMENT = ["Full gym", "Dumbbells at home", "Bodyweight only", "Mixed"]

STARTER_PLAN = {
    0: ("Upper A", [("Bench Press", 3, "6-10", 120), ("Lat Pulldown", 3, "8-12", 90), ("Seated Cable Row", 3, "8-12", 90), ("Lateral Raise", 3, "12-15", 60)]),
    1: ("Lower A", [("Squat or Goblet Squat", 3, "6-10", 120), ("Romanian Deadlift", 3, "8-12", 120), ("Leg Press", 3, "10-15", 90), ("Calf Raise", 3, "12-20", 60)]),
    2: ("Recovery", [("Easy walk", 1, "20-30 min", 0), ("Mobility routine", 1, "5-10 min", 0)]),
    3: ("Upper B", [("Incline Dumbbell Press", 3, "8-12", 90), ("Chest-Supported Row", 3, "8-12", 90), ("Shoulder Press", 3, "8-12", 90), ("Biceps Curl", 2, "10-15", 60), ("Triceps Pushdown", 2, "10-15", 60)]),
    4: ("Lower B", [("Deadlift variation", 3, "5-8", 150), ("Split Squat", 3, "8-12 each", 90), ("Hip Thrust", 3, "8-12", 90), ("Leg Curl", 3, "10-15", 60)]),
    5: ("Optional cardio", [("Comfortable cardio", 1, "20-30 min", 0)]),
    6: ("Rest", [("Rest / light mobility", 1, "—", 0)]),
}

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def current_person_id() -> int:
    """Return the active person while keeping Demo Mode outside normal profiles."""
    # Public visitors are locked to their isolated demo sandbox until they sign
    # into the private cloud. Do not create a normal profile in the demo DB.
    if PUBLIC_DEMO_MODE and not cloud_sync.signed_in():
        demo_id = st.session_state.get("_prism_public_demo_person_id")
        if demo_id is not None and db.get_person(int(demo_id)) is not None:
            st.session_state["active_person_id"] = int(demo_id)
            return int(demo_id)

    people = db.get_people()
    visible_people = db.get_visible_people()

    # A real profile must always exist. Demo Mode does not count as one.
    if visible_people.empty:
        new_id = db.create_person("My profile")
        people = db.get_people()
        visible_people = db.get_visible_people()
    else:
        new_id = None

    all_ids = [int(x) for x in people["id"].tolist()]
    visible_ids = [int(x) for x in visible_people["id"].tolist()]
    default_id = int(new_id) if new_id is not None else visible_ids[0]
    active = int(st.session_state.get("active_person_id", default_id))
    if active not in all_ids:
        active = default_id
    st.session_state["active_person_id"] = active
    return active


def is_demo_person(person_id: int) -> bool:
    # Public demo identity is session-scoped, so even if someone edits fields in
    # the sandbox it cannot accidentally become a real/private profile.
    public_demo_id = st.session_state.get("_prism_public_demo_person_id")
    if PUBLIC_DEMO_MODE and not cloud_sync.signed_in() and public_demo_id is not None:
        if int(person_id) == int(public_demo_id):
            return True
    person = db.get_person(int(person_id))
    return person is not None and str(person["display_name"]) == demo_data.DEMO_NAME


def seed_plan_if_empty(person_id: int) -> None:
    if not db.person_table("plans", person_id, order="id").empty:
        return
    with db.connect() as con:
        for weekday, (split, exercises) in STARTER_PLAN.items():
            for exercise, sets, reps, rest in exercises:
                con.execute(
                    """INSERT OR IGNORE INTO plans
                    (person_id,weekday,split,exercise,sets,reps,rest_seconds)
                    VALUES(?,?,?,?,?,?,?)""",
                    (person_id, weekday, split, exercise, sets, reps, rest),
                )
    db.refresh_person_backups(person_id)


def plan_for_day(person_id: int, weekday: int) -> pd.DataFrame:
    return db.query(
        "SELECT * FROM plans WHERE person_id=? AND weekday=? ORDER BY id",
        (person_id, weekday),
    )


def is_rest_plan(plan: pd.DataFrame) -> bool:
    if plan.empty:
        return False
    text = " ".join(plan["split"].astype(str).str.lower().tolist())
    return "rest" in text and "active" not in text


def current_data(person_id: int):
    weights = db.person_table("weights", person_id, order="day ASC,id ASC")
    workouts = db.person_table("workouts", person_id, order="day DESC,id DESC")
    meals = db.person_table("meals", person_id, order="day DESC,id DESC")
    sleeps = db.person_table("sleep", person_id, order="day DESC,id DESC")
    return weights, workouts, meals, sleeps


def workout_progress(person_id: int, target_day: date) -> tuple[int, int, list[str]]:
    plan = plan_for_day(person_id, target_day.weekday())
    if plan.empty or is_rest_plan(plan):
        return 0, 0, []
    logged = db.query(
        "SELECT * FROM workouts WHERE person_id=? AND day=? ORDER BY id",
        (person_id, target_day.isoformat()),
    )
    total_target = int(plan["sets"].fillna(0).sum())
    completed = 0
    remaining = []
    for _, row in plan.iterrows():
        exercise = str(row["exercise"])
        target_sets = int(row["sets"] or 0)
        count = int((logged["exercise"] == exercise).sum()) if not logged.empty else 0
        completed += min(count, target_sets)
        if count < target_sets:
            remaining.append(exercise)
    return completed, total_target, remaining


def today_is_complete(person_id: int) -> bool:
    today_text = date.today().isoformat()
    if db.session_is_complete(person_id, today_text):
        return True
    completed, target, _ = workout_progress(person_id, date.today())
    return target > 0 and completed >= target


def next_training_session(person_id: int) -> tuple[date | None, pd.DataFrame]:
    start_offset = 1 if today_is_complete(person_id) else 0
    for offset in range(start_offset, 8):
        target_date = date.today() + timedelta(days=offset)
        plan = plan_for_day(person_id, target_date.weekday())
        if plan.empty or is_rest_plan(plan):
            continue
        return target_date, plan
    return None, pd.DataFrame()


def table_label(row, kind: str) -> str:
    if kind == "weight":
        return f"{row['day']} {row['log_time']} · {float(row['kg']):.1f} kg"
    if kind == "workout":
        return f"{row['day']} · {row['exercise']} · set {int(row['set_no'])} · {float(row['kg']):g} kg × {int(row['reps'])}"
    if kind == "meal":
        return f"{row['day']} · {row['meal_time']} · {row['food']}"
    if kind == "sleep":
        return f"{row['day']} · {float(row['hours']):.1f} h"
    return str(row["id"])


def navigate_to(mode: str) -> None:
    """Change PRism screen safely.

    Streamlit widgets own their session-state keys after they are created.
    We keep the radio widget key separate from the app's real navigation state
    so buttons can navigate without causing StreamlitWidgetAlreadyInstantiatedError.
    """
    st.session_state["mode"] = mode
    st.session_state["mode_widget"] = mode


def sync_mode_from_widget() -> None:
    """Copy the top navigation choice into PRism's real navigation state."""
    st.session_state["mode"] = st.session_state.get("mode_widget", "Explore")


def open_demo_mode(reset: bool = False) -> None:
    """Open the hidden demo sandbox and remember the user's real profile."""
    current_id = st.session_state.get("active_person_id")
    if current_id is not None and not is_demo_person(int(current_id)):
        st.session_state["demo_return_person_id"] = int(current_id)

    demo_id = demo_data.open_demo_profile(reset=reset)
    st.session_state["active_person_id"] = demo_id
    # Button callbacks run before the next rerun, so these writes are safe.
    st.session_state["mode"] = "Explore"
    st.session_state["mode_widget"] = "Explore"


def exit_demo_mode() -> None:
    """Leave Demo Mode and return to the last real profile in one click."""
    visible = db.get_visible_people()
    if visible.empty:
        return_id = db.create_person("My profile")
    else:
        valid_ids = [int(x) for x in visible["id"].tolist()]
        remembered = st.session_state.get("demo_return_person_id")
        return_id = int(remembered) if remembered in valid_ids else valid_ids[0]

    st.session_state["active_person_id"] = int(return_id)
    st.session_state["mode"] = "Explore"
    st.session_state["mode_widget"] = "Explore"


def reset_public_demo() -> None:
    """Rebuild only this visitor's disposable demo sandbox."""
    if not PUBLIC_DEMO_MODE or cloud_sync.signed_in():
        return
    demo_id = st.session_state.get("_prism_public_demo_person_id")
    if demo_id is not None and db.get_person(int(demo_id)) is not None:
        # Keep the internal demo identity stable even after profile experiments.
        db.rename_person(int(demo_id), demo_data.DEMO_NAME)
        demo_data.open_demo_profile(reset=True)
        st.session_state["active_person_id"] = int(demo_id)
    else:
        demo_id = demo_data.open_demo_profile(reset=True)
        st.session_state["_prism_public_demo_person_id"] = int(demo_id)
        st.session_state["active_person_id"] = int(demo_id)
    st.session_state["mode"] = "Explore"
    st.session_state["mode_widget"] = "Explore"


def render_cloud_access() -> None:
    """Small public-site login surface. Public registration is intentionally absent."""
    if not PUBLIC_DEMO_MODE:
        return

    with st.container(border=True):
        if cloud_sync.signed_in():
            left, right = st.columns([4, 1])
            with left:
                st.markdown("**🔐 Personal PRism · Private Cloud**")
                email = cloud_sync.user_email()
                detail = f"Signed in as {email} · {cloud_sync.sync_status_text()}" if email else cloud_sync.sync_status_text()
                st.caption(detail)
            with right:
                if st.button("Sign out", use_container_width=True, key="cloud_sign_out"):
                    cloud_sync.sign_out_local()
                    st.rerun()

            conflict = st.session_state.get("_prism_cloud_conflict")
            if conflict:
                st.warning(str(conflict))
                a, b = st.columns(2)
                if a.button("Reload newest cloud copy", use_container_width=True):
                    if cloud_sync.reload_from_cloud():
                        st.success("Newest cloud data loaded.")
                        st.rerun()
                if b.button("Keep this device and overwrite cloud", use_container_width=True):
                    if cloud_sync.force_upload_current():
                        st.success("This device is now the cloud copy.")
                        st.rerun()
        else:
            left, right = st.columns([3, 2])
            with left:
                st.markdown("**🔷 Public PRism Demo**")
                st.caption("Everything here is fictional and isolated. Add, delete, import CSVs, and test the product freely.")
            with right:
                if cloud_sync.configured():
                    with st.expander("🔐 Personal cloud login", expanded=False):
                        with st.form("cloud_login_form", clear_on_submit=True):
                            email = st.text_input("Email")
                            password = st.text_input("Password", type="password")
                            submitted = st.form_submit_button("Open my private PRism", type="primary", use_container_width=True)
                        if submitted:
                            ok, message = cloud_sync.sign_in(email, password)
                            if ok:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                else:
                    st.caption("Private cloud login will appear here after Supabase is connected. Demo Mode is fully usable now.")


# -----------------------------------------------------------------------------
# TOP CONTROLS
# -----------------------------------------------------------------------------

render_cloud_access()
active_id = current_person_id()
seed_plan_if_empty(active_id)
demo_active = is_demo_person(active_id)
visible_people = db.get_visible_people()
person_ids = [int(x) for x in visible_people["id"].tolist()]
labels = {int(row.id): str(row.display_name) for row in visible_people.itertuples()}

control_a, control_b = st.columns([1.15, 1.7])
with control_a:
    if demo_active and PUBLIC_DEMO_MODE and not cloud_sync.signed_in():
        st.markdown("**🔷 Public Demo Sandbox**")
        chosen_id = active_id
    elif demo_active:
        st.button(
            "← Exit Demo Mode",
            use_container_width=True,
            on_click=exit_demo_mode,
        )
        chosen_id = active_id
    else:
        chosen_id = st.selectbox(
            "Profile",
            person_ids,
            index=person_ids.index(active_id),
            format_func=lambda x: labels.get(int(x), f"Profile {x}"),
            label_visibility="collapsed",
        )
        if int(chosen_id) != active_id:
            st.session_state["active_person_id"] = int(chosen_id)
            st.rerun()

with control_b:
    if "mode" not in st.session_state:
        st.session_state["mode"] = "Explore"
    if "mode_widget" not in st.session_state:
        st.session_state["mode_widget"] = st.session_state["mode"]

    # Local Demo Mode stays simple/read-only. The public portfolio demo exposes
    # Manage too so visitors can test add/delete/import/export inside their own
    # disposable sandbox.
    demo_read_only = demo_active and not PUBLIC_DEMO_MODE
    mode_options = ["Explore", "Live Workout"] if demo_read_only else ["Explore", "Live Workout", "Manage"]
    if st.session_state["mode"] not in mode_options:
        st.session_state["mode"] = "Explore"
        st.session_state["mode_widget"] = "Explore"

    st.radio(
        "Mode",
        mode_options,
        horizontal=True,
        key="mode_widget",
        on_change=sync_mode_from_widget,
        label_visibility="collapsed",
    )

active_id = int(chosen_id)
active_name = str(db.get_person(active_id)["display_name"])

# -----------------------------------------------------------------------------
# EXPLORE MODE - ONE CONTINUOUS READ-ONLY SCROLL PAGE
# -----------------------------------------------------------------------------

def explore_page(person_id: int) -> None:
    profile = db.profile_for(person_id)
    weights, workouts, meals, sleeps = current_data(person_id)
    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=6)).isoformat()
    recent_w = workouts[workouts["day"] >= cutoff] if not workouts.empty else workouts
    today_meals = meals[meals["day"] == today] if not meals.empty else meals
    # If nothing was logged today, still show the most recent imported/logged meal day.
    if not meals.empty and today_meals.empty:
        latest_meal_day = str(meals["day"].max())
        display_meals = meals[meals["day"] == latest_meal_day].copy()
        meal_period_label = f"Latest meals · {latest_meal_day}"
    else:
        latest_meal_day = today
        display_meals = today_meals.copy()
        meal_period_label = "Meals today"

    ui.hero(str(db.get_person(person_id)["display_name"]))
    ui.scroll_nav()

    # TODAY ------------------------------------------------------------------
    ui.anchor("today")
    ui.section_start("01", "Today, without the clutter.", "The most useful signals first: body weight, training, protein, recovery and what comes next.")
    m1, m2, m3, m4, m5 = st.columns(5)
    latest_weight = "Not recorded" if weights.empty else f"{float(weights.iloc[-1]['kg']):.1f} kg"
    m1.metric("Latest weight", latest_weight)
    m2.metric("Training days · 7d", int(recent_w["day"].nunique()) if not recent_w.empty else 0)
    protein_value = float(display_meals["protein"].sum()) if not display_meals.empty else 0
    protein_label = "Protein today" if not today_meals.empty else "Protein · latest log"
    m3.metric(protein_label, f"{protein_value:.0f} g")
    m4.metric("Latest sleep", "Not recorded" if sleeps.empty else f"{float(sleeps.iloc[0]['hours']):.1f} h")
    m5.metric("Sets · 7d", len(recent_w))

    # If today was marked complete by mistake, let the user reopen it.
    if db.session_is_complete(person_id, date.today().isoformat()):
        if st.button("↶ Reopen today's workout", key="reopen_today_explore", use_container_width=False):
            db.unmark_session_complete(person_id, date.today().isoformat())
            st.success("Today's workout reopened. The next-workout card will use today again.")
            st.rerun()

    next_date, next_plan = next_training_session(person_id)
    st.markdown("#### Next workout")
    if next_date is None or next_plan.empty:
        st.info("No upcoming training day found. Add a plan in Manage mode.")
    else:
        a, b = st.columns([1.15, 2.1])
        with a:
            ui.card(
                f"{next_plan.iloc[0]['split']} · {DAYS[next_date.weekday()]}",
                next_date.strftime("%d %b %Y"),
                "NEXT SESSION",
            )
        with b:
            st.write(" · ".join(next_plan["exercise"].astype(str).tolist()))
            if next_date == date.today():
                completed, target, _ = workout_progress(person_id, date.today())
                if target:
                    st.progress(min(completed / target, 1.0), text=f"Planned sets completed: {completed}/{target}")
    ui.section_end()
    ui.system_flow()

    # TRAINING ---------------------------------------------------------------
    ui.anchor("training")
    ui.section_start("02", "Training should read like a story, not a spreadsheet.", "Your weekly structure, recent work and next movement live together so you can understand where the week is going.")
    ui.statement("Consistency becomes visible when the plan and the history", "move together.")

    plans = db.person_table("plans", person_id, order="weekday ASC,id ASC")
    if plans.empty:
        st.info("No workout plan yet.")
    else:
        # Build real rows of three instead of three long columns. Desktop keeps
        # the same 3-card grid, while Streamlit mobile now stacks Monday -> Sunday
        # naturally instead of stacking whole columns out of weekday order.
        plan_days = []
        for weekday in range(7):
            day_plan = plans[plans["weekday"] == weekday]
            if not day_plan.empty:
                plan_days.append((weekday, day_plan))

        for row_start in range(0, len(plan_days), 3):
            row_cols = st.columns(3)
            for col, (weekday, day_plan) in zip(row_cols, plan_days[row_start:row_start + 3]):
                with col:
                    split = str(day_plan.iloc[0]["split"])
                    exercises = " · ".join(day_plan["exercise"].astype(str).tolist())
                    ui.card(
                        f"{DAYS[weekday]} · {split}",
                        exercises,
                        "REST" if is_rest_plan(day_plan) else "PLAN",
                    )

    st.markdown("#### Recent training")
    if recent_w.empty:
        st.caption("No sets logged in the last seven days.")
    else:
        chart = recent_w.groupby("exercise").size().sort_values(ascending=False)
        st.bar_chart(chart)
        latest_sets = recent_w[["day", "exercise", "set_no", "reps", "kg", "rpe"]].head(12).rename(
            columns={"day": "Date", "exercise": "Exercise", "set_no": "Set", "reps": "Reps", "kg": "Weight (kg)", "rpe": "RPE"}
        )
        st.dataframe(latest_sets, hide_index=True, use_container_width=True)
    ui.section_end()

    # NUTRITION --------------------------------------------------------------
    ui.anchor("nutrition")
    ui.section_start("03", "Fuel is another training signal.", "PRism keeps nutrition simple: what you logged, what your protein range looks like, and what still needs attention today.")
    left, right = st.columns([1, 1.3])
    with left:
        if weights.empty:
            ui.card("Protein guidance", "Record a body-weight measurement first. PRism will not invent one.", "FUEL")
        else:
            weight = float(weights.iloc[-1]["kg"])
            low, high = weight * 1.6, weight * 2.0
            logged = float(display_meals["protein"].sum()) if not display_meals.empty else 0
            ui.card("Estimated protein range", f"{low:.0f}–{high:.0f} g/day · {logged:.0f} g in displayed meals", "GENERAL GUIDANCE")
            st.caption("A general resistance-training estimate, not a medical prescription. Individual needs can differ.")
    with right:
        if display_meals.empty:
            st.caption("No meal records found yet.")
        else:
            st.caption(meal_period_label)
            if today_meals.empty:
                st.caption("Nothing logged today, so PRism is showing your latest available meal data instead.")
            meal_view = display_meals[["log_time", "meal_time", "food", "calories", "protein"]].sort_values("log_time").rename(
                columns={"log_time": "Time", "meal_time": "Meal", "food": "Food", "calories": "Calories", "protein": "Protein (g)"}
            )
            st.dataframe(meal_view, hide_index=True, use_container_width=True)
    ui.section_end()

    # RECOVERY ---------------------------------------------------------------
    ui.anchor("recovery")
    ui.section_start("04", "Recovery is not the space between workouts.", "It is part of the system. Sleep trends sit beside training so you can see when performance and recovery stop agreeing.")
    if sleeps.empty:
        st.info("No sleep data yet.")
    else:
        c1, c2 = st.columns([.7, 1.6])
        with c1:
            ui.card("Latest sleep", f"{float(sleeps.iloc[0]['hours']):.1f} hours · quality {int(sleeps.iloc[0]['quality']) if pd.notna(sleeps.iloc[0]['quality']) else '—'}/5", "RECOVERY")
            ui.card("Average · last 7 logs", f"{float(sleeps.head(7)['hours'].mean()):.1f} hours", "TREND")
        with c2:
            sleep_chart = sleeps.sort_values("day").copy()
            st.line_chart(sleep_chart.set_index("day")["hours"])
    ui.section_end()

    # PROGRESS ---------------------------------------------------------------
    ui.anchor("progress")
    ui.section_start("05", "Progress is easier to trust when you can see the curve.", "Weight trends and personal records stay visible without making you dig through edit screens.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Body-weight trend")
        if weights.empty:
            st.caption("No body-weight measurements yet.")
        elif len(weights) == 1:
            only = weights.iloc[0]
            ui.card("First measurement saved", f"{float(only['kg']):.1f} kg · {only['day']}", "1 OF 2 NEEDED FOR A TREND")
            st.caption("Add one more measurement on another date and PRism will draw the trend line automatically.")
        else:
            trend = weights.copy()
            trend["day"] = pd.to_datetime(trend["day"])
            trend["kg"] = pd.to_numeric(trend["kg"], errors="coerce")
            trend = trend.dropna(subset=["day", "kg"]).sort_values("day")
            st.line_chart(trend.set_index("day")["kg"])
    with right:
        st.markdown("#### Logged personal records")
        if workouts.empty:
            st.caption("No workout sets yet.")
        else:
            prs = workouts.groupby("exercise", as_index=False).agg(
                best_weight=("kg", "max"), best_reps=("reps", "max"), sets_logged=("id", "count")
            ).sort_values("best_weight", ascending=False).head(12)
            prs = prs.rename(columns={"exercise": "Exercise", "best_weight": "Best weight (kg)", "best_reps": "Best reps", "sets_logged": "Sets logged"})
            st.dataframe(prs, hide_index=True, use_container_width=True)
    ui.section_end()
    ui.feature_cards()

    # PEOPLE -----------------------------------------------------------------
    ui.anchor("people")
    ui.section_start("06", "One app. Separate people. No data collisions.", "Switch profiles to compare. Import another person's bundle without replacing your own records.")
    people_now = db.get_visible_people()
    cards = st.columns(min(3, max(len(people_now), 1)))
    for idx, row in enumerate(people_now.itertuples()):
        pid = int(row.id)
        p_weights, p_workouts, p_meals, p_sleeps = current_data(pid)
        p_recent = p_workouts[p_workouts["day"] >= cutoff] if not p_workouts.empty else p_workouts
        latest = "—" if p_weights.empty else f"{float(p_weights.iloc[-1]['kg']):.1f} kg"
        sleep = "—" if p_sleeps.empty else f"{float(p_sleeps.iloc[0]['hours']):.1f} h"
        with cards[idx % len(cards)]:
            ui.card(str(row.display_name), f"Weight {latest} · {int(p_recent['day'].nunique()) if not p_recent.empty else 0} training days/7d · Sleep {sleep}", "PROFILE")

    st.caption("Use Manage mode to add/delete people or import a PRism Bundle CSV. Existing profiles remain separate.")
    ui.section_end()

    ui.footer_cta()
    c1, c2 = st.columns(2)
    c1.button(
        "Open Live Workout",
        type="primary",
        use_container_width=True,
        on_click=navigate_to,
        args=("Live Workout",),
    )
    c2.button(
        "Manage data & profiles",
        use_container_width=True,
        on_click=navigate_to,
        args=("Manage",),
    )


# -----------------------------------------------------------------------------
# LIVE WORKOUT MODE
# -----------------------------------------------------------------------------

def live_workout_page(person_id: int) -> None:
    st.markdown("## Live Workout")
    st.caption("Focused mode for the gym: next movement, previous performance, one-set logging and rest timer.")

    if st.session_state.get("show_rest_timer"):
        ui.rest_timer(int(st.session_state.get("rest_seconds", 90)))
        if st.button("Hide rest timer"):
            st.session_state["show_rest_timer"] = False
            st.rerun()

    workout_day = st.date_input("Workout date", date.today(), key="live_day")
    plan = plan_for_day(person_id, workout_day.weekday())
    logged = db.query("SELECT * FROM workouts WHERE person_id=? AND day=? ORDER BY id", (person_id, workout_day.isoformat()))

    plan_exercises = []
    if plan.empty:
        st.info("No plan for this day. You can still log a custom exercise.")
    elif is_rest_plan(plan):
        st.info(f"{DAYS[workout_day.weekday()]} is a rest day in your plan. You can still log an activity if you choose.")
    else:
        completed, target, remaining = workout_progress(person_id, workout_day)
        st.progress(min(completed / target, 1.0) if target else 0, text=f"Planned sets completed: {completed}/{target}")
        if remaining:
            st.success(f"Next movement: {remaining[0]}")
        else:
            st.success("All planned sets are logged for this day.")
        plan_exercises = plan["exercise"].astype(str).tolist()

    options = plan_exercises + (["Custom exercise"] if "Custom exercise" not in plan_exercises else [])
    if not options:
        options = ["Custom exercise"]

    default_exercise = None
    if plan_exercises:
        _, _, remaining = workout_progress(person_id, workout_day)
        default_exercise = remaining[0] if remaining else plan_exercises[0]

    selected = st.selectbox(
        "Exercise",
        options,
        index=options.index(default_exercise) if default_exercise in options else 0,
    )
    custom_exercise = st.text_input("Custom exercise name", placeholder="e.g. Cable crossover") if selected == "Custom exercise" else ""
    exercise = custom_exercise.strip() if selected == "Custom exercise" else selected

    if exercise:
        previous = db.query(
            """SELECT day,log_time,set_no,reps,kg,rpe FROM workouts
            WHERE person_id=? AND exercise=? AND day<?
            ORDER BY day DESC,id DESC LIMIT 6""",
            (person_id, exercise, workout_day.isoformat()),
        )
        if not previous.empty:
            with st.expander("Previous performance"):
                st.dataframe(previous.rename(columns={"day":"Date","log_time":"Time","set_no":"Set","reps":"Reps","kg":"Weight (kg)","rpe":"RPE"}), hide_index=True, use_container_width=True)

    today_exercise_sets = logged[logged["exercise"] == exercise] if (exercise and not logged.empty) else pd.DataFrame()
    next_set_number = len(today_exercise_sets) + 1
    rest_seconds = 90
    if not plan.empty and exercise in plan_exercises:
        rest_seconds = int(plan[plan["exercise"] == exercise].iloc[0]["rest_seconds"] or 90)

    with st.form("live_set_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        split_default = str(plan.iloc[0]["split"]) if not plan.empty else "Custom session"
        split = c1.text_input("Session / split", value=split_default)
        log_time = c2.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0))
        c3, c4, c5 = st.columns(3)
        set_no = c3.number_input("Set number", 1, 30, min(next_set_number, 30))
        reps = c4.number_input("Reps completed", 0, 200, 10)
        kg = c5.number_input("Weight (kg)", 0.0, 600.0, 0.0, step=2.5, help="Use 0 for bodyweight/no external load.")
        rpe = st.slider("Effort (RPE)", 1, 10, 7)
        note = st.text_input("Notes", placeholder="Technique, machine setting, how it felt")
        if st.form_submit_button("Save set", type="primary"):
            if not exercise:
                st.warning("Choose or enter an exercise first.")
            else:
                db.execute(
                    """INSERT INTO workouts(person_id,day,log_time,split,exercise,set_no,reps,kg,rpe,note)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (person_id, workout_day.isoformat(), log_time.strftime("%H:%M"), split.strip(), exercise, int(set_no), int(reps), float(kg), int(rpe), note.strip()),
                    refresh_person_id=person_id,
                )
                st.session_state["show_rest_timer"] = True
                st.session_state["rest_seconds"] = rest_seconds
                st.rerun()

    logged = db.query("SELECT * FROM workouts WHERE person_id=? AND day=? ORDER BY id", (person_id, workout_day.isoformat()))
    if not logged.empty:
        st.markdown("### Sets logged on this date")
        view = logged[["log_time", "split", "exercise", "set_no", "reps", "kg", "rpe", "note"]].rename(
            columns={"log_time":"Time","split":"Session","exercise":"Exercise","set_no":"Set","reps":"Reps","kg":"Weight (kg)","rpe":"RPE","note":"Notes"}
        )
        st.dataframe(view, hide_index=True, use_container_width=True)

    if workout_day == date.today() and not plan.empty and not is_rest_plan(plan):
        if db.session_is_complete(person_id, workout_day.isoformat()):
            st.success("Today is marked complete.")
            if st.button("↶ Reopen today's workout", key="reopen_today_live", use_container_width=True):
                db.unmark_session_complete(person_id, workout_day.isoformat())
                st.success("Today's workout reopened.")
                st.rerun()
        else:
            if st.button("Finish today's workout", type="primary", use_container_width=True):
                db.mark_session_complete(person_id, workout_day.isoformat(), str(plan.iloc[0]["split"]))
                st.success("Workout marked complete. Explore mode will advance to the next training day.")
                st.rerun()

    st.button(
        "Back to Explore",
        use_container_width=True,
        on_click=navigate_to,
        args=("Explore",),
    )


# -----------------------------------------------------------------------------
# MANAGE MODE - ALL EDIT / IMPORT / DELETE TOOLS
# -----------------------------------------------------------------------------

def profile_editor(person_id: int) -> None:
    profile = db.profile_for(person_id)
    with st.form("profile_form"):
        name = st.text_input("Name / nickname", str(profile["name"] or ""))
        age = st.number_input("Age", 13, 100, int(profile["age"]) if pd.notna(profile["age"]) else 23)
        height = st.number_input("Height (cm)", 100.0, 240.0, float(profile["height_cm"]) if pd.notna(profile["height_cm"]) else 170.0, step=.5)
        gender_options = ["Prefer not to say", "Male", "Female"]
        gender = st.selectbox("Sex used only for calorie estimate", gender_options, index=gender_options.index(profile["gender"]) if profile["gender"] in gender_options else 0)
        goal = st.selectbox("Main goal", GOALS, index=GOALS.index(profile["goal"]) if profile["goal"] in GOALS else 0)
        activity = st.selectbox("Usual activity", list(ACTIVITY), index=list(ACTIVITY).index(profile["activity"]) if profile["activity"] in ACTIVITY else 2)
        days_goal = st.slider("Target training days / week", 1, 7, int(profile["days_goal"] or 4))
        equipment = st.selectbox("Equipment", EQUIPMENT, index=EQUIPMENT.index(profile["equipment"]) if profile["equipment"] in EQUIPMENT else 0)
        diet = st.selectbox("Food preference", DIETS, index=DIETS.index(profile["diet"]) if profile["diet"] in DIETS else 0)
        if st.form_submit_button("Save profile", type="primary"):
            db.save_profile(person_id, {"name":name,"age":int(age),"height_cm":float(height),"gender":gender,"goal":goal,"activity":activity,"days_goal":int(days_goal),"equipment":equipment,"diet":diet})
            st.success("Profile saved.")
            st.rerun()


def plan_editor(person_id: int) -> None:
    selected_day = st.selectbox("Day", list(range(7)), index=date.today().weekday(), format_func=lambda x: DAYS[x])
    plan = plan_for_day(person_id, selected_day)
    if not plan.empty:
        st.dataframe(plan[["exercise","sets","reps","rest_seconds"]].rename(columns={"exercise":"Exercise","sets":"Sets","reps":"Rep target","rest_seconds":"Rest (sec)"}), hide_index=True, use_container_width=True)
    else:
        st.info("No exercises on this day yet.")

    c1, c2 = st.columns(2)
    with c1:
        with st.form("add_plan_form"):
            exercise = st.text_input("Exercise name")
            split_default = str(plan.iloc[0]["split"]) if not plan.empty else "Workout"
            split = st.text_input("Workout / split name", value=split_default)
            sets = st.number_input("Sets", 1, 10, 3)
            reps = st.text_input("Rep target", "8-12")
            rest = st.number_input("Rest seconds", 0, 600, 90)
            if st.form_submit_button("Add exercise", type="primary"):
                if exercise.strip():
                    try:
                        db.execute("INSERT INTO plans(person_id,weekday,split,exercise,sets,reps,rest_seconds) VALUES(?,?,?,?,?,?,?)", (person_id,selected_day,split.strip(),exercise.strip(),int(sets),reps.strip(),int(rest)), refresh_person_id=person_id)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That exercise is already on this day.")
                else:
                    st.warning("Enter an exercise name.")
    with c2:
        if not plan.empty:
            selected_id = st.selectbox("Exercise to remove", plan["id"].tolist(), format_func=lambda x: str(plan[plan["id"] == x].iloc[0]["exercise"]))
            if st.button("Remove selected exercise", use_container_width=True):
                db.delete_row("plans", int(selected_id), person_id)
                st.rerun()


def nutrition_editor(person_id: int) -> None:
    with st.form("meal_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        day = c1.date_input("Date", date.today())
        log_time = c2.time_input("Time eaten", value=datetime.now().time().replace(second=0,microsecond=0))
        meal_time = st.selectbox("Meal", ["Breakfast","Lunch","Dinner","Snack"])
        food = st.text_input("Food and portion")
        c3,c4,c5,c6 = st.columns(4)
        calories = c3.number_input("Calories", 0.0, 5000.0, 0.0, step=25.0)
        protein = c4.number_input("Protein (g)", 0.0, 300.0, 0.0)
        carbs = c5.number_input("Carbs (g)", 0.0, 500.0, 0.0)
        fat = c6.number_input("Fat (g)", 0.0, 300.0, 0.0)
        if st.form_submit_button("Save meal", type="primary"):
            if not food.strip():
                st.warning("Enter the food name first.")
            else:
                db.execute("INSERT INTO meals(person_id,day,log_time,meal_time,food,calories,protein,carbs,fat) VALUES(?,?,?,?,?,?,?,?,?)", (person_id,day.isoformat(),log_time.strftime("%H:%M"),meal_time,food.strip(),float(calories),float(protein),float(carbs),float(fat)), refresh_person_id=person_id)
                st.rerun()

    meals = db.person_table("meals", person_id, order="day DESC,id DESC")
    if not meals.empty:
        st.dataframe(meals[["day","log_time","meal_time","food","calories","protein","carbs","fat"]].head(30), hide_index=True, use_container_width=True)
        with st.expander("Delete one meal"):
            ids = meals.head(50)["id"].tolist()
            selected = st.selectbox("Meal entry", ids, format_func=lambda x: table_label(meals[meals["id"] == x].iloc[0], "meal"))
            if st.button("Delete selected meal"):
                db.delete_row("meals", int(selected), person_id); st.rerun()


def recovery_editor(person_id: int) -> None:
    with st.form("sleep_form", clear_on_submit=True):
        c1,c2 = st.columns(2)
        day = c1.date_input("Morning / wake-up date", date.today())
        log_time = c2.time_input("Time recorded", value=datetime.now().time().replace(second=0,microsecond=0))
        hours = st.number_input("Sleep duration (hours)", 0.0, 24.0, 7.5, step=.25)
        quality = st.slider("How rested did you feel?", 1, 5, 3)
        note = st.text_input("Notes")
        if st.form_submit_button("Save sleep", type="primary"):
            db.execute("INSERT INTO sleep(person_id,day,log_time,hours,quality,note) VALUES(?,?,?,?,?,?)", (person_id,day.isoformat(),log_time.strftime("%H:%M"),float(hours),int(quality),note.strip()), refresh_person_id=person_id)
            st.rerun()
    sleeps = db.person_table("sleep", person_id, order="day DESC,id DESC")
    if not sleeps.empty:
        st.dataframe(sleeps[["day","log_time","hours","quality","note"]].head(30), hide_index=True, use_container_width=True)
        with st.expander("Delete one sleep record"):
            ids = sleeps.head(50)["id"].tolist()
            selected = st.selectbox("Sleep record", ids, format_func=lambda x: table_label(sleeps[sleeps["id"] == x].iloc[0], "sleep"))
            if st.button("Delete selected sleep record"):
                db.delete_row("sleep", int(selected), person_id); st.rerun()


def progress_editor(person_id: int) -> None:
    with st.form("weight_form", clear_on_submit=True):
        c1,c2 = st.columns(2)
        day = c1.date_input("Date", date.today())
        log_time = c2.time_input("Time", value=datetime.now().time().replace(second=0,microsecond=0))
        kg = st.number_input("Weight (kg)", 20.0, 350.0, 60.0, step=.1)
        note = st.text_input("Note")
        if st.form_submit_button("Save measurement", type="primary"):
            db.execute("INSERT INTO weights(person_id,day,log_time,kg,note) VALUES(?,?,?,?,?)", (person_id,day.isoformat(),log_time.strftime("%H:%M"),float(kg),note.strip()), refresh_person_id=person_id)
            st.rerun()

    weights = db.person_table("weights", person_id, order="day DESC,id DESC")
    workouts = db.person_table("workouts", person_id, order="day DESC,id DESC")
    if not weights.empty:
        st.dataframe(weights[["day","log_time","kg","note"]], hide_index=True, use_container_width=True)
        with st.expander("Delete one weight measurement"):
            ids = weights["id"].tolist()
            selected = st.selectbox("Weight entry", ids, format_func=lambda x: table_label(weights[weights["id"] == x].iloc[0], "weight"))
            if st.button("Delete selected weight"):
                db.delete_row("weights", int(selected), person_id); st.rerun()

    if not workouts.empty:
        with st.expander("Delete one workout set"):
            ids = workouts.head(100)["id"].tolist()
            selected = st.selectbox("Workout set", ids, format_func=lambda x: table_label(workouts[workouts["id"] == x].iloc[0], "workout"))
            if st.button("Delete selected workout set"):
                db.delete_row("workouts", int(selected), person_id); st.rerun()

    with st.expander("Delete a whole category"):
        target = st.selectbox("Category", ["Choose...","All workouts","All meals","All sleep records","All weight records"])
        confirm = st.checkbox("I understand this cannot be undone")
        if st.button("Delete selected category", disabled=(not confirm or target=="Choose...")):
            table = {"All workouts":"workouts","All meals":"meals","All sleep records":"sleep","All weight records":"weights"}.get(target)
            if table:
                db.clear_table_for_person(table, person_id); st.rerun()


def people_data_editor(person_id: int) -> None:
    public_sandbox = PUBLIC_DEMO_MODE and not cloud_sync.signed_in() and is_demo_person(person_id)
    if public_sandbox:
        st.markdown("### Public Demo Sandbox")
        st.caption("This is fictional temporary data. Add, delete, import, export, and reset it freely. Nothing here can touch the private cloud account.")
        st.button("↻ Reset fake demo data", use_container_width=True, on_click=reset_public_demo)

        st.markdown("### Import / preview CSV")
        st.caption("Upload a fake/test PRism Bundle or a separate CSV. The sandbox accepts the same CSV formats as the private app.")
        upload = st.file_uploader("Choose CSV", type=["csv"], key="public_demo_csv")
        info = None
        if upload is not None:
            try:
                info = csv_tools.preview_upload(upload)
                if info["type"] is None:
                    st.warning("PRism could not identify this CSV. Nothing has been imported.")
                    st.dataframe(info["raw"].head(25), hide_index=True, use_container_width=True)
                elif info["type"] == "bundle":
                    types = [k for k,v in info["clean"].items() if isinstance(v,pd.DataFrame) and not v.empty]
                    st.success(f"PRism Bundle detected: {', '.join(types)}")
                    st.dataframe(info["raw"].head(25), hide_index=True, use_container_width=True)
                else:
                    st.success(f"Detected automatically: {info['type'].title()} data")
                    st.dataframe(info["clean"].head(25), hide_index=True, use_container_width=True)
            except Exception as exc:
                st.error(f"Could not read CSV: {exc}")

        if info is not None and info.get("type") is not None:
            mode_label = st.selectbox(
                "Import behavior",
                ["Add safely (recommended)", "Replace matching demo data type(s)"],
                key="public_demo_import_mode",
            )
            import_mode = "append" if mode_label.startswith("Add safely") else "replace"
            if st.button("Import into demo sandbox", type="primary", use_container_width=True):
                try:
                    if info["type"] == "bundle":
                        result = csv_tools.import_bundle(person_id, info["clean"], mode=import_mode)
                    else:
                        result = csv_tools.import_dataframe(person_id, info["type"], info["clean"], mode=import_mode)
                    # A profile row may contain another display name. Keep the
                    # sandbox identity fixed while retaining the other fake fields.
                    db.rename_person(person_id, demo_data.DEMO_NAME)
                    st.success(f"Demo import complete: {result['added']} row(s) added, {result['skipped']} skipped.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Demo import could not finish: {exc}")

        st.markdown("### Fake demo CSV & templates")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "Download fake Demo CSV",
                data=csv_tools.export_person_bundle_csv(person_id),
                file_name="PRism_Demo_Bundle.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "Download demo CSV ZIP",
                data=csv_tools.export_person_zip(person_id),
                file_name="PRism_Demo_Data.zip",
                mime="application/zip",
                use_container_width=True,
            )
        with c3:
            st.download_button(
                "Download CSV templates",
                data=csv_tools.template_zip(),
                file_name="PRism_CSV_templates.zip",
                mime="application/zip",
                use_container_width=True,
            )
        st.info("Public demo changes are temporary and isolated to this visitor session. Reset Demo restores the original fictional data.")
        return

    st.markdown("### Demo Mode")
    st.caption("Try the full product with fictional sample data. Demo Mode is a separate profile and never changes your real records.")
    demo_a, demo_b = st.columns(2)
    with demo_a:
        st.button(
            "▶ Open Demo Mode",
            type="primary",
            use_container_width=True,
            on_click=open_demo_mode,
            kwargs={"reset": False},
        )
    with demo_b:
        st.button(
            "↻ Reset Demo Data",
            use_container_width=True,
            on_click=open_demo_mode,
            kwargs={"reset": True},
        )

    st.markdown("### People index")
    people_now = db.get_visible_people()
    st.dataframe(people_now.rename(columns={"display_name":"Profile","created_at":"Created"})[["Profile","Created"]], hide_index=True, use_container_width=True)

    with st.expander("Add another person", expanded=False):
        new_name = st.text_input("New profile name", placeholder="e.g. Aman")
        if st.button("Create separate profile"):
            if not new_name.strip():
                st.warning("Enter a name first.")
            else:
                new_id = db.create_person(new_name.strip()); seed_plan_if_empty(new_id)
                st.session_state["active_person_id"] = new_id
                st.success("Separate profile created."); st.rerun()

    st.markdown("### Import / preview CSV")
    st.caption("Easiest option: one PRism Bundle CSV can contain profile + weights + workouts + meals + sleep + plan. Normal separate CSVs still work too.")
    upload = st.file_uploader("Choose CSV", type=["csv"], key="manage_csv")
    info = None
    if upload is not None:
        try:
            info = csv_tools.preview_upload(upload)
            if info["type"] is None:
                st.warning("PRism could not identify this CSV. Nothing has been imported.")
                st.dataframe(info["raw"].head(25), hide_index=True, use_container_width=True)
            elif info["type"] == "bundle":
                bundle_name = csv_tools.bundle_profile_name(info["clean"])
                types = [k for k,v in info["clean"].items() if isinstance(v,pd.DataFrame) and not v.empty]
                st.success(f"PRism Bundle detected: {', '.join(types)}")
                if bundle_name:
                    st.info(f"Profile name inside bundle: {bundle_name}")
                st.dataframe(info["raw"].head(25), hide_index=True, use_container_width=True)
            else:
                st.success(f"Detected automatically: {info['type'].title()} data")
                st.dataframe(info["clean"].head(25), hide_index=True, use_container_width=True)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")

    if info is not None and info.get("type") is not None:
        people_now = db.get_visible_people()
        ids = [int(x) for x in people_now["id"].tolist()]
        destination = st.radio("Import destination", ["Current profile","Existing profile","Create separate profile from CSV"], horizontal=True)
        target_id = person_id
        if destination == "Existing profile":
            target_id = st.selectbox("Choose profile", ids, format_func=lambda x: str(db.get_person(int(x))["display_name"]))
        elif destination == "Create separate profile from CSV":
            suggested = csv_tools.bundle_profile_name(info["clean"]) if info["type"] == "bundle" else ""
            new_name = st.text_input("New profile name", value=suggested, placeholder="e.g. Rahul")

        mode_label = st.selectbox("Import behavior", ["Add safely (recommended)","Replace this person's matching data type(s)"])
        import_mode = "append" if mode_label.startswith("Add safely") else "replace"

        if st.button("Import CSV", type="primary", use_container_width=True):
            created_new_profile = False
            try:
                if destination == "Create separate profile from CSV":
                    if not new_name.strip():
                        st.warning("Enter the new person's name first.")
                        st.stop()
                    target_id = db.create_person(new_name.strip())
                    created_new_profile = True

                if info["type"] == "bundle":
                    result = csv_tools.import_bundle(int(target_id), info["clean"], mode=import_mode)
                else:
                    result = csv_tools.import_dataframe(int(target_id), info["type"], info["clean"], mode=import_mode)

                if created_new_profile:
                    seed_plan_if_empty(int(target_id))
                    st.session_state["active_person_id"] = int(target_id)

                st.success(f"Import complete: {result['added']} row(s) added, {result['skipped']} skipped.")
                st.rerun()
            except Exception as exc:
                # Keep the public UI friendly. The user should see a useful
                # message instead of a full Python traceback.
                st.error(f"Import could not finish: {exc}")

    st.markdown("### Export & templates")
    person = db.get_person(person_id)
    safe_name = str(person["display_name"]).strip().replace(" ", "_") or f"profile_{person_id}"
    c1,c2,c3 = st.columns(3)
    with c1:
        st.download_button("Download one Bundle CSV", data=csv_tools.export_person_bundle_csv(person_id), file_name=f"PRism_{safe_name}_bundle.csv", mime="text/csv", use_container_width=True)
    with c2:
        st.download_button("Download complete CSV ZIP", data=csv_tools.export_person_zip(person_id), file_name=f"PRism_{safe_name}_data.zip", mime="application/zip", use_container_width=True)
    with c3:
        st.download_button("Download CSV templates", data=csv_tools.template_zip(), file_name="PRism_CSV_templates.zip", mime="application/zip", use_container_width=True)

    st.markdown("### Delete profile")
    people_now = db.get_visible_people()
    if len(people_now) <= 1:
        st.info("PRism must keep at least one profile.")
    else:
        delete_ids = [int(x) for x in people_now["id"].tolist()]
        delete_id = st.selectbox("Profile to delete", delete_ids, index=delete_ids.index(person_id), format_func=lambda x: str(db.get_person(int(x))["display_name"]))
        delete_name = str(db.get_person(int(delete_id))["display_name"])
        typed = st.text_input(f'Type "{delete_name}" to confirm deletion')
        if st.button(f"Delete {delete_name}", disabled=typed.strip()!=delete_name):
            was_active = int(delete_id) == person_id
            db.delete_person(int(delete_id))
            if was_active:
                st.session_state["active_person_id"] = int(db.get_visible_people().iloc[0]["id"])
            st.rerun()


def manage_page(person_id: int) -> None:
    ui.manage_banner(str(db.get_person(person_id)["display_name"]))
    tabs = st.tabs(["Profile", "Workout plan", "Nutrition", "Recovery", "Progress & delete", "People & CSV"])
    with tabs[0]: profile_editor(person_id)
    with tabs[1]: plan_editor(person_id)
    with tabs[2]: nutrition_editor(person_id)
    with tabs[3]: recovery_editor(person_id)
    with tabs[4]: progress_editor(person_id)
    with tabs[5]: people_data_editor(person_id)


# -----------------------------------------------------------------------------
# RUN SELECTED MODE
# -----------------------------------------------------------------------------

mode = st.session_state.get("mode", "Explore")
if mode == "Explore":
    explore_page(active_id)
elif mode == "Live Workout":
    live_workout_page(active_id)
else:
    manage_page(active_id)

# Save private cloud changes after a normal completed Streamlit run. If an
# action called st.rerun() earlier, prepare_private_database() saves that change
# at the beginning of the next run before it checks for changes from another device.
if PUBLIC_DEMO_MODE and cloud_sync.signed_in():
    try:
        cloud_sync.sync_if_needed()
    except Exception as exc:
        st.warning(f"Cloud sync could not finish: {exc}")

st.divider()
if PUBLIC_DEMO_MODE:
    st.caption(
        "Public portfolio demo · Each visitor uses a private temporary session database. "
        "Demo data may reset when the session or app restarts. PRism is a fitness tracking and education project, not medical care."
    )
else:
    st.caption(
        "PRism is a fitness tracking and education project. It does not diagnose medical conditions or replace a qualified trainer, dietitian or healthcare professional. "
        "Local SQLite and CSV backups are stored only on this computer unless you export or share them."
    )

