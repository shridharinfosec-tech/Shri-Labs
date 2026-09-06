import "server-only";
import crypto from "node:crypto";
import { cookies } from "next/headers";
import { SignJWT, jwtVerify } from "jose";
import { getUser, insertUser } from "./db";

const PW_ITERS = 200_000;
const COOKIE = "sis_session";
export const USERNAME_RE = /^[A-Za-z0-9 ._-]{3,30}$/;

function secretKey() {
  return new TextEncoder().encode(process.env.SESSION_SECRET || "sis-dev-secret-change-me");
}

export function normUsername(u: string): string {
  return (u || "").trim().replace(/\s+/g, " ");
}

export function hashPw(password: string, saltHex: string): string {
  return crypto
    .pbkdf2Sync(password, Buffer.from(saltHex, "hex"), PW_ITERS, 32, "sha256")
    .toString("hex");
}

// ---- registration / login ----
export async function registerUser(
  username: string,
  password: string
): Promise<{ ok: boolean; message: string }> {
  if (!USERNAME_RE.test(username))
    return { ok: false, message: "Username must be 3-30 characters (letters, numbers, spaces, . _ - )." };
  if ((password || "").length < 6)
    return { ok: false, message: "Password must be at least 6 characters." };
  if (await getUser(username)) return { ok: false, message: "That username is already taken." };
  const salt = crypto.randomBytes(16).toString("hex");
  try {
    await insertUser(username, salt, hashPw(password, salt));
  } catch (e: any) {
    if (String(e).includes("23505") || /duplicate/i.test(String(e)))
      return { ok: false, message: "That username is already taken." };
    throw e;
  }
  return { ok: true, message: "ok" };
}

export async function verifyUser(username: string, password: string): Promise<string | null> {
  const rec = await getUser(normUsername(username));
  if (!rec) return null;
  const a = Buffer.from(hashPw(password, rec.salt));
  const b = Buffer.from(rec.pw_hash);
  return a.length === b.length && crypto.timingSafeEqual(a, b) ? rec.username : null;
}

// ---- sessions (signed JWT cookie) ----
export async function createSession(username: string): Promise<void> {
  const jwt = await new SignJWT({ u: username })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(secretKey());
  cookies().set(COOKIE, jwt, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 30 * 24 * 3600,
    secure: process.env.NODE_ENV === "production",
  });
}

export function clearSession(): void {
  cookies().set(COOKIE, "", { path: "/", maxAge: 0 });
}

export async function getSessionUser(): Promise<string | null> {
  const tok = cookies().get(COOKIE)?.value;
  if (!tok) return null;
  try {
    const { payload } = await jwtVerify(tok, secretKey());
    return (payload.u as string) || null;
  } catch {
    return null;
  }
}
