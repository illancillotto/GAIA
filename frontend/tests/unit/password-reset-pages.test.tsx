import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import ForgotPasswordPage from "@/app/auth/password-dimenticata/page";
import ResetPasswordPage from "@/app/auth/reset-password/[token]/page";
import LoginPage from "@/app/login/page";

const mocks = vi.hoisted(() => ({
  confirmPasswordReset: vi.fn(),
  getApiBaseUrl: vi.fn(() => "/api"),
  getAuthProviders: vi.fn(),
  getClientDeviceLabel: vi.fn(),
  getPasswordResetInfo: vi.fn(),
  getStoredAccessToken: vi.fn(),
  getStoredClientDeviceId: vi.fn(),
  login: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
  replace: vi.fn(),
  requestPasswordReset: vi.fn(),
  routeToken: "reset-token" as string | string[] | undefined,
  searchParams: new URLSearchParams(),
  setStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  getApiBaseUrl: mocks.getApiBaseUrl,
  getAuthProviders: mocks.getAuthProviders,
  login: mocks.login,
}));

vi.mock("@/lib/password-reset-api", () => ({
  confirmPasswordReset: mocks.confirmPasswordReset,
  getPasswordResetInfo: mocks.getPasswordResetInfo,
  requestPasswordReset: mocks.requestPasswordReset,
}));

vi.mock("@/lib/auth", () => ({
  getClientDeviceLabel: mocks.getClientDeviceLabel,
  getStoredAccessToken: mocks.getStoredAccessToken,
  getStoredClientDeviceId: mocks.getStoredClientDeviceId,
  setStoredAccessToken: mocks.setStoredAccessToken,
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: mocks.routeToken }),
  useRouter: () => ({ push: mocks.push, refresh: mocks.refresh, replace: mocks.replace }),
  useSearchParams: () => mocks.searchParams,
}));

describe("password reset pages", () => {
  beforeEach(() => {
    mocks.confirmPasswordReset.mockReset();
    mocks.getApiBaseUrl.mockReturnValue("/api");
    mocks.getAuthProviders.mockReset();
    mocks.getClientDeviceLabel.mockReset();
    mocks.getClientDeviceLabel.mockReturnValue("Linux · it-IT");
    mocks.getPasswordResetInfo.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredClientDeviceId.mockReset();
    mocks.getStoredClientDeviceId.mockReturnValue("browser-1");
    mocks.login.mockReset();
    mocks.push.mockReset();
    mocks.refresh.mockReset();
    mocks.replace.mockReset();
    mocks.requestPasswordReset.mockReset();
    mocks.routeToken = "reset-token";
    mocks.searchParams = new URLSearchParams();
    mocks.setStoredAccessToken.mockReset();
  });

  test("renders forgot password link on login", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.getAuthProviders.mockResolvedValue({ password: true, google: false });

    render(<LoginPage />);

    expect(await screen.findByRole("link", { name: "Password dimenticata?" })).toHaveAttribute(
      "href",
      "/auth/password-dimenticata",
    );
  });

  test("handles login page token redirects, provider branches and submit states", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce("stored-token");
    mocks.getAuthProviders.mockRejectedValueOnce(new Error("providers down"));
    render(<LoginPage />);
    expect(mocks.replace).toHaveBeenCalledWith("/");
    cleanup();

    mocks.searchParams = new URLSearchParams("access_token=google-token");
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    mocks.getAuthProviders.mockResolvedValueOnce({ password: true, google: true });
    render(<LoginPage />);
    await waitFor(() => expect(mocks.setStoredAccessToken).toHaveBeenCalledWith("google-token"));
    expect(mocks.replace).toHaveBeenCalledWith("/");
    expect(mocks.refresh).toHaveBeenCalled();
    cleanup();

    mocks.getAuthProviders.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.searchParams = new URLSearchParams("auth_error=errore-google");
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.getAuthProviders.mockResolvedValue({ password: true, google: true });
    render(<LoginPage />);
    expect(await screen.findByText("errore-google")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Accedi con Google/ })).toHaveAttribute(
      "href",
      "/api/auth/google/start?device_id=browser-1&device_label=Linux+%C2%B7+it-IT",
    );
  });

  test("submits login form and handles validation and failures", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.getAuthProviders.mockResolvedValue({ password: true, google: false });
    mocks.login.mockRejectedValueOnce(new Error("credenziali errate")).mockResolvedValueOnce({ access_token: "jwt", token_type: "bearer" });

    render(<LoginPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Accedi alla piattaforma" }));
    expect(screen.getByText("Compila username o email e password per continuare.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Username o email"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "bad-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Mostra password" }));
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: "Accedi alla piattaforma" }));
    expect(await screen.findByText("credenziali errate")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Accedi alla piattaforma" }));
    await waitFor(() => expect(mocks.setStoredAccessToken).toHaveBeenCalledWith("jwt"));
    expect(mocks.push).toHaveBeenCalledWith("/");
    expect(mocks.refresh).toHaveBeenCalled();
  });

  test("shows generic login error for non-error failures", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    mocks.getAuthProviders.mockResolvedValue({ password: true, google: false });
    mocks.login.mockRejectedValueOnce("plain failure");

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Username o email"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Accedi alla piattaforma" }));

    expect(await screen.findAllByText("Accesso non riuscito")).toHaveLength(2);
  });

  test("requests a password reset email with generic response", async () => {
    mocks.requestPasswordReset.mockResolvedValue({
      message: "Se l'account esiste ed e attivo, riceverai una mail.",
    });

    render(<ForgotPasswordPage />);
    fireEvent.click(screen.getByRole("button", { name: "Invia link di ripristino" }));
    expect(screen.getByText("Inserisci username o email.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Username o email"), { target: { value: "admin@example.local" } });
    fireEvent.click(screen.getByRole("button", { name: "Invia link di ripristino" }));

    await waitFor(() => expect(mocks.requestPasswordReset).toHaveBeenCalledWith("admin@example.local"));
    expect(screen.getByText("Se l'account esiste ed e attivo, riceverai una mail.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Torna al login" })).toHaveAttribute("href", "/login");
  });

  test("shows forgot password request errors", async () => {
    mocks.requestPasswordReset.mockRejectedValue(new Error("SMTP non configurato"));

    render(<ForgotPasswordPage />);
    fireEvent.change(screen.getByLabelText("Username o email"), { target: { value: "admin" } });
    fireEvent.click(screen.getByRole("button", { name: "Invia link di ripristino" }));

    expect(await screen.findByText("SMTP non configurato")).toBeInTheDocument();
  });

  test("shows generic forgot password error for non-error failures", async () => {
    mocks.requestPasswordReset.mockRejectedValue("plain failure");

    render(<ForgotPasswordPage />);
    fireEvent.change(screen.getByLabelText("Username o email"), { target: { value: "admin" } });
    fireEvent.click(screen.getByRole("button", { name: "Invia link di ripristino" }));

    expect(await screen.findAllByText("Richiesta non riuscita")).toHaveLength(2);
  });

  test("loads reset token info, validates passwords and confirms reset", async () => {
    mocks.getPasswordResetInfo.mockResolvedValue({
      username: "admin",
      email: "admin@example.local",
      full_name: null,
      expires_at: "2026-07-27T10:00:00+00:00",
    });
    mocks.confirmPasswordReset.mockResolvedValue({
      username: "admin",
      message: "Password aggiornata",
    });

    render(<ResetPasswordPage />);
    expect(await screen.findByText(/Account/)).toBeInTheDocument();
    expect(mocks.getPasswordResetInfo).toHaveBeenCalledWith("reset-token");

    fireEvent.change(screen.getByLabelText("Nuova password"), { target: { value: "secret123" } });
    fireEvent.change(screen.getByLabelText("Conferma password"), { target: { value: "different123" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna password" }));
    expect(screen.getByText("Le password non coincidono")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Conferma password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Nuova password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna password" }));
    expect(screen.getByText("La password deve essere di almeno 8 caratteri")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nuova password"), { target: { value: "new-secret123" } });
    fireEvent.change(screen.getByLabelText("Conferma password"), { target: { value: "new-secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna password" }));

    await waitFor(() => expect(mocks.confirmPasswordReset).toHaveBeenCalledWith("reset-token", "new-secret123"));
    expect(screen.getByText("Password aggiornata")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Vai al login" }));
    expect(mocks.push).toHaveBeenCalledWith("/login");
  });

  test("shows reset token load and submit errors", async () => {
    mocks.getPasswordResetInfo.mockRejectedValueOnce(new Error("Link non valido o scaduto"));
    const { unmount } = render(<ResetPasswordPage />);
    expect(await screen.findByText("Link non valido o scaduto")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Richiedi un nuovo link" })).toHaveAttribute("href", "/auth/password-dimenticata");
    unmount();

    mocks.getPasswordResetInfo.mockResolvedValueOnce({
      username: "admin",
      email: "admin@example.local",
      full_name: null,
      expires_at: "2026-07-27T10:00:00+00:00",
    });
    mocks.confirmPasswordReset.mockRejectedValueOnce(new Error("token usato"));
    render(<ResetPasswordPage />);
    await screen.findByText(/admin@example.local/);
    fireEvent.change(screen.getByLabelText("Nuova password"), { target: { value: "new-secret123" } });
    fireEvent.change(screen.getByLabelText("Conferma password"), { target: { value: "new-secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna password" }));
    expect(await screen.findByText("token usato")).toBeInTheDocument();
  });

  test("covers reset token array, missing token and generic failure branches", async () => {
    mocks.routeToken = ["array-token"];
    mocks.getPasswordResetInfo.mockResolvedValueOnce({
      username: "admin",
      email: "admin@example.local",
      full_name: null,
      expires_at: "2026-07-27T10:00:00+00:00",
    });
    const { unmount } = render(<ResetPasswordPage />);
    await waitFor(() => expect(mocks.getPasswordResetInfo).toHaveBeenCalledWith("array-token"));
    unmount();

    mocks.routeToken = undefined;
    render(<ResetPasswordPage />);
    expect(screen.getByText("Verifica link in corso...")).toBeInTheDocument();
    expect(mocks.getPasswordResetInfo).toHaveBeenCalledTimes(1);
    cleanup();

    mocks.routeToken = "reset-token";
    mocks.getPasswordResetInfo.mockRejectedValueOnce("plain load failure");
    render(<ResetPasswordPage />);
    expect(await screen.findAllByText("Link non valido")).toHaveLength(2);
    cleanup();

    mocks.getPasswordResetInfo.mockResolvedValueOnce({
      username: "admin",
      email: "admin@example.local",
      full_name: null,
      expires_at: "2026-07-27T10:00:00+00:00",
    });
    mocks.confirmPasswordReset.mockRejectedValueOnce("plain submit failure");
    render(<ResetPasswordPage />);
    await screen.findByText(/admin@example.local/);
    fireEvent.change(screen.getByLabelText("Nuova password"), { target: { value: "new-secret123" } });
    fireEvent.change(screen.getByLabelText("Conferma password"), { target: { value: "new-secret123" } });
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna password" }));
    expect(await screen.findAllByText("Ripristino non riuscito")).toHaveLength(2);
  });
});
