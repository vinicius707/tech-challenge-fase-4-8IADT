export type UploadFieldIds = {
  inputId: string;
  hintId: string;
  errorId: string;
  successId: string;
};

export function uploadFieldIds(fieldKey: string): UploadFieldIds {
  const base = `upload-${fieldKey}`;
  return {
    inputId: base,
    hintId: `${base}-hint`,
    errorId: `${base}-error`,
    successId: `${base}-success`,
  };
}

export function uploadFieldDescribedBy(options: {
  hintId: string;
  errorId?: string | null;
  successId?: string | null;
}): string {
  const parts = [options.hintId];
  if (options.errorId) parts.push(options.errorId);
  else if (options.successId) parts.push(options.successId);
  return parts.join(" ");
}
