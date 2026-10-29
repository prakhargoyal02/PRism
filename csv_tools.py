"""CSV import/export tools for PRism.

Beginner summary:
- Normal CSV file names do not matter. PRism reads the columns.
- A PRism Bundle CSV can contain profile, weight, workouts, meals, sleep and plan rows in ONE file.
- Safe import keeps existing data and skips exact duplicates.
"""

from __future__ import annotations

from io import BytesIO
import numbers
import zipfile

import pandas as pd

import database as db

COLUMN_ALIASES = {
    "type": "record_type",
    "data_type": "record_type",
    "record": "record_type",
    "date": "day",
    "workout_date": "day",
    "sleep_date": "day",
    "measurement_date": "day",
    "time": "log_time",
    "recorded_time": "log_time",
    "meal": "meal_time",
    "meal_type": "meal_time",
    "weight": "kg",
    "weight_kg": "kg",
    "body_weight": "kg",
    "body_weight_kg": "kg",
    "set": "set_no",
    "set_number": "set_no",
    "repetitions": "reps",
    "reps_completed": "reps",
    "protein_g": "protein",
    "carbs_g": "carbs",
    "fat_g": "fat",
    "calories_kcal": "calories",
    "sleep_hours": "hours",
    "sleep_quality": "quality",
    "rest": "rest_seconds",
    "rest_sec": "rest_seconds",
    "height": "height_cm",
    "workout_name": "split",
    "session": "split",
    "session_split": "split",
    "nickname": "name",
    "target_training_days": "days_goal",
    "training_days": "days_goal",
}

DETECTION_RULES = {
    "weights": [{"day", "kg"}],
    "workouts": [{"day", "exercise", "reps", "kg"}, {"exercise", "set_no", "reps", "kg"}],
    "meals": [{"day", "food", "protein"}, {"day", "food", "calories"}],
    "sleep": [{"day", "hours"}],
    "plans": [{"weekday", "exercise", "sets"}, {"weekday", "exercise", "reps"}],
    "profile": [{"name", "age", "height_cm"}, {"age", "height_cm", "goal"}],
}

DEFAULTS = {
    "weights": {"log_time": "00:00", "note": ""},
    "workouts": {"log_time": "00:00", "split": "", "set_no": 1, "rpe": None, "note": ""},
    "meals": {"log_time": "00:00", "meal_time": "", "calories": 0, "protein": 0, "carbs": 0, "fat": 0},
    "sleep": {"log_time": "00:00", "quality": None, "note": ""},
    "plans": {"split": "Workout", "sets": 3, "reps": "8-12", "rest_seconds": 90},
    "profile": {
        "name": "",
        "age": None,
        "height_cm": None,
        "gender": "Prefer not to say",
        "goal": "Build muscle",
        "activity": "Moderate (3–5 days/week)",
        "days_goal": 4,
        "equipment": "Full gym",
        "diet": "No preference",
    },
}

DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

BUNDLE_TYPES = {"profile", "weights", "workouts", "meals", "sleep", "plans"}
BUNDLE_TYPE_ALIASES = {
    "weight": "weights", "weights": "weights", "body_weight": "weights",
    "workout": "workouts", "workouts": "workouts", "set": "workouts",
    "meal": "meals", "meals": "meals", "nutrition": "meals",
    "sleep": "sleep", "recovery": "sleep",
    "plan": "plans", "plans": "plans", "workout_plan": "plans",
    "profile": "profile", "person": "profile",
}


def normalise_column_name(name: str) -> str:
    clean = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    clean = clean.strip("_")
    return COLUMN_ALIASES.get(clean, clean)


def normalise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [normalise_column_name(c) for c in result.columns]
    return result.loc[:, ~result.columns.duplicated()]


def _normalise_record_type(value) -> str | None:
    if pd.isna(value):
        return None
    key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return BUNDLE_TYPE_ALIASES.get(key)


def detect_csv_type(df: pd.DataFrame) -> str | None:
    clean = normalise_dataframe(df)

    # One-file bundle detection comes first.
    if "record_type" in clean.columns:
        seen = {_normalise_record_type(v) for v in clean["record_type"].tolist()}
        seen.discard(None)
        if seen and seen.issubset(BUNDLE_TYPES):
            return "bundle"

    columns = set(clean.columns)
    matches = []
    for data_type, rule_sets in DETECTION_RULES.items():
        best = max((len(rule) for rule in rule_sets if rule.issubset(columns)), default=0)
        if best:
            matches.append((best, data_type))
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def _clean_day(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return pd.Timestamp.today().date().isoformat()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Could not understand date: {value}")
    return parsed.date().isoformat()


def _clean_time(value) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "00:00"
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Could not understand time: {value}")
    return parsed.strftime("%H:%M")


def _clean_weekday(value) -> int:
    if pd.isna(value):
        raise ValueError("Workout-plan weekday is missing")
    text = str(value).strip().lower()
    if text in DAY_NAMES:
        return DAY_NAMES[text]
    try:
        number = int(float(text))
        if 0 <= number <= 6:
            return number
    except ValueError:
        pass
    raise ValueError(f"Could not understand weekday: {value}. Use Monday-Sunday or 0-6.")


def prepare_dataframe(df: pd.DataFrame, data_type: str) -> pd.DataFrame:
    """Convert a loose CSV into PRism's clean internal format."""
    clean = normalise_dataframe(df)

    for column, default in DEFAULTS[data_type].items():
        if column not in clean.columns:
            clean[column] = default

    cols = db.PROFILE_COLUMNS if data_type == "profile" else db.TABLE_COLUMNS[data_type]
    required = {
        "weights": ["day", "kg"],
        "workouts": ["day", "exercise", "reps", "kg"],
        "meals": ["day", "food"],
        "sleep": ["day", "hours"],
        "plans": ["weekday", "exercise"],
        "profile": ["age", "height_cm"],
    }[data_type]

    missing = [c for c in required if c not in clean.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    clean = clean[cols].copy()

    # Drop rows whose required values are blank. This matters for bundle CSVs,
    # where every possible column exists but most cells are intentionally empty.
    for col in required:
        if col in clean.columns:
            clean = clean[clean[col].notna()]
            if clean[col].dtype == object:
                clean = clean[clean[col].astype(str).str.strip() != ""]

    if "day" in clean.columns:
        clean["day"] = clean["day"].apply(_clean_day)
    if "log_time" in clean.columns:
        clean["log_time"] = clean["log_time"].apply(_clean_time)
    if "weekday" in clean.columns:
        clean["weekday"] = clean["weekday"].apply(_clean_weekday)

    numeric_columns = {
        "weights": ["kg"],
        "workouts": ["set_no", "reps", "kg", "rpe"],
        "meals": ["calories", "protein", "carbs", "fat"],
        "sleep": ["hours", "quality"],
        "plans": ["sets", "rest_seconds"],
        "profile": ["age", "height_cm", "days_goal"],
    }[data_type]

    for column in numeric_columns:
        if column in clean.columns:
            clean[column] = pd.to_numeric(clean[column], errors="coerce")

    # Numeric conversion can create NaN for bad required values.
    clean = clean.dropna(subset=[c for c in required if c in clean.columns]).reset_index(drop=True)
    return clean


def prepare_bundle(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    clean = normalise_dataframe(df)
    if "record_type" not in clean.columns:
        raise ValueError("Bundle CSV needs a record_type column")

    clean["record_type"] = clean["record_type"].apply(_normalise_record_type)
    unknown_count = int(clean["record_type"].isna().sum())
    prepared: dict[str, pd.DataFrame] = {}

    for data_type in ("profile", "weights", "workouts", "meals", "sleep", "plans"):
        subset = clean[clean["record_type"] == data_type].drop(columns=["record_type"])
        if subset.empty:
            continue
        prepared[data_type] = prepare_dataframe(subset, data_type)

    prepared["_unknown_count"] = unknown_count  # type: ignore[assignment]
    return prepared


def bundle_profile_name(prepared: dict) -> str:
    profile = prepared.get("profile")
    if isinstance(profile, pd.DataFrame) and not profile.empty and "name" in profile.columns:
        name = str(profile.iloc[0]["name"] or "").strip()
        if name and name.lower() != "nan":
            return name
    return ""


def preview_upload(uploaded_file) -> dict:
    uploaded_file.seek(0)
    raw = pd.read_csv(uploaded_file)
    data_type = detect_csv_type(raw)
    if data_type is None:
        return {"type": None, "raw": raw, "clean": None}
    if data_type == "bundle":
        prepared = prepare_bundle(raw)
        return {"type": "bundle", "raw": raw, "clean": prepared}
    clean = prepare_dataframe(raw, data_type)
    return {"type": data_type, "raw": raw, "clean": clean}


def _row_key(row, columns: list[str]) -> tuple:
    values = []
    for column in columns:
        value = row[column]
        if pd.isna(value):
            value = None
        elif isinstance(value, numbers.Number) and not isinstance(value, bool):
            value = round(float(value), 6)
        else:
            value = str(value).strip()
        values.append(value)
    return tuple(values)


def import_dataframe(person_id: int, data_type: str, clean: pd.DataFrame, mode: str = "append") -> dict:
    """Import one clean DataFrame for one person."""
    if data_type == "profile":
        if clean.empty:
            return {"added": 0, "skipped": 0}
        row = clean.iloc[0].to_dict()
        values = {c: (None if pd.isna(row.get(c)) else row.get(c)) for c in db.PROFILE_COLUMNS}
        existing = db.profile_for(person_id)
        same = True
        for col in db.PROFILE_COLUMNS:
            old_value = existing.get(col)
            new_value = values.get(col)
            if pd.isna(old_value): old_value = None
            if pd.isna(new_value): new_value = None
            if isinstance(old_value, numbers.Number) and isinstance(new_value, numbers.Number):
                if round(float(old_value), 6) != round(float(new_value), 6):
                    same = False; break
            elif str(old_value or "").strip() != str(new_value or "").strip():
                same = False; break
        if same and mode != "replace":
            return {"added": 0, "skipped": len(clean)}
        db.save_profile(person_id, values)
        return {"added": 1, "skipped": max(len(clean) - 1, 0)}

    columns = db.TABLE_COLUMNS[data_type]

    # Most tables can use the whole row to decide whether a record is already
    # present. Workout plans are different: SQLite deliberately allows only
    # one exercise per person + weekday + exercise name, even if sets/reps/rest
    # are different. Use the SAME key here so "Add safely" never crashes on
    # the database UNIQUE constraint. If someone wants to replace a plan, they
    # can choose the explicit Replace import mode.
    unique_columns = ["weekday", "exercise"] if data_type == "plans" else columns

    if mode == "replace":
        db.clear_table_for_person(data_type, person_id)
        existing_keys = set()
    else:
        existing = db.person_table(data_type, person_id, order="id")
        existing_keys = set()
        if not existing.empty:
            for _, row in existing[unique_columns].iterrows():
                existing_keys.add(_row_key(row, unique_columns))

    rows_to_add = []
    skipped = 0
    for _, row in clean[columns].iterrows():
        key = _row_key(row, unique_columns)
        if key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)
        values = tuple(None if pd.isna(row[c]) else row[c] for c in columns)
        rows_to_add.append(values)

    actually_added = 0
    if rows_to_add:
        placeholders = ",".join(["?"] * (len(columns) + 1))
        insert_word = "INSERT OR IGNORE" if data_type == "plans" else "INSERT"
        sql = f"{insert_word} INTO {data_type}(person_id,{','.join(columns)}) VALUES({placeholders})"
        with db.connect() as con:
            before = con.total_changes
            con.executemany(sql, [(person_id, *row) for row in rows_to_add])
            actually_added = con.total_changes - before

        # OR IGNORE is a final safety net. If SQLite ignored anything that our
        # duplicate check did not catch, count it as skipped instead of lying
        # about how many rows were imported.
        skipped += len(rows_to_add) - actually_added
    else:
        actually_added = 0

    db.refresh_person_backups(person_id)
    return {"added": int(actually_added), "skipped": int(skipped)}


def import_bundle(person_id: int, prepared: dict, mode: str = "append") -> dict:
    """Import every supported record type from one bundle CSV."""
    results = {}
    total_added = 0
    total_skipped = int(prepared.get("_unknown_count", 0) or 0)
    for data_type in ("profile", "weights", "workouts", "meals", "sleep", "plans"):
        frame = prepared.get(data_type)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        result = import_dataframe(person_id, data_type, frame, mode=mode)
        results[data_type] = result
        total_added += int(result["added"])
        total_skipped += int(result["skipped"])
    return {"added": total_added, "skipped": total_skipped, "details": results}


def _bundle_frame_for_person(person_id: int) -> pd.DataFrame:
    """Build one wide CSV where record_type tells PRism how to read each row."""
    all_columns = [
        "record_type",
        *db.PROFILE_COLUMNS,
        "day", "log_time", "kg", "note",
        "split", "exercise", "set_no", "reps", "rpe",
        "meal_time", "food", "calories", "protein", "carbs", "fat",
        "hours", "quality", "weekday", "sets", "rest_seconds",
    ]
    # Keep order but remove duplicate column names such as reps/kg.
    all_columns = list(dict.fromkeys(all_columns))
    rows = []

    profile = db.query("SELECT * FROM profile WHERE id=?", (person_id,))
    if not profile.empty:
        row = {c: "" for c in all_columns}
        row["record_type"] = "profile"
        for col in db.PROFILE_COLUMNS:
            row[col] = profile.iloc[0][col]
        rows.append(row)

    for data_type in ("weights", "workouts", "meals", "sleep", "plans"):
        df = db.person_table(data_type, person_id, order="id")
        for _, source in df.iterrows():
            row = {c: "" for c in all_columns}
            row["record_type"] = data_type
            for col in db.TABLE_COLUMNS[data_type]:
                row[col] = source[col]
            rows.append(row)

    return pd.DataFrame(rows, columns=all_columns)


def export_person_bundle_csv(person_id: int) -> bytes:
    return _bundle_frame_for_person(person_id).to_csv(index=False).encode("utf-8-sig")


def export_person_zip(person_id: int) -> bytes:
    memory = BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("PRism_bundle.csv", export_person_bundle_csv(person_id))

        profile = db.query("SELECT * FROM profile WHERE id=?", (person_id,))
        profile_csv = (
            profile[db.PROFILE_COLUMNS] if not profile.empty else pd.DataFrame(columns=db.PROFILE_COLUMNS)
        ).to_csv(index=False)
        z.writestr("prism_profile.csv", profile_csv)

        for table, columns in db.TABLE_COLUMNS.items():
            df = db.person_table(table, person_id, order="id")
            export_df = df[columns] if not df.empty else pd.DataFrame(columns=columns)
            z.writestr(f"prism_{table}.csv", export_df.to_csv(index=False))
    return memory.getvalue()


def bundle_template_csv() -> bytes:
    frame = _bundle_frame_for_person_template()
    return frame.to_csv(index=False).encode("utf-8-sig")


def _bundle_frame_for_person_template() -> pd.DataFrame:
    columns = [
        "record_type",
        *db.PROFILE_COLUMNS,
        "day", "log_time", "kg", "note",
        "split", "exercise", "set_no", "reps", "rpe",
        "meal_time", "food", "calories", "protein", "carbs", "fat",
        "hours", "quality", "weekday", "sets", "rest_seconds",
    ]
    columns = list(dict.fromkeys(columns))
    example_rows = [
        {"record_type": "profile", "name": "Example Person", "age": 22, "height_cm": 170, "goal": "Improve fitness"},
        {"record_type": "weights", "day": "2026-10-26", "log_time": "07:30", "kg": 70, "note": "Morning"},
        {"record_type": "workouts", "day": "2026-10-26", "log_time": "18:30", "split": "Upper", "exercise": "Bench Press", "set_no": 1, "reps": 10, "kg": 40, "rpe": 7},
        {"record_type": "meals", "day": "2026-10-26", "log_time": "13:00", "meal_time": "Lunch", "food": "Rice, dal and vegetables", "calories": 600, "protein": 25},
        {"record_type": "sleep", "day": "2026-10-26", "log_time": "07:30", "hours": 7.5, "quality": 4},
        {"record_type": "plans", "weekday": "Monday", "split": "Upper", "exercise": "Bench Press", "sets": 3, "reps": "8-12", "rest_seconds": 90},
    ]
    rows = []
    for example in example_rows:
        row = {c: "" for c in columns}
        row.update(example)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def template_zip() -> bytes:
    memory = BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("PRism_bundle_template.csv", bundle_template_csv())
        z.writestr("profile_template.csv", pd.DataFrame(columns=db.PROFILE_COLUMNS).to_csv(index=False))
        for table, columns in db.TABLE_COLUMNS.items():
            z.writestr(f"{table}_template.csv", pd.DataFrame(columns=columns).to_csv(index=False))
        z.writestr(
            "README.txt",
            "PRism CSV templates\n\n"
            "EASIEST OPTION: use PRism_bundle_template.csv.\n"
            "The record_type column tells PRism whether each row is profile, weights, workouts, meals, sleep or plans.\n\n"
            "1. Open the CSV in Excel or Google Sheets.\n"
            "2. Keep the first header row.\n"
            "3. Add your data underneath.\n"
            "4. Save as CSV UTF-8.\n"
            "5. File name does not matter. PRism reads columns and record_type.\n",
        )
    return memory.getvalue()
