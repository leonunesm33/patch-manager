import type { ReactNode } from "react";

type ConfirmModalProps = {
  open: boolean;
  title: string;
  description: string;
  children?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal({
  open,
  title,
  description,
  children,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  confirmDisabled = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <p className="eyebrow">Confirmacao</p>
        <h3 className="modal-title">{title}</h3>
        <p className="modal-copy">{description}</p>
        {children ? <div className="modal-extra">{children}</div> : null}
        <div className="modal-actions">
          <button className="btn" type="button" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button className="btn btn-danger" disabled={confirmDisabled} type="button" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
