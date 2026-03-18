import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import type {
  EntityType,
  ProjectSchema,
  RelationType,
  SchemaRefreshResult,
} from "./types";

export function getProjectSchema(projectId: string): Promise<ProjectSchema> {
  return apiGet<ProjectSchema>(`/projects/${projectId}/schema`);
}

export function refreshProjectSchema(projectId: string): Promise<SchemaRefreshResult> {
  return apiPost<SchemaRefreshResult>(`/projects/${projectId}/schema/refresh`);
}

export function createEntityType(projectId: string, typeName: string): Promise<EntityType> {
  return apiPost<EntityType, { type_name: string }>(`/projects/${projectId}/entity-types`, {
    type_name: typeName,
  });
}

export function renameEntityType(entityTypeId: string, newName: string): Promise<EntityType> {
  return apiPut<EntityType, { new_name: string }>(`/entity-types/${entityTypeId}`, {
    new_name: newName,
  });
}

export function deleteEntityType(entityTypeId: string): Promise<boolean> {
  return apiDelete(`/entity-types/${entityTypeId}`);
}

export function createRelationType(projectId: string, relationName: string): Promise<RelationType> {
  return apiPost<RelationType, { relation_name: string }>(
    `/projects/${projectId}/relation-types`,
    {
      relation_name: relationName,
    },
  );
}

export function renameRelationType(
  relationTypeId: string,
  newName: string,
): Promise<RelationType> {
  return apiPut<RelationType, { new_name: string }>(`/relation-types/${relationTypeId}`, {
    new_name: newName,
  });
}

export function deleteRelationType(relationTypeId: string): Promise<boolean> {
  return apiDelete(`/relation-types/${relationTypeId}`);
}
