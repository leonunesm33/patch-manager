import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchMachineOperationalDetails } from "@/features/machines/api";
import { MachineOperationalDetailsPanel } from "@/features/machines/components/machine-operational-details-panel";
import type { MachineOperationalDetails } from "@/features/machines/types";
import {
  reintegrateConnectedAgent,
  requestConnectedAgentReboot,
  revokeConnectedAgent,
} from "@/features/settings/api";
import { ConfirmModal } from "@/components/common/confirm-modal";

export function MachineDetailPage() {
  const navigate = useNavigate();
  const { machineId } = useParams<{ machineId: string }>();
  const [details, setDetails] = useState<MachineOperationalDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmAction, setConfirmAction] = useState<"reboot" | "reintegrate" | "revoke" | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!machineId) {
        setError("Maquina nao informada.");
        setLoading(false);
        return;
      }
      try {
        const response = await fetchMachineOperationalDetails(machineId);
        if (!active) return;
        setDetails(response);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof Error ? err.message : "Falha ao carregar os detalhes operacionais do host.",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, [machineId]);

  async function reload() {
    if (!machineId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetchMachineOperationalDetails(machineId);
      setDetails(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Falha ao carregar os detalhes operacionais do host.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmAction() {
    if (!details?.agent_id || !confirmAction) return;
    setActionLoading(true);
    setError(null);
    try {
      if (confirmAction === "reboot") {
        await requestConnectedAgentReboot(details.agent_id);
      } else if (confirmAction === "reintegrate") {
        await reintegrateConnectedAgent(details.agent_id);
      } else {
        await revokeConnectedAgent(details.agent_id);
      }
      setConfirmAction(null);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao executar a acao do host.");
    } finally {
      setActionLoading(false);
    }
  }

  const inventoryAgentId = details?.agent_id ?? null;
  const managedByAgent = Boolean(details?.agent_id);

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <ConfirmModal
        open={confirmAction !== null}
        title={
          confirmAction === "reboot"
            ? "Solicitar reboot deste host?"
            : confirmAction === "reintegrate"
              ? "Forcar reintegracao deste host?"
              : "Revogar agente deste host?"
        }
        description={
          confirmAction === "reboot"
            ? `O host ${details?.machine.name ?? ""} recebera um comando operacional de reboot.`
            : confirmAction === "reintegrate"
              ? `O host ${details?.machine.name ?? ""} voltara para o fluxo de aprovacao do agente.`
              : `O agente associado ao host ${details?.machine.name ?? ""} perdera a credencial atual.`
        }
        confirmLabel={
          confirmAction === "reboot"
            ? "Solicitar reboot"
            : confirmAction === "reintegrate"
              ? "Forcar reintegracao"
              : "Revogar agente"
        }
        cancelLabel="Cancelar"
        confirmDisabled={actionLoading}
        onCancel={() => setConfirmAction(null)}
        onConfirm={() => void handleConfirmAction()}
      />
      <section className="hero">
        <h1 className="hero-title">Detalhe do host</h1>
        <p className="hero-copy">
          Esta visao consolida inventario, jobs, execucoes e comandos operacionais de um unico host.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn" onClick={() => navigate("/machines")} type="button">
            Voltar para maquinas
          </button>
          <button className="btn" onClick={() => void reload()} type="button">
            Atualizar
          </button>
          {managedByAgent ? (
            <>
              <button className="btn" onClick={() => setConfirmAction("reboot")} type="button">
                Solicitar reboot
              </button>
              <button className="btn" onClick={() => setConfirmAction("reintegrate")} type="button">
                Reintegrar
              </button>
              <button className="btn" onClick={() => setConfirmAction("revoke")} type="button">
                Revogar agente
              </button>
            </>
          ) : null}
        </div>
      </section>

      <MachineOperationalDetailsPanel
        details={details}
        error={error}
        inventoryAgentId={inventoryAgentId}
        loading={loading}
        title={details ? `Host ${details.machine.name}` : "Detalhes do host"}
      />
    </div>
  );
}
