// Explicit development opt-in only. Production builds always require authentication.
export const DEV_AUTH_BYPASS =
  import.meta.env.DEV && import.meta.env.VITE_DEV_AUTH_BYPASS === "1";
