import axios, { AxiosError, type AxiosRequestConfig, type AxiosResponse } from "axios";

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export class ApiClientError extends Error {
  code?: number;
  status?: number;
  details?: unknown;

  constructor(message: string, options?: { code?: number; status?: number; details?: unknown }) {
    super(message);
    this.name = "ApiClientError";
    this.code = options?.code;
    this.status = options?.status;
    this.details = options?.details;
  }
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});

function buildBackendErrorMessage(payload: Partial<ApiEnvelope<unknown>> | undefined): string {
  if (!payload) {
    return "请求失败";
  }

  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }

  return "请求失败";
}

async function unwrap<T>(request: Promise<AxiosResponse<ApiEnvelope<T>>>): Promise<T> {
  try {
    const response = await request;
    const payload = response.data;
    if (payload.code !== 0) {
      throw new ApiClientError(buildBackendErrorMessage(payload), {
        code: payload.code,
        status: response.status,
        details: payload.data,
      });
    }
    return payload.data;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiEnvelope<unknown>>;
      const payload = axiosError.response?.data;
      throw new ApiClientError(buildBackendErrorMessage(payload), {
        code: payload?.code,
        status: axiosError.response?.status,
        details: payload?.data,
      });
    }

    throw new ApiClientError("请求失败");
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "请求失败";
}

export function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return unwrap(api.get<ApiEnvelope<T>>(url, config));
}

export function apiPost<T, P = unknown>(
  url: string,
  payload?: P,
  config?: AxiosRequestConfig,
): Promise<T> {
  return unwrap(api.post<ApiEnvelope<T>>(url, payload, config));
}

export function apiPut<T, P = unknown>(
  url: string,
  payload?: P,
  config?: AxiosRequestConfig,
): Promise<T> {
  return unwrap(api.put<ApiEnvelope<T>>(url, payload, config));
}

export async function apiDelete(url: string, config?: AxiosRequestConfig): Promise<boolean> {
  await unwrap(api.delete<ApiEnvelope<null>>(url, config));
  return true;
}
