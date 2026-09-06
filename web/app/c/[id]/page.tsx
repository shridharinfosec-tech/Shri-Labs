import { redirect, notFound } from "next/navigation";
import Nav from "@/components/Nav";
import { getSessionUser } from "@/lib/auth";
import { getProgress } from "@/lib/db";
import { byId, pointsFor, levelWord } from "@/lib/manifest";
import { IconShield, IconCheck, IconDownload, IconSteps, stars } from "@/app/icons";
import { ResetLabButton } from "@/components/ResetButtons";
import { submitFlagAction } from "@/app/actions";

export const dynamic = "force-dynamic";

export default async function LabPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { m?: string };
}) {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  const c = byId[params.id];
  if (!c) notFound();
  const prog = await getProgress(user);
  const solved = Boolean(prog.solved[c.id]);
  const attempts = prog.attempts[c.id] || 0;

  let banner = null;
  if (searchParams.m === "ok")
    banner = (
      <div className="msg ok">
        <IconCheck /> Correct flag &mdash; challenge solved!
      </div>
    );
  else if (searchParams.m === "bad")
    banner = <div className="msg bad">&#10007; Not quite. Check your flag and try again.</div>;
  else if (searchParams.m === "labreset")
    banner = (
      <div className="msg info">This lab has been reset &mdash; you can solve it again.</div>
    );

  return (
    <>
      <Nav />
      <div className="wrap">
        {banner}
        {solved && (
          <div className="msg ok">
            <IconCheck /> You solved this lab.
          </div>
        )}
        <div className="crumbs">
          <a href="/">All labs</a> &nbsp;/&nbsp; {c.category} &nbsp;/&nbsp; Lab {c.id}
        </div>

        <div className="detail">
          {/* LEFT: objective, details, files, submit, reset */}
          <div className="panel aside">
            <div className="objbox">
              <span className="ob-label">Objective</span>
              {c.objective || c.brief}
            </div>
            <h4>Lab details</h4>
            <ul className="labmeta">
              <li>
                <span className="k">Track</span>
                <span className="v">{c.category}</span>
              </li>
              <li>
                <span className="k">Level</span>
                <span className="v">
                  {stars(c.difficulty)} &nbsp;{levelWord(c.difficulty)}
                </span>
              </li>
              <li>
                <span className="k">Points</span>
                <span className="v">{pointsFor(c.difficulty)}</span>
              </li>
              <li>
                <span className="k">Est. time</span>
                <span className="v">{c.est_time || "—"}</span>
              </li>
              <li>
                <span className="k">Tools</span>
                <span className="v">{c.tools.join(", ")}</span>
              </li>
            </ul>
            <h4>Lab files</h4>
            <div className="files">
              {c.files.length ? (
                c.files.map((f) => (
                  <a key={f} href={`/challenges/${c.slug}/${f}`} download>
                    <IconDownload /> {f}
                  </a>
                ))
              ) : (
                <span className="kv">no downloadable files</span>
              )}
            </div>
            <h4>Submit flag</h4>
            <form action={submitFlagAction}>
              <input type="hidden" name="id" value={c.id} />
              <p className="kv" style={{ margin: "2px 0 8px" }}>
                Format <code>{"SIS{...}"}</code>
              </p>
              <input
                type="text"
                name="flag"
                placeholder="SIS{...}"
                autoComplete="off"
                spellCheck={false}
              />
              <div className="row">
                <button className="btn" type="submit">
                  Submit flag
                </button>
              </div>
              <p className="pts" style={{ marginTop: 10 }}>
                attempts: {attempts}
              </p>
            </form>
            <ResetLabButton id={c.id} title={c.title} />
          </div>

          {/* RIGHT: the detailed lab manual */}
          <div className="panel manual">
            <div className="phead">
              <span className="cnum">{c.id}</span>
              <h2>{c.title}</h2>
            </div>
            <div className="detail-sec">
              {c.category} &nbsp;&middot;&nbsp; {c.section}
            </div>
            <div className="sec-h">
              <IconShield />
              <span>Lab Scenario</span>
            </div>
            <p className="scenario">{c.scenario || c.brief}</p>
            <div className="sec-h">
              <span className="ic">
                <IconSteps />
              </span>
              <span>Solve Guide</span>
            </div>
            <div className="steps">
              {(c.steps || []).map((s, i) => (
                <div className="step" key={i}>
                  <div className="no">{i + 1}</div>
                  <div className="sbody">
                    <div className="st">{s.title}</div>
                    <div className="sd">{s.desc}</div>
                    {s.cmd ? <pre>{s.cmd}</pre> : null}
                  </div>
                </div>
              ))}
            </div>
            <details style={{ marginTop: 14 }}>
              <summary>Quick hint (one-line nudge)</summary>
              <pre>{c.hint}</pre>
            </details>
          </div>
        </div>

        <p style={{ marginTop: 14 }}>
          <a className="back" href="/">
            &larr; back to all labs
          </a>
        </p>
      </div>
    </>
  );
}
