import { apiGet, apiPost, apiPut, apiDelete } from "./client";
import type {
  Batch,
  BatchProgress,
  ReparseResult,
  SourceDetail,
  SourceSummary,
  Triple,
  CreateTriplePayload,
} from "./types";

export function uploadBatch(projectId: string, file: File): Promise<Batch> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPost<Batch>(`/projects/${projectId}/batches/upload`, formData);
}

export function listBatches(projectId: string): Promise<Batch[]> {
  return apiGet<Batch[]>(`/projects/${projectId}/batches`);
}

export function listBatchSources(batchId: string): Promise<SourceSummary[]> {
  return apiGet<SourceSummary[]>(`/batches/${batchId}/sources`);
}

export function startExtract(batchId: string, instruction: string): Promise<{ batch_id: string; status: string }> {
  return apiPost<{ batch_id: string; status: string }, { instruction: string }>(
    `/batches/${batchId}/extract`,
    { instruction },
  );
}

export function getBatchProgress(batchId: string): Promise<BatchProgress> {
  return apiGet<BatchProgress>(`/batches/${batchId}/progress`);
}

export function retryFailed(batchId: string): Promise<{ batch_id: string; status: string; queued?: number }> {
  return apiPost<{ batch_id: string; status: string; queued?: number }>(
    `/batches/${batchId}/retry-failed`,
  );
}

export function retrySource(sourceId: string): Promise<{ batch_id: string; status: string; queued?: number }> {
  return apiPost<{ batch_id: string; status: string; queued?: number }>(`/sources/${sourceId}/retry`);
}

export function getSourceDetail(sourceId: string): Promise<SourceDetail> {
  return apiGet<SourceDetail>(`/sources/${sourceId}`);
}

export function updateRawResponse(sourceId: string, rawResponse: string): Promise<SourceDetail> {
  return apiPut<SourceDetail, { raw_response: string }>(`/sources/${sourceId}/raw-response`, {
    raw_response: rawResponse,
  });
}

export function reparseSource(sourceId: string): Promise<ReparseResult> {
  return apiPost<ReparseResult>(`/sources/${sourceId}/reparse`);
}

export function listSourceTriples(sourceId: string): Promise<Triple[]> {
  return apiGet<Triple[]>(`/sources/${sourceId}/triples`);
}

export function createSourceTriple(sourceId: string, payload: CreateTriplePayload): Promise<Triple> {
  return apiPost<Triple, CreateTriplePayload>(`/sources/${sourceId}/triples`, payload);
}

export function updateTriple(tripleId: string, payload: CreateTriplePayload): Promise<Triple> {
  return apiPut<Triple, CreateTriplePayload>(`/triples/${tripleId}`, payload);
}

export function deleteTriple(tripleId: string): Promise<boolean> {
  return apiDelete(`/triples/${tripleId}`);
}
