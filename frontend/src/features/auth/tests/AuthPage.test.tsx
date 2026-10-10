import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../../../shared/api/client";
import { AuthPage } from "../pages/AuthPage";

vi.mock("../../../shared/api/client", () => ({
  forgotPassword: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));

vi.mock("../context/AuthProvider", () => ({
  useAuth: () => ({ setSession: vi.fn() }),
}));

function requestReset() {
  render(
    <MemoryRouter>
      <AuthPage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Forgot password?" }));
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
  fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
}

describe("AuthPage forgot password", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows the development reset link when the API returns one", async () => {
    const url = "http://127.0.0.1:5173/reset-password?token=abc";
    vi.mocked(api.forgotPassword).mockResolvedValue({ ok: true, reset_url: url });
    requestReset();

    const link = await screen.findByRole("link", { name: "Open reset link" });
    expect(link.getAttribute("href")).toBe(url);
    expect(api.forgotPassword).toHaveBeenCalledWith("a@b.com");
  });

  it("shows only the generic notice when no link is returned", async () => {
    vi.mocked(api.forgotPassword).mockResolvedValue({ ok: true });
    requestReset();

    expect(await screen.findByText(/a reset link was sent to its email/)).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Open reset link" })).toBeNull();
  });

  it("registers an account and opens its workspace", async () => {
    vi.mocked(api.register).mockResolvedValue({ access_token: "access", refresh_token: "refresh", token_type: "bearer", user_id: 9, email: "new@example.com" });
    render(<MemoryRouter initialEntries={["/signup"]}><Routes><Route path="/signup" element={<AuthPage initialMode="register" />} /><Route path="/app" element={<h1>Your workspace</h1>} /></Routes></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("heading", { name: "Your workspace" })).toBeTruthy();
    expect(api.register).toHaveBeenCalledWith("new@example.com", "longpassword");
  });

  it("keeps failed login on the form and displays the server error", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("Invalid email or password"));
    render(<MemoryRouter><AuthPage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrongpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Invalid email or password");
  });
});
