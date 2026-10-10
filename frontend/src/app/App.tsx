import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "../features/auth/context/AuthProvider";
import { DEV_AUTH_BYPASS } from "../features/auth/config";
import { AuthPage } from "../features/auth/pages/AuthPage";
import { HomePage } from "../features/library/pages/WorkspacePage";
import { LandingPage } from "../features/marketing/pages/LandingPage";
import { LegalPage } from "../features/legal/pages/LegalPage";
import { ResetPasswordPage } from "../features/auth/pages/ResetPasswordPage";
import "../styles/index.css";

function Gate() {
  const { token, userId } = useAuth();
  return DEV_AUTH_BYPASS || token ? <HomePage key={userId} /> : <Navigate to="/login" replace />;
}

function AuthRoute({ mode }: { mode: "login" | "register" }) {
  const { token } = useAuth();
  return token ? <Navigate to="/app" replace /> : <AuthPage key={mode} initialMode={mode} />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/privacy" element={<LegalPage kind="privacy" />} />
          <Route path="/terms" element={<LegalPage kind="terms" />} />
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthRoute mode="login" />} />
          <Route path="/signup" element={<AuthRoute mode="register" />} />
          <Route path="/app" element={<Gate />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
