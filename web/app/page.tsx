import { redirect } from "next/navigation";
import Nav from "@/components/Nav";
import { getSessionUser } from "@/lib/auth";
import { getProgress } from "@/lib/db";
import { manifest, challenges, pointsFor } from "@/lib/manifest";
import { IconShield, IconCheck, stars } from "@/app/icons";
import { ResetAllButton } from "@/components/ResetButtons";

export const dynamic = "force-dynamic";

export default async function Dashboard({
  searchParams,
}: {
  searchParams: { m?: string };
}) {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  const prog = await getProgress(user);

  const core = challenges;
  const total = core.reduce((s, c) => s + pointsFor(c.difficulty), 0);
  const got = core
    .filter((c) => prog.solved[c.id])
    .reduce((s, c) => s + pointsFor(c.difficulty), 0);
  const nsolved = core.filter((c) => prog.solved[c.id]).length;
  const pct = core.length ? Math.round((100 * nsolved) / core.length) : 0;

  return (
    <>
      <Nav />
      <div className="wrap">
        {searchParams.m === "reset" && <div className="msg info">All progress reset.</div>}

        <section className="hero">
          <span className="eyebrow">
            <IconShield /> Module 20 &middot; Hands-on Lab
          </span>
          <h1>Applied Cryptography Lab</h1>
          <p>
            Twelve guided labs across encoding, classical ciphers, encryption and hashing. Each lab
            has a scenario and a step-by-step solve guide &mdash; do the work in your Kali terminal,
            then submit the <code>{"SIS{...}"}</code> flag to record your progress.
          </p>
          <div className="hero-auth">
            <IconShield /> Authorised training environment &middot; sign in to track your progress
          </div>
          <div className="stats">
            <div className="ring" style={{ ["--p" as any]: pct }}>
              <div className="hole">
                <b>{pct}%</b>
                <span>DONE</span>
              </div>
            </div>
            <div className="stat">
              <b>
                {nsolved}
                <span style={{ color: "#6f86a8" }}>/{core.length}</span>
              </b>
              <span>Labs</span>
            </div>
            <div className="stat">
              <b>
                {got}
                <span style={{ color: "#6f86a8" }}>/{total}</span>
              </b>
              <span>Points</span>
            </div>
            <div className="stat spacer"></div>
          </div>
        </section>

        {manifest.categories.map((cat) => {
          const members = challenges.filter((c) => c.category === cat);
          if (!members.length) return null;
          const done = members.filter((c) => prog.solved[c.id]).length;
          return (
            <div key={cat}>
              <div className="cat-h">
                <span className="dot"></span>
                {cat}
                <span className="cat-count">
                  {done}/{members.length}
                </span>
              </div>
              <div className="grid">
                {members.map((c) => {
                  const solved = Boolean(prog.solved[c.id]);
                  return (
                    <a key={c.id} className={"card" + (solved ? " done" : "")} href={`/c/${c.id}`}>
                      <div className="card-top">
                        <span className="cnum">{c.id}</span>
                        {solved ? (
                          <span className="badge solved">
                            <IconCheck /> Solved
                          </span>
                        ) : (
                          <span className="badge">Open</span>
                        )}
                      </div>
                      <h3>{c.title}</h3>
                      <div className="csec">{c.section}</div>
                      <div className="cmeta">
                        <span className="stars">{stars(c.difficulty)}</span>
                        <span className="pts">{pointsFor(c.difficulty)} pts</span>
                      </div>
                      <p className="cbrief">{c.brief}</p>
                      <div className="chips">
                        {c.tools.map((t) => (
                          <span key={t} className="chip">
                            {t}
                          </span>
                        ))}
                      </div>
                    </a>
                  );
                })}
              </div>
            </div>
          );
        })}

        <div className="row" style={{ marginTop: 24 }}>
          <ResetAllButton />
        </div>
      </div>
    </>
  );
}
