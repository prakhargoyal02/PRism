# PRism Final Test Checklist

## Public Demo

- [ ] Live link opens without login.
- [ ] Only fictional PRism Demo data appears.
- [ ] Explore works.
- [ ] Live Workout works.
- [ ] Manage works in the public sandbox.
- [ ] Add fake workout / meal / sleep / weight works.
- [ ] Delete fake records works.
- [ ] Add safely import works.
- [ ] Replace import works.
- [ ] Fake Demo Bundle CSV downloads.
- [ ] `sample_data/PRism_Demo_Bundle.csv` imports.
- [ ] Reset Demo restores fictional data.

## Private Cloud

- [ ] Public sign-up is not exposed.
- [ ] Owner sign-in works.
- [ ] Demo data disappears after private sign-in.
- [ ] Private CSV import works.
- [ ] Private Bundle CSV export works.
- [ ] Phone workout entry syncs to desktop.
- [ ] Desktop change syncs back to phone.
- [ ] Sign out returns to public Demo.
- [ ] A second visitor cannot read private data.

## Local Desktop

- [ ] `py -m streamlit run app.py` still works.
- [ ] Existing `prism.db` remains untouched by GitHub packaging.
- [ ] Existing `csv_backups/` remains private.
- [ ] Local Bundle CSV export/import still works.

## Repository safety

- [ ] No `.db` or `.sqlite` files tracked.
- [ ] No `csv_backups/` tracked.
- [ ] No `.streamlit/secrets.toml` tracked.
- [ ] Only fake CSV exists under `sample_data/`.
- [ ] Supabase service-role/secret key is nowhere in the repository.

