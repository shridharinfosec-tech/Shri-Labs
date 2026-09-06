import { redirect } from "next/navigation";
import { getSessionUser } from "@/lib/auth";
import { loginAction } from "@/app/actions";

export const dynamic = "force-dynamic";

export default async function Login({
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
            <h2>Sign in</h2>
            <p className="auth-sub">Access your Module 20 cryptography labs.</p>
            {searchParams.error && <div className="msg bad">{searchParams.error}</div>}
            <form action={loginAction}>
              <label>Username</label>
              <input
                type="text"
                name="username"
                defaultValue={searchParams.u || ""}
                autoComplete="username"
                autoFocus
              />
              <label>Password</label>
              <input type="password" name="password" autoComplete="current-password" />
              <button
                className="btn"
                type="submit"
                style={{ width: "100%", marginTop: 18, justifyContent: "center" }}
              >
                Sign in
              </button>
            </form>
            <p className="auth-alt">
              New here? <a href="/register">Create an account</a>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
