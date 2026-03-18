import { apiGet, apiPost } from "./client";
import type { GraphImportLog, GraphImportResult, GraphInitResult } from "./types";

export function initGraph(projectId: string): Promise<GraphInitResult> {
  return apiPost<GraphInitResult>(`/projects/${projectId}/graph/init`);
}

export function importGraph(projectId: string): Promise<GraphImportResult> {
  return apiPost<GraphImportResult>(`/projects/${projectId}/graph/import`);
}

export function rebuildGraph(projectId: string): Promise<GraphImportResult> {
  return apiPost<GraphImportResult>(`/projects/${projectId}/graph/rebuild`);
}

export function listImportLogs(projectId: string): Promise<GraphImportLog[]> {
  return apiGet<GraphImportLog[]>(`/projects/${projectId}/graph/import-logs`);
}
