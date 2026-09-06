/**
 * Storage backend: Supabase (Postgres via PostgREST) when SUPABASE_URL and
 * SUPABASE_SERVICE_KEY are set (production / Vercel), else local JSON files
 * under web/.data for local development.
 */
import "server-only";
import fs from "node:fs";
import path from "node:path";

const URL = (process.env.SUPABASE_URL || "").replace(/\/+$/, "");
const KEY =
  process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || "";
export const useSupabase = Boolean(URL && KEY);

export interface UserRow {
  username: string;
  salt: string;
  pw_hash: string;
}
export interface Progress {
  solved: Record<string, string>;
  attempts: Record<string, number>;
}

// ---------------------------------------------------------------- Supabase
async function sb(
  method: string,
  table: string,
  opts: { params?: Record<string, string>; body?: unknown; prefer?: string } = {}
): Promise<any> {
  const qs = opts.params ? "?" + new URLSearchParams(opts.params).toString() : "";
  const headers: Record<string, string> = {
    apikey: KEY,
    Authorization: `Bearer ${KEY}`,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (opts.prefer) headers["Prefer"] = opts.prefer;
  const res = await fetch(`${URL}/rest/v1/${table}${qs}`, {
    method,
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Supabase ${method} ${table} -> ${res.status}: ${await res.text()}`);
  }
  const txt = await res.text();
  return txt ? JSON.parse(txt) : [];
}

// ---------------------------------------------------------------- local files
const DATA_DIR = path.join(process.cwd(), ".data");
const USERS = path.join(DATA_DIR, "users.json");
const PROG = path.join(DATA_DIR, "progress");

function readJson<T>(p: string, def: T): T {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8")) as T;
  } catch {
    return def;
  }
}
function writeJson(p: string, data: unknown) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(data, null, 2));
}
function progFile(username: string) {
  return path.join(PROG, username.replace(/[^A-Za-z0-9_]/g, "_").slice(0, 60) + ".json");
}

// ---------------------------------------------------------------- API
export async function getUser(username: string): Promise<UserRow | null> {
  const lower = (username || "").toLowerCase();
  if (useSupabase) {
    const rows = await sb("GET", "users", {
      params: { username_lower: `eq.${lower}`, select: "username,salt,pw_hash", limit: "1" },
    });
    return rows[0] || null;
  }
  const users: Record<string, any> = readJson(USERS, {});
  const key = Object.keys(users).find((u) => u.toLowerCase() === lower);
  if (!key) return null;
  return { username: key, salt: users[key].salt, pw_hash: users[key].pw_hash };
}

export async function insertUser(username: string, salt: string, pw_hash: string): Promise<void> {
  if (useSupabase) {
    await sb("POST", "users", {
      body: {
        username,
        username_lower: username.toLowerCase(),
        salt,
        pw_hash,
        created_at: new Date().toISOString(),
      },
      prefer: "return=minimal",
    });
    return;
  }
  const users: Record<string, any> = readJson(USERS, {});
  users[username] = { salt, pw_hash, created: new Date().toISOString() };
  writeJson(USERS, users);
}

export async function getProgress(username: string): Promise<Progress> {
  if (useSupabase) {
    const rows = await sb("GET", "progress", {
      params: { username: `eq.${username}`, select: "solved,attempts", limit: "1" },
    });
    if (rows[0]) return { solved: rows[0].solved || {}, attempts: rows[0].attempts || {} };
    return { solved: {}, attempts: {} };
  }
  return readJson(progFile(username), { solved: {}, attempts: {} });
}

export async function saveProgress(username: string, p: Progress): Promise<void> {
  if (useSupabase) {
    await sb("POST", "progress", {
      params: { on_conflict: "username" },
      body: { username, solved: p.solved, attempts: p.attempts, updated_at: new Date().toISOString() },
      prefer: "resolution=merge-duplicates,return=minimal",
    });
    return;
  }
  writeJson(progFile(username), { solved: p.solved, attempts: p.attempts });
}
