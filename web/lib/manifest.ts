import manifestJson from "@/data/manifest.json";

export interface Step {
  title: string;
  desc: string;
  cmd?: string;
}

export interface Challenge {
  id: string;
  slug: string;
  title: string;
  section: string;
  difficulty: number;
  tools: string[];
  brief: string;
  files: string[];
  hint: string;
  flag_pbkdf2: string;
  category: string;
  scenario?: string;
  objective?: string;
  est_time?: string;
  steps?: Step[];
}

export interface Manifest {
  batch: string;
  generated: string;
  salt: string;
  pbkdf2_iters: number;
  categories: string[];
  challenges: Challenge[];
}

export const manifest = manifestJson as unknown as Manifest;
export const challenges = manifest.challenges;
export const byId: Record<string, Challenge> = Object.fromEntries(
  challenges.map((c) => [c.id, c])
);

export function pointsFor(difficulty: number): number {
  return difficulty * 100;
}

export function levelWord(n: number): string {
  return n <= 1 ? "Beginner" : n === 2 ? "Easy" : n === 3 ? "Medium" : "Advanced";
}
