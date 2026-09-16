import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SessionDialog, WhatsAppSessionManager } from "@/app/presenze/whatsapp/whatsapp-session-manager";

const mocks = vi.hoisted(() => ({
  token: vi.fn(),
  session: vi.fn(),
  start: vi.fn(),
  qr: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  getPresenzeWhatsAppSession: mocks.session,
  startPresenzeWhatsAppSession: mocks.start,
  getPresenzeWhatsAppQr: mocks.qr,
  logoutPresenzeWhatsAppSession: mocks.logout,
}));

const notCreated = { name: "default", status: "not_created", phone: null, display_name: null };
const scanning = { ...notCreated, status: "scan_qr_code" };
const working = { name: "default", status: "working", phone: "39333123", display_name: "GAIA" };

describe("WhatsApp session manager", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.token.mockReturnValue("token");
    mocks.session.mockResolvedValue(notCreated);
    mocks.start.mockResolvedValue(scanning);
    mocks.qr.mockResolvedValue({ image_data_url: "data:image/png;base64,cXI=" });
    mocks.logout.mockResolvedValue({ ...notCreated, status: "stopped" });
  });

  test("starts a session and displays the QR inside GAIA", async () => {
    mocks.session.mockResolvedValueOnce(notCreated).mockResolvedValue(scanning);
    render(<WhatsAppSessionManager />);
    fireEvent.click(screen.getByRole("button", { name: "Gestisci collegamento" }));
    expect(await screen.findByText("Non configurata")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Avvia e genera QR" }));
    expect(await screen.findByRole("img", { name: "QR per associare WhatsApp a GAIA" })).toHaveAttribute("src", "data:image/png;base64,cXI=");
    expect(mocks.start).toHaveBeenCalledWith("token");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna stato" }));
    await waitFor(() => expect(mocks.session).toHaveBeenCalledTimes(3));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("shows the linked number and requires confirmation before logout", async () => {
    mocks.session.mockResolvedValueOnce(working).mockResolvedValue({ ...notCreated, status: "stopped" });
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(<WhatsAppSessionManager />);
    fireEvent.click(screen.getByRole("button", { name: "Gestisci collegamento" }));
    expect(await screen.findByText("+39333123")).toBeInTheDocument();
    expect(screen.getByText("GAIA")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disconnetti numero" }));
    expect(mocks.logout).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Disconnetti numero" }));
    await waitFor(() => expect(mocks.logout).toHaveBeenCalledWith("token"));
    confirm.mockRestore();
  });

  test("handles status, QR and action failures without exposing secrets", async () => {
    mocks.session.mockRejectedValueOnce(new Error("WAHA offline")).mockResolvedValue(scanning);
    mocks.qr.mockRejectedValue(new Error("QR non pronto"));
    mocks.start.mockRejectedValue("errore");
    render(<WhatsAppSessionManager />);
    fireEvent.click(screen.getByRole("button", { name: "Gestisci collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("WAHA offline");
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna stato" }));
    await waitFor(() => expect(screen.getByText("QR non ancora disponibile")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Avvia e genera QR" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossibile avviare");
  });

  test("stays inert if authentication disappears", async () => {
    mocks.token.mockReturnValue(null);
    render(<WhatsAppSessionManager />);
    fireEvent.click(screen.getByRole("button", { name: "Gestisci collegamento" }));
    fireEvent.click(screen.getByRole("button", { name: "Avvia e genera QR" }));
    expect(mocks.session).not.toHaveBeenCalled();
    expect(mocks.start).not.toHaveBeenCalled();
    expect(screen.getByText("Stato non disponibile")).toBeInTheDocument();
  });

  test("renders partial linked identities", () => {
    const props = {
      qr: null, busy: false, error: null,
      onClose: vi.fn(), onRefresh: vi.fn(), onStart: vi.fn(), onLogout: vi.fn(),
    };
    const { rerender } = render(<SessionDialog {...props} session={{ ...working, display_name: null }} />);
    expect(screen.getByText("Numero collegato")).toBeInTheDocument();
    rerender(<SessionDialog {...props} session={{ ...working, phone: null }} />);
    expect(screen.getByText("Telefono disponibile")).toBeInTheDocument();
  });
});
