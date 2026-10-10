import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { resetPassword } from "../../../shared/api/client";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <p className="brand">Clipseek</p>
        <h1>Choose a new password</h1>
        {done ? (
          <p className="lede">
            Password updated. <Link to="/login">Sign in</Link>
          </p>
        ) : (
          <form onSubmit={onSubmit} className="stack">
            <label>
              New password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
              />
            </label>
            {error && <p className="error">{error}</p>}
            <button className="btn primary" disabled={busy || !token} type="submit">
              {busy ? "Please wait…" : "Update password"}
            </button>
            {!token && <p className="error">Missing reset token. Use the link from your email.</p>}
          </form>
        )}
      </div>
    </div>
  );
}
