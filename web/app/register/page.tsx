import { redirect } from "next/navigation";
import { getSessionUser } from "@/lib/auth";
import { registerAction } from "@/app/actions";

export const dynamic = "force-dynamic";

export default async function Register({
  searchParams,
}: {
  searchParams: { error?: string; u?: string };
}) {
  if (await getSessionUser()) redirect("/");
  return (
    <>
      <header className="nav">
        <div className="nav-inner" style={{ justifyContent: "center" }}>
          <span className="logo-pill">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/assets/sis-logo.png" alt="Shridhar Infosec Solutions" />
          </span>
        </div>
      </header>
      <div className="wrap">
        <div className="auth-wrap">
          <div className="auth-card">
            <h2>Create your account</h2>
            <p className="auth-sub">Pick a username and password to track your lab progress.</p>
            {searchParams.error && <div className="msg bad">{searchParams.error}</div>}
            <form action={registerAction}>
              <label>
                Username{" "}
                <span className="hintlabel">(3&ndash;30 chars: letters, numbers, spaces)</span>
              </label>
              <input
                type="text"
                name="username"
                defaultValue={searchParams.u || ""}
                autoComplete="username"
                autoFocus
              />
              <label>
                Password <span className="hintlabel">(min 6 characters)</span>
              </label>
              <input type="password" name="password" autoComplete="new-password" />
              <label>Confirm password</label>
              <input type="password" name="confirm" autoComplete="new-password" />
              <button
                className="btn"
                type="submit"
                style={{ width: "100%", marginTop: 18, justifyContent: "center" }}
              >
                Create account
              </button>
            </form>
            <p className="auth-alt">
              Already have an account? <a href="/login">Sign in</a>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
