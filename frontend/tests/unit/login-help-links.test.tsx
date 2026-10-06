import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import { LoginHelpLinks } from "@/components/auth/login-help-links";
import { GAIA_CA_DOWNLOAD_BASE, GAIA_CA_SHA256 } from "@/lib/gaia-ca";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("login certificate downloads", () => {
  test("shows versioned downloads only after the matching public bundle is available", async () => {
    const request = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ sha256: GAIA_CA_SHA256 }),
    });
    vi.stubGlobal("fetch", request);
    const view = render(<LoginHelpLinks />);
    expect(screen.getByRole("link", { name: "Password dimenticata?" })).toHaveAttribute("href", "/auth/password-dimenticata");
    expect(await screen.findByRole("region", { name: "Certificato HTTPS GAIA" })).toBeInTheDocument();
    for (const [label, filename] of [
      ["Windows Intel/AMD (.exe)", "CBO-CA-GAIA-Windows-amd64.exe"],
      ["Windows ARM64 (.exe)", "CBO-CA-GAIA-Windows-arm64.exe"],
      ["Pacchetto Linux e macOS", "GAIA-CA-client.tar.gz"],
      ["Guida di installazione", "GUIDA-CLIENT.txt"],
    ]) {
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", `${GAIA_CA_DOWNLOAD_BASE}/${filename}`);
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("download");
    }
    expect(screen.getByText(`SHA-256: ${GAIA_CA_SHA256}`)).toBeInTheDocument();
    expect(screen.getByText(/Confronta l’impronta con il CED/)).toBeInTheDocument();
    expect(screen.getByText(/non sono firmati Authenticode/)).toBeInTheDocument();
    const options = request.mock.calls[0][1];
    expect(request).toHaveBeenCalledWith("/gaia-ca/manifest.json", { signal: options.signal, cache: "no-store" });
    expect(options.signal.aborted).toBe(false);
    view.unmount();
    expect(options.signal.aborted).toBe(true);
  });

  test.each([{}, { sha256: "different-ca" }, null])("hides downloads for an absent or different CA manifest %j", async (manifest) => {
    const json = vi.fn().mockResolvedValue(manifest);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json }));
    render(<LoginHelpLinks />);
    await waitFor(() => expect(json).toHaveBeenCalled());
    expect(screen.queryByRole("region", { name: "Certificato HTTPS GAIA" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Password dimenticata?" })).toBeInTheDocument();
  });

  test("a missing bundle does not break password recovery", async () => {
    const json = vi.fn();
    const request = vi.fn().mockResolvedValue({ ok: false, json });
    vi.stubGlobal("fetch", request);
    render(<LoginHelpLinks />);
    await waitFor(() => expect(request).toHaveBeenCalled());
    expect(json).not.toHaveBeenCalled();
    expect(screen.queryByRole("region", { name: "Certificato HTTPS GAIA" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Password dimenticata?" })).toBeInTheDocument();
  });

  test.each(["network", "json"])("download discovery failure remains isolated from login: %s", async (failure) => {
    const request = vi.fn();
    if (failure === "network") {
      request.mockRejectedValue(new Error("network unavailable"));
    } else {
      request.mockResolvedValue({ ok: true, json: async () => { throw new Error("invalid manifest"); } });
    }
    vi.stubGlobal("fetch", request);
    render(<LoginHelpLinks />);
    await waitFor(() => expect(request).toHaveBeenCalled());
    expect(screen.queryByRole("region", { name: "Certificato HTTPS GAIA" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Password dimenticata?" })).toBeInTheDocument();
  });
});
