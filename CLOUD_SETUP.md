# PRism Private Cloud Setup

PRism uses Supabase only for the private signed-in experience. Signed-out visitors remain in a temporary fake demo and never read or write the private cloud table.

## 1. Create a Supabase project

Create a project in Supabase and keep the project URL plus the **publishable key** (or legacy anon key).

Do **not** use a service-role or secret key in PRism.

## 2. Create the PRism cloud table

Open the Supabase SQL editor and run the complete contents of:

```text
supabase_schema.sql
```

The migration:

- creates `public.prism_state`;
- enables Row Level Security;
- removes anonymous access;
- grants the authenticated role only the operations PRism needs;
- adds separate SELECT / INSERT / UPDATE / DELETE policies using `auth.uid()`;
- ensures each authenticated user can access only their own cloud row.

## 3. Create the private owner account

Create the owner/user in Supabase Auth. PRism intentionally provides **sign-in only** on the public website, so random visitors cannot create cloud accounts from the app.

## 4. Configure Streamlit secrets

In Streamlit Community Cloud, add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_PUBLISHABLE_KEY"
```

A legacy project can use:

```toml
SUPABASE_ANON_KEY = "YOUR_ANON_KEY"
```

Never commit `.streamlit/secrets.toml`.

## 5. First private login

Open the live PRism site and expand **Personal cloud login**.

On the first login PRism creates a fresh private cloud state. To move existing desktop data into it:

1. Export your personal **PRism Bundle CSV** from local PRism.
2. Sign in to the live private PRism.
3. Open `Manage → People & CSV`.
4. Upload the personal Bundle CSV.
5. Choose the correct profile/destination.
6. Use **Add safely** for normal migration.

After that, phone and desktop browser sessions use the same private cloud state.

## Cloud synchronization behavior

PRism keeps an SQLite working copy for compatibility with the existing app and CSV code. The complete working state is compressed into a private Supabase row after changes.

Each cloud save increments a revision number. If another device changes the cloud state first, PRism refuses to silently overwrite it and shows two explicit options:

- **Reload newest cloud copy**
- **Keep this device and overwrite cloud**

For normal gym use, use one device at a time and the sync is automatic.

