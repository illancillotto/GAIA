"use client";

import { useCallback, useRef } from "react";

// Callback ref for an overlay close button: when the button mounts it records the
// element that had focus (the opener) and focuses the button; when it unmounts it
// returns focus to the recorded opener. Use one instance per overlay.
export function useOverlayCloseButtonRef() {
  const openerRef = useRef<HTMLElement | null>(null);

  return useCallback((closeButton: HTMLButtonElement | null) => {
    if (closeButton) {
      openerRef.current = document.activeElement as HTMLElement | null;
      closeButton.focus();
    } else {
      openerRef.current?.focus();
    }
  }, []);
}
