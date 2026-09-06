import { getSessionUser } from "@/lib/auth";
import { logoutAction } from "@/app/actions";

export default async function Nav() {
  const user = await getSessionUser();
  return (
    <header className="nav">
      <div className="nav-inner">
        <a href="/" className="logo-pill" title="Shridhar Infosec Solutions">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/assets/sis-logo.png" alt="Shridhar Infosec Solutions" />
        </a>
        <div className="nav-right">
          <span className="nav-title">
            CEH&nbsp;v13 &middot; Module&nbsp;20 &middot; Cryptography Lab
          </span>
          {user && (
            <span className="nav-user">
              <span className="nav-uname">{user}</span>
              <form action={logoutAction} style={{ display: "inline" }}>
                <button className="nav-logout" type="submit">
                  Logout
                </button>
              </form>
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
