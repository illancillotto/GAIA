import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoDeliveryPointsConfigPage from "@/app/catasto/punti-consegna-configurazione/page";

const mocks = vi.hoisted(() => ({
  getConfig: vi.fn(),
  updateConfig: vi.fn(),
  runImport: vi.fn(),
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetDeliveryPointsImportConfig: mocks.getConfig,
  catastoUpdateDeliveryPointsImportConfig: mocks.updateConfig,
  catastoImportDeliveryPointsFromConfig: mocks.runImport,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/ui/alert-banner", () => ({
  AlertBanner: ({ title, message, children }: { title: string; message?: string; children?: ReactNode }) => (
    <div>
      <span>{title}</span>
      <span>{message ?? children}</span>
    </div>
  ),
}));

describe("Catasto delivery points config page", () => {
  beforeEach(() => {
    mocks.getConfig.mockReset();
    mocks.updateConfig.mockReset();
    mocks.runImport.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token-123");
  });

  test("loads config and allows saving a new NAS path", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.updateConfig.mockResolvedValue({
      root_path: "/mnt/nas/updated",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T11:00:00Z",
    });

    render(<CatastoDeliveryPointsConfigPage />);

    const input = await screen.findByLabelText("Cartella sorgente NAS");
    expect(input).toHaveValue("/mnt/nas/current");

    fireEvent.change(input, { target: { value: "/mnt/nas/updated" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await waitFor(() => {
      expect(mocks.updateConfig).toHaveBeenCalledWith("token-123", { root_path: "/mnt/nas/updated" });
    });
    expect(screen.getByLabelText("Cartella sorgente NAS")).toHaveValue("/mnt/nas/updated");
  });

  test("runs import and renders returned stats", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockResolvedValue({
      root_path: "/mnt/nas/current",
      points_processed: 10,
      canals_processed: 2,
      meter_readings_linked: 8,
      meter_readings_unlinked: 3,
    });

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Punti processati");
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("Letture collegate")).toBeInTheDocument();
    expect(screen.getByText("/mnt/nas/current")).toBeInTheDocument();
  });

  test("shows a session error when config load has no token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("Operazione non completata");
    expect(screen.getByText("Sessione non disponibile.")).toBeInTheDocument();
    expect(mocks.getConfig).not.toHaveBeenCalled();
  });

  test("shows load errors and keeps fallback directory labels", async () => {
    mocks.getConfig.mockRejectedValue(new Error("NAS non raggiungibile"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("NAS non raggiungibile");
    expect(screen.getByText("Punti_Cons-Con_contatoti")).toBeInTheDocument();
    expect(screen.getByText("Punti_Cons-Con_Senza_contatoti")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa dal NAS" })).toBeDisabled();
  });

  test("shows generic load error for non-error failures", async () => {
    mocks.getConfig.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("Errore caricamento configurazione.");
  });

  test("saves a blank path as null and renders unsaved config metadata", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: null,
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: null,
      updated_at: null,
    });
    mocks.updateConfig.mockResolvedValue({
      root_path: null,
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: null,
      updated_at: null,
    });

    render(<CatastoDeliveryPointsConfigPage />);

    const input = await screen.findByLabelText("Cartella sorgente NAS");
    expect(input).toHaveValue("");
    expect(screen.getByText("Configurazione non ancora salvata.")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await waitFor(() => {
      expect(mocks.updateConfig).toHaveBeenCalledWith("token-123", { root_path: null });
    });
  });

  test("shows save errors and handles missing token on save", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.updateConfig.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Errore salvataggio configurazione.");

    mocks.updateConfig.mockReset();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.updateConfig).not.toHaveBeenCalled();
  });

  test("shows explicit save Error messages and null update timestamps", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: null,
    });
    mocks.updateConfig.mockRejectedValue(new Error("Path NAS non valido"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByText("admin · Mai");
    fireEvent.click(screen.getByRole("button", { name: "Salva configurazione" }));

    await screen.findByText("Path NAS non valido");
  });

  test("shows import errors and handles missing token on import", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockRejectedValue(new Error("Credenziali NAS non valide"));

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Credenziali NAS non valide");

    mocks.runImport.mockReset();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Sessione non disponibile.");
    expect(mocks.runImport).not.toHaveBeenCalled();
  });

  test("shows generic import error for non-error failures", async () => {
    mocks.getConfig.mockResolvedValue({
      root_path: "/mnt/nas/current",
      expected_with_meter_dir: "with-meter",
      expected_without_meter_dir: "without-meter",
      updated_by: "admin",
      updated_at: "2026-07-06T10:00:00Z",
    });
    mocks.runImport.mockRejectedValue("failure");

    render(<CatastoDeliveryPointsConfigPage />);

    await screen.findByDisplayValue("/mnt/nas/current");
    fireEvent.click(screen.getByRole("button", { name: "Importa dal NAS" }));

    await screen.findByText("Errore import punti di consegna.");
  });
});
