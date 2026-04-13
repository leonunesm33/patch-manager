import { useEffect, useRef, useState } from "react";

type ActionMenuItem = {
  label: string;
  onSelect: () => void;
  disabled?: boolean;
  tone?: "default" | "danger";
};

type ActionMenuProps = {
  label?: string;
  items: ActionMenuItem[];
};

export function ActionMenu({ label = "Abrir acoes", items }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  return (
    <div className="action-menu" ref={rootRef}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={label}
        className="action-menu-trigger"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        ...
      </button>
      {open ? (
        <div className="action-menu-popover" role="menu">
          {items.map((item) => (
            <button
              className={`action-menu-item ${item.tone === "danger" ? "danger" : ""}`}
              disabled={item.disabled}
              key={item.label}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
              role="menuitem"
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
