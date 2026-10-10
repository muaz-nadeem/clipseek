import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { forgotPassword, login, register } from "../../../shared/api/client";
import { useAuth } from "../context/AuthProvider";
import { Brand, Icon } from "../../../shared/components/Icon";

export function AuthPage({ initialMode = "login" }: { initialMode?: "login" | "register" }) {
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register" | "forgot">(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resetUrl, setResetUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    setResetUrl(null);
    try {
      if (mode === "forgot") {
        const res = await forgotPassword(email);
        setResetUrl(res.reset_url ?? null);
        setNotice(
          res.reset_url
            ? "Development mode: use this link to reset the password."
            : "If that account exists, a reset link was sent to its email.",
        );
        return;
      }
      const data = mode === "login" ? await login(email, password) : await register(email, password);
      setSession(data);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setBusy(false);
    }
  }

  const title = mode === "login" ? "Welcome back" : mode === "register" ? "Create account" : "Reset password";

  return (
    <div className="auth-layout">
      <div className="auth-main">
        <Link className="auth-brand" to="/" aria-label="Clipseek home"><Brand /></Link>
        <div className="auth-form-wrap">
        <Link className="back-link" to="/"><span aria-hidden="true">←</span> Back to home</Link>
        <p className="eyebrow">{mode === "register" ? "YOUR NEXT DISCOVERY STARTS HERE" : mode === "forgot" ? "LET’S GET YOU BACK IN" : "YOUR WORKSPACE IS WAITING"}</p>
        <h1>{title}</h1>
        <p className="lede">{mode === "register" ? "Give your footage a home. Make every moment easier to find." : mode === "forgot" ? "Enter your email and we’ll help you reset your password." : "Sign in to your library. Pick up where you left off."}</p>
        <form onSubmit={onSubmit} className="stack">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" placeholder="you@example.com" required disabled={busy} />
          </label>
          {mode !== "forgot" && (
            <div className="password-group">
              <label htmlFor="account-password">Password</label>
              <span className="password-field"><input
                id="account-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                placeholder={mode === "register" ? "At least 8 characters" : "Your password"}
                disabled={busy}
                minLength={8}
                required
              /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button></span>
            </div>
          )}
          {error && <p className="error" role="alert">{error}</p>}
          {notice && <p className="notice" role="status">{notice}</p>}
          {resetUrl && <a href={resetUrl}>Open reset link</a>}
          <button className="btn primary" disabled={busy} type="submit">
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : "Send reset link"}<Icon name="arrow" size={17} />
          </button>
        </form>
        <p className="auth-switch">{mode === "login" ? <>New to Clipseek? <Link to="/signup">Create an account</Link></> : mode === "register" ? <>Already have an account? <Link to="/login">Sign in</Link></> : <button className="linkish" onClick={() => setMode("login")}>Back to sign in</button>}</p>
        {mode !== "forgot" && (
          <button type="button" className="linkish forgot-link" disabled={busy} onClick={() => { setMode("forgot"); setError(null); setNotice(null); }}>
            Forgot password?
          </button>
        )}
        {mode === "register" && <p className="auth-terms">By creating an account, you agree to our <Link to="/terms">Terms</Link> and acknowledge our <Link to="/privacy">Privacy notice</Link>.</p>}
        </div>
        <div className="auth-bottom"><span>© {new Date().getFullYear()} Clipseek</span><span className="legal-links">
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
        </span></div>
      </div>
      <aside className="auth-visual"><img src="/city-scene.jpg" alt="City street in black and white" /><div className="auth-visual-overlay" /><div className="auth-visual-top"><span className="eyebrow">SEE YOUR FOOTAGE DIFFERENTLY</span><Icon name="film" size={25} /></div><div className="auth-visual-copy"><span className="auth-visual-tag"><Icon name="search" size={16} />A city street, a passing car, a moment.</span><h2>It’s in there.<br />Let’s find it.</h2><p>Your videos hold more than you remember.<br />Turn what you’ve captured into what you can find.</p><div className="auth-visual-footer"><span>UPLOAD. SEARCH. DISCOVER.</span><span>01 — 03</span></div></div></aside>
    </div>
  );
}
