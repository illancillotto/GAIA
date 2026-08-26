"use client";

import { useEffect, useRef } from "react";

export type WizardStep = 1 | 2 | 3;

export function useWizardStepFocus(step: WizardStep) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const initialRender = useRef(true);

  useEffect(() => {
    if (initialRender.current) {
      initialRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  return headingRef;
}

export function WizardSteps({ step }: { step: WizardStep }) {
  return (
    <ol
      className="mb-4 grid grid-cols-3 gap-2 text-center text-xs font-semibold"
      aria-label="Avanzamento procedura"
    >
      {["Scegli", "Descrivi", "Conferma"].map((label, index) => {
        const itemStep = (index + 1) as WizardStep;
        return (
          <li
            key={label}
            aria-current={step === itemStep ? "step" : undefined}
            className={`rounded-full px-2 py-2 ${step >= itemStep ? "bg-[#1D4E35] text-white" : "bg-gray-100 text-gray-500"}`}
          >
            {itemStep}. {label}
          </li>
        );
      })}
    </ol>
  );
}
