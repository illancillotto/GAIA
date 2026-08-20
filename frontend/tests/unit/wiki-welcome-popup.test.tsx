import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { WikiWelcomePopup } from "@/components/wiki/WikiWelcomePopup";

describe("WikiWelcomePopup", () => {
  test("does not render the startup modal", () => {
    const { container } = render(<WikiWelcomePopup />);

    expect(container).toBeEmptyDOMElement();
  });
});
