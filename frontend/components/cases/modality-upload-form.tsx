"use client";

import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  uploadFieldDescribedBy,
  uploadFieldIds,
} from "@/lib/a11y/upload-field";
import {
  attachCaseModality,
  createIdempotencyKey,
  type AttachableModality,
  type CaseDetail,
} from "@/lib/cases/api";

const MODALITY_META: Record<
  AttachableModality,
  { label: string; hint: string; accept: string }
> = {
  video: {
    label: "Arquivo de vídeo",
    hint: "Clip de vídeo (ex.: .avi, .mp4).",
    accept: "video/*,.avi,.mp4",
  },
  audio: {
    label: "Arquivo de áudio",
    hint: "Clip de áudio ≤60s (ex.: .wav).",
    accept: "audio/*,.wav",
  },
  prescriptions: {
    label: "CSV de prescrições",
    hint: "Arquivo CSV sintético de prescriptions.",
    accept: ".csv,text/csv",
  },
};

type ModalityUploadFormProps = {
  caseId: string;
  modality: AttachableModality;
  onAttached: (detail: CaseDetail) => void;
};

export function ModalityUploadForm({
  caseId,
  modality,
  onAttached,
}: ModalityUploadFormProps) {
  const ids = uploadFieldIds(modality);
  const meta = MODALITY_META[modality];
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (selected: File) => {
      const key = createIdempotencyKey();
      return attachCaseModality(caseId, modality, selected, key);
    },
    onSuccess: (detail) => {
      setSuccess(`Modalidade ${modality} anexada.`);
      setError(null);
      setFile(null);
      onAttached(detail);
    },
    onError: (err) => {
      setSuccess(null);
      setError((err as Error).message);
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (!file) {
      setError(`Selecione um arquivo para ${modality}.`);
      return;
    }
    mutation.mutate(file);
  }

  const describedBy = uploadFieldDescribedBy({
    hintId: ids.hintId,
    errorId: error ? ids.errorId : null,
    successId: success ? ids.successId : null,
  });

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-3 rounded-md border border-border p-3"
      noValidate
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor={ids.inputId}>{meta.label}</Label>
        <p id={ids.hintId} className="text-xs text-muted-foreground">
          {meta.hint}
        </p>
        <Input
          id={ids.inputId}
          name="file"
          type="file"
          accept={meta.accept}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
            setSuccess(null);
          }}
          required
        />
        {error ? (
          <p id={ids.errorId} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {success ? (
          <p
            id={ids.successId}
            role="status"
            className="text-sm text-muted-foreground"
          >
            {success}
          </p>
        ) : null}
      </div>
      <Button type="submit" size="sm" disabled={mutation.isPending}>
        {mutation.isPending ? "Enviando…" : `Anexar ${modality}`}
      </Button>
    </form>
  );
}
