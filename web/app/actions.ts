"use server";

import { redirect } from "next/navigation";
import {
  registerUser,
  verifyUser,
  createSession,
  clearSession,
  getSessionUser,
  normUsername,
} from "@/lib/auth";
import { getProgress, saveProgress } from "@/lib/db";
import { checkFlag } from "@/lib/flags";
import { byId } from "@/lib/manifest";

export async function loginAction(formData: FormData) {
  const username = normUsername(String(formData.get("username") || ""));
  const password = String(formData.get("password") || "");
  const key = await verifyUser(username, password);
  if (!key) {
    redirect(
      `/login?error=${encodeURIComponent("Invalid username or password.")}&u=${encodeURIComponent(username)}`
    );
  }
  await createSession(key);
  redirect("/");
}

export async function registerAction(formData: FormData) {
  const username = normUsername(String(formData.get("username") || ""));
  const password = String(formData.get("password") || "");
  const confirm = String(formData.get("confirm") || "");
  if (password !== confirm) {
    redirect(
      `/register?error=${encodeURIComponent("The two passwords do not match.")}&u=${encodeURIComponent(username)}`
    );
  }
  const { ok, message } = await registerUser(username, password);
  if (!ok) {
    redirect(`/register?error=${encodeURIComponent(message)}&u=${encodeURIComponent(username)}`);
  }
  await createSession(username);
  redirect("/");
}

export async function logoutAction() {
  clearSession();
  redirect("/login");
}

export async function submitFlagAction(formData: FormData) {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  const id = String(formData.get("id") || "");
  const flag = String(formData.get("flag") || "");
  if (!byId[id]) redirect("/");
  const p = await getProgress(user);
  p.attempts[id] = (p.attempts[id] || 0) + 1;
  let ok = false;
  if (checkFlag(id, flag)) {
    if (!p.solved[id]) p.solved[id] = new Date().toISOString();
    ok = true;
  }
  await saveProgress(user, p);
  redirect(`/c/${id}?m=${ok ? "ok" : "bad"}`);
}

export async function resetLabAction(formData: FormData) {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  const id = String(formData.get("id") || "");
  if (!byId[id]) redirect("/");
  const p = await getProgress(user);
  delete p.solved[id];
  delete p.attempts[id];
  await saveProgress(user, p);
  redirect(`/c/${id}?m=labreset`);
}

export async function resetAllAction() {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  await saveProgress(user, { solved: {}, attempts: {} });
  redirect("/?m=reset");
}
