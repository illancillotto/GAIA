import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, test } from "vitest";
import GisLayerControls from "@/components/catasto/gis/GisLayerControls";

function Controls() {
  const [active, setActive] = useState(false);
  const [opacity, setOpacity] = useState(0.5);
  return <GisLayerControls showDistretti={active} setShowDistretti={setActive} showDistrettiFill={active} setShowDistrettiFill={setActive} showParticelleFill={active} setShowParticelleFill={setActive} showDeliveryPoints={active} setShowDeliveryPoints={setActive} highlightSelected={active} setHighlightSelected={setActive} distrettiOpacity={opacity} setDistrettiOpacity={setOpacity} particelleOpacity={opacity} setParticelleOpacity={setOpacity} />;
}

test("shares accessible layer toggles and opacity controls between GIS consoles", () => {
  render(<Controls />);
  for (const label of ["Distretti", "Aree colorate", "Riempimento particelle", "Punti consegna", "Evidenzia sel."]) {
    const button = screen.getByRole("button", { name: label });
    expect(button).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "false");
  }
  fireEvent.change(screen.getByRole("slider", { name: "Opacità aree distretto" }), { target: { value: "0.75" } });
  expect(screen.getAllByText("75%")).toHaveLength(2);
  fireEvent.change(screen.getByRole("slider", { name: "Opacità particelle" }), { target: { value: "0.25" } });
  expect(screen.getAllByText("25%")).toHaveLength(2);
});
