import { apiDelete, apiGet, apiPost } from "./client";
import type {
  CreateConfigPayload,
  CreateProjectPayload,
  ModelConfig,
  Project,
} from "./types";

export function listConfigs(): Promise<ModelConfig[]> {
  return apiGet<ModelConfig[]>("/configs");
}

export function createConfig(payload: CreateConfigPayload): Promise<ModelConfig> {
  return apiPost<ModelConfig, CreateConfigPayload>("/configs", payload);
}

export function deleteConfig(configId: string): Promise<boolean> {
  return apiDelete(`/configs/${configId}`);
}

export function listProjects(): Promise<Project[]> {
  return apiGet<Project[]>("/projects");
}

export function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiPost<Project, CreateProjectPayload>("/projects", payload);
}

export function deleteProject(projectId: string): Promise<boolean> {
  return apiDelete(`/projects/${projectId}`);
}
