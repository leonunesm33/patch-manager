import { createPortal } from "react-dom";
import { useRef, useState } from "react";

interface InfoHintProps {
  text: string;
}

/**
 * Small "?" button that shows a tooltip popover on hover/focus.
 * Uses CSS classes: info-hint, info-hint-button, info-hint-popover-fixed.
 */
export function InfoHint({ text }: InfoHintProps) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);

  function show() {
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setPos({ top: rect.top - 10, left: rect.left + rect.width / 2 });
    }
    setVisible(true);
  }

  return (
    <span className="info-hint">
      <button
        ref={btnRef}
        aria-label={text}
        className="info-hint-button"
        onMouseEnter={show}
        onMouseLeave={() => setVisible(false)}
        onFocus={show}
        onBlur={() => setVisible(false)}
        type="button"
      >
        ?
      </button>
      {visible
        ? createPortal(
            <span className="info-hint-popover-fixed" style={{ top: pos.top, left: pos.left }}>
              {text}
            </span>,
            document.body,
          )
        : null}
    </span>
  );
}
