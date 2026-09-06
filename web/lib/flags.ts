import "server-only";
import crypto from "node:crypto";
import { manifest, byId } from "./manifest";

export function checkFlag(id: string, submitted: string): boolean {
  const c = byId[id];
  if (!c) return false;
  const guess = crypto
    .pbkdf2Sync(
      (submitted || "").trim(),
      Buffer.from(manifest.salt, "hex"),
      manifest.pbkdf2_iters,
      32,
      "sha256"
    )
    .toString("hex");
  const a = Buffer.from(guess);
  const b = Buffer.from(c.flag_pbkdf2);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
