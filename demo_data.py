"""One-click sample data for PRism.

This file creates a completely separate profile called "PRism Demo".
It never changes the user's real profiles.
Dates are generated relative to today so the dashboard always looks useful.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import database as db

DEMO_NAME = "PRism Demo"


def _demo_person_id() -> int | None:
    """Return the demo profile id when it already exists."""
    people = db.get_people()
    if people.empty:
        return None
    match = people[people["display_name"] == DEMO_NAME]
    if match.empty:
        return None
    return int(match.iloc[0]["id"])


def _clear_demo_data(person_id: int) -> None:
    """Clear only the demo profile, never another person's records."""
    with db.connect() as con:
        for table in db.DATA_TABLES:
            con.execute(f"DELETE FROM {table} WHERE person_id=?", (person_id,))
        con.execute("DELETE FROM sessions WHERE person_id=?", (person_id,))


def _populate_demo(person_id: int) -> None:
    """Fill the demo profile with believable fictional test data."""
    today = date.today()

    # Profile details are fictional and exist only for product demonstration.
    with db.connect() as con:
        con.execute(
            """
            UPDATE profile
            SET name=?,age=?,height_cm=?,gender=?,goal=?,activity=?,days_goal=?,equipment=?,diet=?
            WHERE id=?
            """,
            (
                DEMO_NAME,
                24,
                172.0,
                "Prefer not to say",
                "Build muscle",
                "Moderate (3–5 days/week)",
                4,
                "Full gym",
                "Vegetarian",
                person_id,
            ),
        )
        con.execute("UPDATE people SET display_name=? WHERE id=?", (DEMO_NAME, person_id))

        # Weight trend: several points so the chart is immediately visible.
        weight_values = [68.8, 68.6, 68.5, 68.3, 68.2, 68.0]
        weight_days = [10, 8, 6, 4, 2, 0]
        con.executemany(
            "INSERT INTO weights(person_id,day,log_time,kg,note) VALUES(?,?,?,?,?)",
            [
                (person_id, (today - timedelta(days=days_ago)).isoformat(), "07:30", kg, "Demo measurement")
                for days_ago, kg in zip(weight_days, weight_values)
            ],
        )

        # Sleep for the latest week.
        sleep_values = [7.1, 6.8, 7.5, 7.3, 8.0, 7.6, 7.8]
        con.executemany(
            "INSERT INTO sleep(person_id,day,log_time,hours,quality,note) VALUES(?,?,?,?,?,?)",
            [
                (
                    person_id,
                    (today - timedelta(days=6-index)).isoformat(),
                    "07:20",
                    hours,
                    4 if hours >= 7 else 3,
                    "Demo recovery data",
                )
                for index, hours in enumerate(sleep_values)
            ],
        )

        # Meals today so the Nutrition section is never empty in Demo Mode.
        meals = [
            ("08:00", "Breakfast", "Oats, milk, banana and curd", 520, 24, 72, 16),
            ("13:15", "Lunch", "Rice, dal, paneer and salad", 720, 36, 94, 22),
            ("17:00", "Snack", "Fruit, yogurt and roasted chana", 310, 18, 45, 7),
            ("20:30", "Dinner", "Roti, vegetables, tofu/paneer and curd", 680, 38, 73, 23),
        ]
        con.executemany(
            """
            INSERT INTO meals(person_id,day,log_time,meal_time,food,calories,protein,carbs,fat)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            [
                (person_id, today.isoformat(), log_time, meal_time, food, calories, protein, carbs, fat)
                for log_time, meal_time, food, calories, protein, carbs, fat in meals
            ],
        )

        # Workout history on recent days. These are fictional test sets.
        workout_days = [today - timedelta(days=6), today - timedelta(days=4), today - timedelta(days=2)]
        workout_sets = [
            (workout_days[0], "Upper A", "Bench Press", [(1, 10, 35, 7), (2, 8, 40, 8), (3, 8, 40, 8)]),
            (workout_days[0], "Upper A", "Lat Pulldown", [(1, 12, 35, 7), (2, 10, 40, 8)]),
            (workout_days[1], "Lower A", "Leg Press", [(1, 12, 60, 7), (2, 10, 70, 8), (3, 10, 70, 8)]),
            (workout_days[1], "Lower A", "Romanian Deadlift", [(1, 10, 35, 7), (2, 8, 40, 8)]),
            (workout_days[2], "Upper B", "Incline Dumbbell Press", [(1, 12, 12.5, 7), (2, 10, 15, 8)]),
            (workout_days[2], "Upper B", "Seated Cable Row", [(1, 12, 30, 7), (2, 10, 35, 8)]),
        ]
        rows = []
        minute = 0
        for workout_day, split, exercise, sets in workout_sets:
            for set_no, reps, kg, rpe in sets:
                rows.append(
                    (
                        person_id,
                        workout_day.isoformat(),
                        f"18:{30 + (minute % 25):02d}",
                        split,
                        exercise,
                        set_no,
                        reps,
                        kg,
                        rpe,
                        "Fictional demo set",
                    )
                )
                minute += 4
        con.executemany(
            """
            INSERT INTO workouts(person_id,day,log_time,split,exercise,set_no,reps,kg,rpe,note)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )

        # A complete weekly plan. Sunday is rest.
        plan = {
            0: ("Upper A", [("Bench Press", 3, "6-10", 120), ("Lat Pulldown", 3, "8-12", 90), ("Seated Cable Row", 3, "8-12", 90), ("Lateral Raise", 3, "12-15", 60)]),
            1: ("Lower A", [("Leg Press", 3, "8-12", 120), ("Romanian Deadlift", 3, "8-12", 120), ("Leg Curl", 3, "10-15", 75), ("Calf Raise", 3, "12-20", 60)]),
            2: ("Recovery", [("Easy walk", 1, "20-30 min", 0), ("Mobility routine", 1, "5-10 min", 0)]),
            3: ("Upper B", [("Incline Dumbbell Press", 3, "8-12", 90), ("Seated Cable Row", 3, "8-12", 90), ("Shoulder Press", 3, "8-12", 90), ("Biceps Curl", 2, "10-15", 60)]),
            4: ("Lower B", [("Squat or Goblet Squat", 3, "6-10", 120), ("Hip Thrust", 3, "8-12", 90), ("Leg Extension", 3, "10-15", 75), ("Calf Raise", 3, "12-20", 60)]),
            5: ("Optional cardio", [("Comfortable cardio", 1, "20-30 min", 0)]),
            6: ("Rest", [("Rest / light mobility", 1, "—", 0)]),
        }
        plan_rows = []
        for weekday, (split, exercises) in plan.items():
            for exercise, sets, reps, rest in exercises:
                plan_rows.append((person_id, weekday, split, exercise, sets, reps, rest))
        con.executemany(
            """
            INSERT OR IGNORE INTO plans(person_id,weekday,split,exercise,sets,reps,rest_seconds)
            VALUES(?,?,?,?,?,?,?)
            """,
            plan_rows,
        )

    db.refresh_person_backups(person_id)


def open_demo_profile(reset: bool = False) -> int:
    """Create/open the demo profile. reset=True rebuilds only demo data."""
    person_id = _demo_person_id()
    if person_id is None:
        person_id = db.create_person(DEMO_NAME)
        reset = True

    if reset:
        _clear_demo_data(person_id)
        _populate_demo(person_id)

    return person_id

