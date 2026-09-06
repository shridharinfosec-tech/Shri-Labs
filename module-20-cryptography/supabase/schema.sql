-- ==========================================================================
-- Shri Labs  ·  Module 20 Cryptography portal  ·  Supabase schema
-- Run this once in your Supabase project:  Dashboard -> SQL Editor -> New query
-- -> paste -> Run.
-- ==========================================================================

-- ---- accounts (password stored only as a salted PBKDF2 hash) ----
create table if not exists public.users (
  username        text primary key,
  username_lower  text not null,
  salt            text not null,
  pw_hash         text not null,
  created_at      timestamptz default now()
);
create unique index if not exists users_username_lower_idx
  on public.users (username_lower);

-- ---- per-user lab progress ----
create table if not exists public.progress (
  username    text primary key references public.users(username) on delete cascade,
  solved      jsonb default '{}'::jsonb,
  attempts    jsonb default '{}'::jsonb,
  updated_at  timestamptz default now()
);

-- ---- security ----
-- The portal talks to these tables ONLY with the service_role key from the
-- server (which bypasses RLS). Enable RLS with NO policies so the public/anon
-- key can never read or write accounts or progress.
alter table public.users    enable row level security;
alter table public.progress enable row level security;
