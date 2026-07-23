"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  formatPatientLabel,
  formatSensitiveLabelAnnouncement,
  revealSensitiveLabel,
  type Patient,
} from "@/lib/patients/api";

type SensitiveLabelRevealProps = {
  patient: Patient;
};

/**
 * Reveal/remask do Rótulo Sensível com confirmação, audit (API) e anúncio SR.
 */
export function SensitiveLabelReveal({ patient }: SensitiveLabelRevealProps) {
  const [confirming, setConfirming] = useState(false);
  const [plaintext, setPlaintext] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");

  const revealMutation = useMutation({
    mutationFn: () => revealSensitiveLabel(patient.id),
    onSuccess: (revealed) => {
      setPlaintext(revealed.sensitiveLabel);
      setConfirming(false);
      setError(null);
      setAnnouncement(
        formatSensitiveLabelAnnouncement("revealed", revealed.sensitiveLabel),
      );
    },
    onError: (err) => {
      setError((err as Error).message);
      setConfirming(false);
    },
  });

  function remask() {
    setPlaintext(null);
    setConfirming(false);
    setError(null);
    setAnnouncement(formatSensitiveLabelAnnouncement("masked"));
  }

  if (!patient.hasSensitiveLabel) {
    return (
      <section aria-labelledby="rotulo-sensivel-heading" className="text-sm">
        <h2
          id="rotulo-sensivel-heading"
          className="text-muted-foreground font-normal"
        >
          Rótulo Sensível
        </h2>
        <p className="font-medium">—</p>
      </section>
    );
  }

  const display = plaintext ?? formatPatientLabel(patient);

  return (
    <section
      aria-labelledby="rotulo-sensivel-heading"
      className="flex flex-col gap-2 text-sm"
    >
      <h2
        id="rotulo-sensivel-heading"
        className="text-muted-foreground font-normal"
      >
        Rótulo Sensível
      </h2>
      <p className="font-medium">{display}</p>

      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {plaintext ? (
        <Button type="button" variant="outline" size="sm" onClick={remask}>
          Remascarar
        </Button>
      ) : confirming ? (
        <div
          role="group"
          aria-label="Confirmar revelação do Rótulo Sensível"
          className="flex flex-wrap items-center gap-2"
        >
          <p className="text-sm text-muted-foreground">
            A revelação será auditada. Continuar?
          </p>
          <Button
            type="button"
            size="sm"
            disabled={revealMutation.isPending}
            onClick={() => revealMutation.mutate()}
          >
            {revealMutation.isPending ? "Revelando…" : "Confirmar revelação"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setConfirming(false)}
          >
            Cancelar
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-fit"
          onClick={() => {
            setError(null);
            setConfirming(true);
          }}
        >
          Revelar rótulo
        </Button>
      )}
    </section>
  );
}
