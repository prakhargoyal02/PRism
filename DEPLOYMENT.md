# Deploy PRism

## GitHub release rules

Commit the application code, docs, assets, fake sample CSV, and `supabase_schema.sql`.

Do not commit:

```text
prism.db
*.db
*.sqlite*
csv_backups/
.streamlit/secrets.toml
.env
```

The included `.gitignore` already blocks these paths.

## Streamlit Community Cloud

Create a new app from the PRism GitHub repository.

Use:

```text
Branch: main
Main file path: streamlit_app.py
```

`streamlit_app.py` enables the public/live mode.

### Before adding Supabase secrets

The site still works as a complete disposable public demo. Private cloud login is hidden behind a setup message.

### After adding Supabase secrets

Add the values described in `CLOUD_SETUP.md` to Streamlit's Secrets settings. The live site then supports:

- signed-out visitor → isolated fake demo;
- signed-in owner → private cloud-synced PRism.

## First real-data migration

Do not upload your local `prism.db` to GitHub or Streamlit.

Export your personal PRism Bundle CSV locally, sign into the live private PRism, and import the bundle with **Add safely**.

## Final checks

1. Open the live site while signed out.
2. Confirm only fictional Demo data is visible.
3. Add and delete a fake record.
4. Import `sample_data/PRism_Demo_Bundle.csv`.
5. Reset fake demo data.
6. Sign into the private account.
7. Confirm private records are different from Demo records.
8. Make one change on phone.
9. Refresh/open the private app on desktop and confirm it appears.
10. Sign out and verify the site returns to the fake Demo sandbox.
