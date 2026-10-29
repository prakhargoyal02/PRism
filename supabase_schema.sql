-- PRism private cloud state
-- Run this once in the Supabase SQL editor.
-- Public/demo visitors never access this table.

create table if not exists public.prism_state (
    user_id uuid primary key references auth.users(id) on delete cascade,
    state_blob text not null default '',
    revision bigint not null default 1 check (revision > 0),
    updated_at timestamptz not null default now()
);

create index if not exists prism_state_user_id_idx
    on public.prism_state(user_id);

create or replace function public.prism_touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists prism_state_touch_updated_at on public.prism_state;
create trigger prism_state_touch_updated_at
before update on public.prism_state
for each row execute function public.prism_touch_updated_at();

alter table public.prism_state enable row level security;

-- Least privilege: signed-out users get no access at all.
revoke all on table public.prism_state from anon, authenticated;
grant select, insert, update, delete on table public.prism_state to authenticated;

-- Each authenticated Supabase user can touch ONLY their own row.
drop policy if exists "PRism users select own state" on public.prism_state;
create policy "PRism users select own state"
on public.prism_state
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "PRism users insert own state" on public.prism_state;
create policy "PRism users insert own state"
on public.prism_state
for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "PRism users update own state" on public.prism_state;
create policy "PRism users update own state"
on public.prism_state
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "PRism users delete own state" on public.prism_state;
create policy "PRism users delete own state"
on public.prism_state
for delete
to authenticated
using ((select auth.uid()) = user_id);
