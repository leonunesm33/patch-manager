import { useState } from "react";

interface CopyButtonProps {
  text: string;
  /** Duration in ms to show the "Copiado!" feedback. Default: 2000 */
  feedbackDurationMs?: number;
}

/**
 * Button that copies `text` to the clipboard.
 * Shows "Copiado!" for ~2s on success, or an error message on failure.
 */
export function CopyButton({ text, feedbackDurationMs = 2000 }: CopyButtonProps) {
  const [state, setState] = useState<"idle" | "copied" | "error">("idle");

  async function handleCopy() {
    if (state !== "idle") return;
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("error");
    } finally {
      setTimeout(() => setState("idle"), feedbackDurationMs);
    }
  }

  const label =
    state === "copied" ? "Copiado!" : state === "error" ? "Erro ao copiar" : "Copiar";

  return (
    <button
      aria-label={label}
      className={state === "copied" ? "btn btn-primary" : "btn"}
      disabled={state !== "idle"}
      onClick={() => void handleCopy()}
      type="button"
    >
      {label}
    </button>
  );
}
