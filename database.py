"""PRism database helpers.

This file has one job: talk to SQLite.
Keeping database code here makes app.py easier for a beginner to read.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
import re
import shutil
import sqlite3

import pandas as pd

APP_DIR = Path(__file__).parent
DEFAULT_DB_PATH = APP_DIR / "prism.db"
DEFAULT_BACKUP_DIR = APP_DIR / "csv_backups"
HIDDEN_DEMO_NAME = "PRism Demo"

# Context variables keep storage paths isolated between concurrent Streamlit
# script sessions. A normal module global could be overwritten by another
# visitor while both sessions are active on the same server process.
_DB_PATH_CONTEXT: ContextVar[Path] = ContextVar("prism_db_path", default=DEFAULT_DB_PATH)
_BACKUP_DIR_CONTEXT: ContextVar[Path] = ContextVar("prism_backup_dir", default=DEFAULT_BACKUP_DIR)


def configure_storage(db_path: str | Path | None = None, backup_dir: str | Path | None = None) -> None:
    """Configure storage for the current execution context."""
    if db_path is not None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _DB_PATH_CONTEXT.set(path)
    if backup_dir is not None:
        path = Path(backup_dir)
        path.mkdir(parents=True, exist_ok=True)
        _BACKUP_DIR_CONTEXT.set(path)


def current_db_path() -> Path:
    return _DB_PATH_CONTEXT.get()


def current_backup_dir() -> Path:
    return _BACKUP_DIR_CONTEXT.get()

DATA_TABLES = ("weights", "workouts", "meals", "sleep", "plans")

TABLE_COLUMNS = {
    "weights": ["day", "log_time", "kg", "note"],
    "workouts": ["day", "log_time", "split", "exercise", "set_no", "reps", "kg", "rpe", "note"],
    "meals": ["day", "log_time", "meal_time", "food", "calories", "protein", "carbs", "fat"],
    "sleep": ["day", "log_time", "hours", "quality", "note"],
    "plans": ["weekday", "split", "exercise", "sets", "reps", "rest_seconds"],
}

PROFILE_COLUMNS = ["name", "age", "height_cm", "gender", "goal", "activity", "days_goal", "equipment", "diet"]


def connect() -> sqlite3.Connection:
    """Open the local PRism database."""
    con = sqlite3.connect(current_db_path(), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def table_has_column(con: sqlite3.Connection, table: str, column: str) -> bool:
    columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    return column in columns


def table_sql(con: sqlite3.Connection, table: str) -> str:
    row = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row[0] if row and row[0] else ""


def _create_people_and_profile(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Older PRism used CHECK(id=1), which only allowed one profile.
    # Rebuild that table once so PRism can safely keep many people separate.
    old_profile_sql = table_sql(con, "profile")
    if old_profile_sql and "CHECK(id=1)" in old_profile_sql.replace(" ", ""):
        con.execute("ALTER TABLE profile RENAME TO profile_old_single")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY,
            name TEXT DEFAULT '',
            age INTEGER,
            height_cm REAL,
            gender TEXT DEFAULT 'Prefer not to say',
            goal TEXT DEFAULT 'Build muscle',
            activity TEXT DEFAULT 'Moderate (3–5 days/week)',
            days_goal INTEGER DEFAULT 4,
            equipment TEXT DEFAULT 'Full gym',
            diet TEXT DEFAULT 'No preference'
        )
        """
    )

    # Move the old single profile into person 1.
    if table_sql(con, "profile_old_single"):
        old = con.execute("SELECT * FROM profile_old_single LIMIT 1").fetchone()
        if old:
            old_keys = set(old.keys())
            name = old["name"] if "name" in old_keys else ""
            age = old["age"] if "age" in old_keys else None
            height = old["height_cm"] if "height_cm" in old_keys else None
            gender = old["gender"] if "gender" in old_keys else "Prefer not to say"
            goal = old["goal"] if "goal" in old_keys else "Build muscle"
            activity = old["activity"] if "activity" in old_keys else "Moderate (3–5 days/week)"
            days_goal = old["days_goal"] if "days_goal" in old_keys else 4
            equipment = old["equipment"] if "equipment" in old_keys else "Full gym"
            con.execute(
                """
                INSERT OR REPLACE INTO profile
                (id,name,age,height_cm,gender,goal,activity,days_goal,equipment,diet)
                VALUES(1,?,?,?,?,?,?,?,?,?)
                """,
                (name, age, height, gender, goal, activity, days_goal, equipment, "No preference"),
            )
        con.execute("DROP TABLE profile_old_single")

    # Add diet if the user already has the newer profile table but not this field.
    if not table_has_column(con, "profile", "diet"):
        con.execute("ALTER TABLE profile ADD COLUMN diet TEXT DEFAULT 'No preference'")

    # Person 1 represents existing data from older PRism versions.
    if con.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 0:
        existing = con.execute("SELECT name FROM profile WHERE id=1").fetchone()
        display_name = (existing[0] if existing and existing[0] else "My profile")
        con.execute(
            "INSERT INTO people(id,display_name,created_at) VALUES(1,?,?)",
            (display_name, datetime.now().isoformat(timespec="seconds")),
        )

    if con.execute("SELECT COUNT(*) FROM profile WHERE id=1").fetchone()[0] == 0:
        con.execute("INSERT INTO profile(id,name) VALUES(1,'')")


def _create_or_migrate_data_tables(con: sqlite3.Connection) -> None:
    # Regular tables can be upgraded by adding person_id.
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            day TEXT NOT NULL,
            log_time TEXT NOT NULL DEFAULT '00:00',
            kg REAL NOT NULL,
            note TEXT DEFAULT ''
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            day TEXT NOT NULL,
            log_time TEXT NOT NULL DEFAULT '00:00',
            split TEXT DEFAULT '',
            exercise TEXT NOT NULL,
            set_no INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            kg REAL NOT NULL,
            rpe REAL,
            note TEXT DEFAULT ''
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            day TEXT NOT NULL,
            log_time TEXT NOT NULL DEFAULT '00:00',
            meal_time TEXT DEFAULT '',
            food TEXT NOT NULL,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            fat REAL DEFAULT 0
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS sleep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            day TEXT NOT NULL,
            log_time TEXT NOT NULL DEFAULT '00:00',
            hours REAL NOT NULL,
            quality INTEGER,
            note TEXT DEFAULT ''
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            day TEXT NOT NULL,
            split TEXT DEFAULT '',
            completed_at TEXT NOT NULL,
            UNIQUE(person_id, day)
        )
        """
    )

    for table in ("weights", "workouts", "meals", "sleep"):
        if not table_has_column(con, table, "person_id"):
            con.execute(f"ALTER TABLE {table} ADD COLUMN person_id INTEGER NOT NULL DEFAULT 1")
        if not table_has_column(con, table, "log_time"):
            con.execute(f"ALTER TABLE {table} ADD COLUMN log_time TEXT NOT NULL DEFAULT '00:00'")

    # Old plans used UNIQUE(weekday, exercise), so two people could not have
    # the same exercise on the same day. Rebuild it with person_id included.
    plans_sql = table_sql(con, "plans")
    needs_rebuild = bool(plans_sql) and "person_id" not in plans_sql.lower()
    if needs_rebuild:
        con.execute("ALTER TABLE plans RENAME TO plans_old_single")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL DEFAULT 1,
            weekday INTEGER NOT NULL,
            split TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER DEFAULT 3,
            reps TEXT DEFAULT '8-12',
            rest_seconds INTEGER DEFAULT 90,
            UNIQUE(person_id, weekday, exercise)
        )
        """
    )

    if table_sql(con, "plans_old_single"):
        old_rows = con.execute(
            "SELECT weekday,split,exercise,sets,reps,rest_seconds FROM plans_old_single"
        ).fetchall()
        con.executemany(
            """
            INSERT OR IGNORE INTO plans
            (person_id,weekday,split,exercise,sets,reps,rest_seconds)
            VALUES(1,?,?,?,?,?,?)
            """,
            [tuple(r) for r in old_rows],
        )
        con.execute("DROP TABLE plans_old_single")


def init_db() -> None:
    """Create tables and upgrade databases from older PRism versions."""
    with connect() as con:
        _create_people_and_profile(con)
        _create_or_migrate_data_tables(con)


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run SELECT and return a pandas DataFrame."""
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)


def execute(sql: str, params: tuple = (), refresh_person_id: int | None = None) -> None:
    """Run one database change, then refresh CSV backups for that person."""
    with connect() as con:
        con.execute(sql, params)
    if refresh_person_id is not None:
        refresh_person_backups(refresh_person_id)


def safe_folder_name(text: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "-", text.strip()).strip("-").lower()
    return clean or "profile"


def person_folder(person_id: int) -> Path:
    person = get_person(person_id)
    name = person["display_name"] if person is not None else f"person-{person_id}"
    return current_backup_dir() / f"{person_id:03d}_{safe_folder_name(str(name))}"


def refresh_people_index() -> None:
    """Write only real user profiles to the public people index.

    PRism Demo is an internal sandbox, so it must never appear beside real
    profiles in the index CSV.
    """
    backup_dir = current_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Remove any demo backup folder left by an older build.
    for old_demo_folder in backup_dir.glob("*_prism-demo"):
        if old_demo_folder.is_dir():
            shutil.rmtree(old_demo_folder, ignore_errors=True)
    people = get_visible_people()
    if people.empty:
        pd.DataFrame(columns=["id", "display_name", "created_at"]).to_csv(backup_dir / "people_index.csv", index=False)
    else:
        people.to_csv(backup_dir / "people_index.csv", index=False)


def refresh_person_backups(person_id: int) -> None:
    """Create fresh CSV snapshots for only one real person.

    PRism Demo is intentionally excluded because it is a disposable sandbox,
    not one of the user's profiles or backups.
    """
    person = get_person(person_id)
    if person is not None and str(person["display_name"]) == HIDDEN_DEMO_NAME:
        folder = current_backup_dir() / f"{person_id:03d}_{safe_folder_name(HIDDEN_DEMO_NAME)}"
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        refresh_people_index()
        return

    folder = person_folder(person_id)
    folder.mkdir(parents=True, exist_ok=True)

    profile = query("SELECT * FROM profile WHERE id=?", (person_id,))
    if profile.empty:
        pd.DataFrame(columns=PROFILE_COLUMNS).to_csv(folder / "prism_profile.csv", index=False)
    else:
        profile[PROFILE_COLUMNS].to_csv(folder / "prism_profile.csv", index=False)

    table_frames = {}
    for table, cols in TABLE_COLUMNS.items():
        df = query(f"SELECT * FROM {table} WHERE person_id=? ORDER BY id", (person_id,))
        export_df = df[cols] if not df.empty else pd.DataFrame(columns=cols)
        table_frames[table] = export_df
        export_df.to_csv(folder / f"prism_{table}.csv", index=False)

    # One portable file containing every data type. record_type tells PRism
    # what each row means when it is imported later.
    bundle_columns = [
        "record_type", *PROFILE_COLUMNS,
        "day", "log_time", "kg", "note",
        "split", "exercise", "set_no", "reps", "rpe",
        "meal_time", "food", "calories", "protein", "carbs", "fat",
        "hours", "quality", "weekday", "sets", "rest_seconds",
    ]
    bundle_columns = list(dict.fromkeys(bundle_columns))
    rows = []

    if not profile.empty:
        row = {c: "" for c in bundle_columns}
        row["record_type"] = "profile"
        for col in PROFILE_COLUMNS:
            row[col] = profile.iloc[0][col]
        rows.append(row)

    for table in ("weights", "workouts", "meals", "sleep", "plans"):
        for _, source in table_frames[table].iterrows():
            row = {c: "" for c in bundle_columns}
            row["record_type"] = table
            for col in TABLE_COLUMNS[table]:
                row[col] = source[col]
            rows.append(row)

    pd.DataFrame(rows, columns=bundle_columns).to_csv(folder / "PRism_bundle.csv", index=False)
    refresh_people_index()


def refresh_all_backups() -> None:
    for person_id in get_people()["id"].tolist():
        refresh_person_backups(int(person_id))


def get_people() -> pd.DataFrame:
    """Return every database person, including the internal demo sandbox."""
    return query("SELECT id,display_name,created_at FROM people ORDER BY id")


def get_visible_people() -> pd.DataFrame:
    """Return only real profiles shown in PRism's normal profile UI."""
    return query(
        "SELECT id,display_name,created_at FROM people WHERE display_name<>? ORDER BY id",
        (HIDDEN_DEMO_NAME,),
    )


def get_person(person_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()


def create_person(display_name: str) -> int:
    name = display_name.strip() or "New profile"
    with connect() as con:
        cur = con.execute(
            "INSERT INTO people(display_name,created_at) VALUES(?,?)",
            (name, datetime.now().isoformat(timespec="seconds")),
        )
        person_id = int(cur.lastrowid)
        con.execute("INSERT INTO profile(id,name) VALUES(?,?)", (person_id, name))
    refresh_person_backups(person_id)
    return person_id


def rename_person(person_id: int, display_name: str) -> None:
    name = display_name.strip() or "Profile"
    with connect() as con:
        con.execute("UPDATE people SET display_name=? WHERE id=?", (name, person_id))
        con.execute("UPDATE profile SET name=? WHERE id=?", (name, person_id))
    refresh_person_backups(person_id)


def delete_person(person_id: int) -> None:
    """Delete one profile and its separate local CSV backup folder.

    PRism never allows the final remaining profile to be deleted.
    """
    people = get_people()
    if len(people) <= 1:
        raise ValueError("PRism must keep at least one profile.")

    # Remember the backup folder before deleting the profile row, because the
    # folder name uses the person's display name.
    backup_folder = person_folder(person_id)
    with connect() as con:
        for table in DATA_TABLES:
            con.execute(f"DELETE FROM {table} WHERE person_id=?", (person_id,))
        con.execute("DELETE FROM sessions WHERE person_id=?", (person_id,))
        con.execute("DELETE FROM profile WHERE id=?", (person_id,))
        con.execute("DELETE FROM people WHERE id=?", (person_id,))

    if backup_folder.exists():
        shutil.rmtree(backup_folder, ignore_errors=True)

    refresh_people_index()


def profile_for(person_id: int) -> pd.Series:
    df = query("SELECT * FROM profile WHERE id=?", (person_id,))
    if df.empty:
        with connect() as con:
            con.execute("INSERT INTO profile(id,name) VALUES(?,?)", (person_id, ""))
        df = query("SELECT * FROM profile WHERE id=?", (person_id,))
    return df.iloc[0]


def save_profile(person_id: int, values: dict) -> None:
    old_folder = person_folder(person_id)
    with connect() as con:
        con.execute(
            """
            UPDATE profile
            SET name=?,age=?,height_cm=?,gender=?,goal=?,activity=?,days_goal=?,equipment=?,diet=?
            WHERE id=?
            """,
            (
                values.get("name", ""),
                values.get("age"),
                values.get("height_cm"),
                values.get("gender", "Prefer not to say"),
                values.get("goal", "Build muscle"),
                values.get("activity", "Moderate (3–5 days/week)"),
                values.get("days_goal", 4),
                values.get("equipment", "Full gym"),
                values.get("diet", "No preference"),
                person_id,
            ),
        )
        if values.get("name", "").strip():
            con.execute("UPDATE people SET display_name=? WHERE id=?", (values["name"].strip(), person_id))
    new_folder = person_folder(person_id)
    if old_folder != new_folder and old_folder.exists():
        shutil.rmtree(old_folder, ignore_errors=True)
    refresh_person_backups(person_id)


def person_table(table: str, person_id: int, order: str = "id DESC") -> pd.DataFrame:
    if table not in DATA_TABLES:
        raise ValueError("Unknown PRism table")
    return query(f"SELECT * FROM {table} WHERE person_id=? ORDER BY {order}", (person_id,))


def clear_table_for_person(table: str, person_id: int) -> None:
    if table not in DATA_TABLES:
        raise ValueError("Unknown PRism table")
    with connect() as con:
        con.execute(f"DELETE FROM {table} WHERE person_id=?", (person_id,))
        if table == "workouts":
            con.execute("DELETE FROM sessions WHERE person_id=?", (person_id,))
    refresh_person_backups(person_id)


def delete_row(table: str, row_id: int, person_id: int) -> None:
    if table not in DATA_TABLES:
        raise ValueError("Unknown PRism table")
    with connect() as con:
        con.execute(f"DELETE FROM {table} WHERE id=? AND person_id=?", (row_id, person_id))
    refresh_person_backups(person_id)


def mark_session_complete(person_id: int, day: str, split: str) -> None:
    """Mark one workout day complete so the dashboard can advance."""
    with connect() as con:
        con.execute(
            """
            INSERT INTO sessions(person_id,day,split,completed_at) VALUES(?,?,?,?)
            ON CONFLICT(person_id,day) DO UPDATE SET split=excluded.split,completed_at=excluded.completed_at
            """,
            (person_id, day, split, datetime.now().isoformat(timespec="seconds")),
        )


def unmark_session_complete(person_id: int, day: str) -> None:
    """Undo an accidental Finish workout action for one day."""
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE person_id=? AND day=?", (person_id, day))


def session_is_complete(person_id: int, day: str) -> bool:
    with connect() as con:
        row = con.execute(
            "SELECT 1 FROM sessions WHERE person_id=? AND day=? LIMIT 1",
            (person_id, day),
        ).fetchone()
    return row is not None


# Storage is initialized by app.py after Streamlit page configuration.
# This lets the public entrypoint assign an isolated per-session database
# before any SQLite file is opened.

