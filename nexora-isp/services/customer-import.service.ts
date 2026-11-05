import { apiBlob, apiRequest } from "@/services/api-client";

export type ImportRowValues = Record<string, string>;

export interface ImportPreviewRow {
  row: number;
  valid: boolean;
  errors: string[];
  values: ImportRowValues;
}

export interface ImportPreview {
  total_rows: number;
  valid_count: number;
  invalid_count: number;
  rows: ImportPreviewRow[];
}

export interface ImportBatch {
  id: string;
  file_name: string;
  total_rows: number;
  imported_count: number;
  skipped_count: number;
  create_on_router: boolean;
  errors: { row: number; errors: string[] }[];
  created_by_name: string;
  created_at: string;
}

function fileForm(file: File, extra: Record<string, string> = {}) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(extra).forEach(([key, value]) => form.append(key, value));
  return form;
}

export const customerImportService = {
  downloadTemplate(): Promise<Blob> {
    return apiBlob("/customers/import/template/");
  },

  preview(file: File): Promise<ImportPreview> {
    return apiRequest<ImportPreview>("/customers/import/preview/", {
      method: "POST",
      body: fileForm(file),
      timeoutMs: 120_000,
    });
  },

  run(file: File, createOnRouter: boolean): Promise<ImportBatch> {
    return apiRequest<ImportBatch>("/customers/import/", {
      method: "POST",
      body: fileForm(file, { create_on_router: createOnRouter ? "true" : "false" }),
      timeoutMs: 300_000,
    });
  },

  history(): Promise<ImportBatch[]> {
    return apiRequest<ImportBatch[]>("/customers/import/history/");
  },
};
