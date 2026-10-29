# How PRism Works

PRism intentionally keeps the code split into beginner-friendly responsibilities.

## `app.py`

Owns screens and user interactions:

- Explore
- Live Workout
- Manage
- public Demo behavior
- private cloud login surface

## `database.py`

Owns the SQLite schema and local data operations. SQLite remains the working data model because it keeps the app simple and makes CSV import/export straightforward.

## `cloud_sync.py`

Owns private live synchronization.

When the public site is signed out, this module is not used for personal data.

When the owner signs in:

1. Supabase Auth verifies the email/password.
2. PRism selects a private per-session SQLite working file.
3. The newest RLS-protected cloud state is restored into that file.
4. Normal PRism code reads/writes SQLite exactly as before.
5. Changed SQLite state is compressed and saved back to the user's private Supabase row.
6. A revision number protects against silently overwriting a newer change from another device.

## `csv_tools.py`

Recognizes CSV types from their columns and supports:

- Bundle CSV
- weights
- workouts
- meals
- sleep
- plans
- profile

`Add safely` skips duplicates. Replace intentionally replaces matching categories.

## `demo_data.py`

Creates fictional sample data relative to the current date so the public portfolio demo stays useful instead of aging into an empty dashboard.

## Public vs private storage

```text
Signed out
→ session temp directory
→ fake Demo SQLite
→ disposable

Signed in
→ session private working SQLite
→ Supabase prism_state row
→ durable across phone/desktop

Local app.py
→ project prism.db
→ persistent on that computer
```

No personal database or backup folder belongs in GitHub.
