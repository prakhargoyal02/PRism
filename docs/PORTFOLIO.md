# PRism — Portfolio Case Study

> A private fitness tracker and live training companion built as a product, not just a CRUD demo.

**Live app:** https://prism-prakhargoyal-0002.streamlit.app/  
**Repository:** https://github.com/prakhargoyal02/PRism

## The product problem

Training data usually ends up fragmented across notes, spreadsheets, meal trackers, sleep apps, and memory. PRism was built to make those signals readable in one place while keeping the gym workflow fast enough to use between sets.

The project had a second constraint: it also needed to work as a **public portfolio project without publishing the owner's real fitness data**.

That created two product modes from one codebase:

1. **Public Demo Sandbox** — disposable fictional data for anyone opening the live link.
2. **Private Cloud** — authenticated personal data synchronized between trusted devices.

## What I built

| Surface | What it does |
|---|---|
| Explore | Continuous read-only story of today, training, nutrition, recovery, progress and the next workout |
| Live Workout | Set-by-set logging with reps, load, RPE, notes, previous performance, planned-set progress and rest timer |
| Manage | Workout-plan editing, meals, sleep, weight, profiles, deletion tools and CSV workflows |
| Public Demo | Isolated temporary sandbox with fake data, reset, imports and exports |
| Private Cloud | Supabase-authenticated state with Row Level Security and cross-device synchronization |

## Engineering decisions

### 1. SQLite stays the working database

PRism keeps SQLite as the local/session working store because it is simple, portable, fast, and easy to back up. The cloud layer synchronizes that state rather than replacing the whole application with remote database calls.

### 2. Cloud sync is a privacy boundary, not just storage

The public demo and private account do not share the same working database. Signed-out visitors get an isolated temporary demo database. Authenticated users get a separate private database synchronized to their own Supabase row.

### 3. Supabase RLS protects private state

The cloud schema uses Supabase Auth and PostgreSQL Row Level Security so a signed-in user can only access the state row owned by that user. The app ships only the publishable key, never a service-role secret.

### 4. Login survives normal refreshes without storing a password

PRism uses a two-step email → password login flow. After successful authentication, the browser stores only the Supabase refresh token needed to restore the session. A normal page refresh or browser reopen can restore Private PRism without storing the user's password.

### 5. CSV remains first-class

Cloud sync is convenient, but portable files still matter. PRism can export one Bundle CSV or separate files and can detect supported CSV types from their columns rather than requiring exact filenames.

Multiple separate CSV files can also be selected together and imported in one pass.

### 6. Mobile is treated as a real gym interface

The live app has mobile-specific layout rules for navigation, cards, the animated system map, chart interaction, and weekly-plan stacking. Desktop keeps the wider editorial grid while phone layouts become a clean single-column flow.

## Problems solved during development

This project included several bugs that only appeared after real deployment and use:

- Streamlit reruns initially blanked the UI because the entrypoint imported `app.py` only once. The deployed entrypoint now executes it on every rerun.
- Streamlit Community Cloud used a server timezone that could disagree with India dates. The deployment entrypoint now sets the India timezone and advances the live-workout date on a new local calendar day.
- A single Streamlit form submitted too early when Enter was pressed in the email field. Login was redesigned as a true two-step flow.
- Normal browser refreshes originally discarded the authenticated session. PRism now restores the Supabase session through browser storage without storing the password.
- Streamlit's responsive column stacking produced out-of-order weekly-plan cards. The plan is now rendered as real rows so mobile order stays Monday → Sunday naturally.
- Public deployment needed to remain useful without exposing personal records, which led to the isolated disposable demo architecture.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python |
| UI / deployment | Streamlit |
| Dataframes / CSV | Pandas |
| Working store | SQLite |
| Private cloud | Supabase Auth + PostgreSQL |
| Security | Row Level Security |
| Visual system | HTML + CSS + SVG |
| Hosting | Streamlit Community Cloud |
| Source control | GitHub |

## Privacy model

```text
Live URL
  ├── signed out → fictional disposable demo
  └── signed in  → private cloud-synced working database
```

Private database files, local CSV backups, secrets, and environment files are excluded from Git.

## How to demo PRism in an interview

A short walkthrough:

1. Open the live link while signed out and explain that the visible data is fictional.
2. Show Explore and the continuous training/nutrition/recovery/progress story.
3. Open Live Workout and show set logging, planned-set progress and previous performance.
4. Open Manage and show the Bundle/multi-CSV workflow.
5. Explain the privacy split between the public sandbox and Supabase-authenticated private mode.
6. Mention the deployment-specific fixes: rerun-safe entrypoint, India timezone, refresh-safe auth and mobile layout.

That demonstrates product design, application state, database work, authentication, privacy, deployment debugging and responsive UI in one project.

## What this project demonstrates

- building beyond a tutorial-style CRUD app;
- designing a public/private data boundary;
- debugging real Streamlit rerun and deployment behavior;
- authentication and browser-session restoration;
- SQLite + cloud synchronization;
- duplicate-safe import/export workflows;
- responsive product design;
- translating real daily use into software requirements.

## Status

PRism is live and usable. Core functionality is intentionally kept stable; future changes should be additive polish or clearly scoped features rather than large rewrites.

