import { apiPost } from "./client";
import type { QAAskResult } from "./types";


interface AskQuestionPayload {
  question: string;
}


export function askQuestion(projectId: string, question: string): Promise<QAAskResult> {
  return apiPost<QAAskResult, AskQuestionPayload>(`/projects/${projectId}/qa/ask`, {
    question,
  });
}
