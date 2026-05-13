export type TabKey = "project" | "batch" | "schema" | "qa";

export interface ModelConfig {
  id: string;
  config_type: string;
  name: string;
  base_url: string;
  api_key_masked: string;
  model_name: string;
  timeout_seconds: number;
  provider_options: Record<string, unknown> | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  extract_config_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_import_at: string | null;
}

export interface Batch {
  id: string;
  project_id: string;
  file_name: string;
  instruction: string | null;
  total_lines: number;
  valid_lines: number;
  status: string;
  success_count: number;
  request_failed_count: number;
  parse_failed_count: number;
  created_at: string;
  updated_at: string;
}

export interface SourceSummary {
  id: string;
  batch_id: string;
  line_no: number;
  input_text: string;
  request_status: string;
  parse_status: string;
  is_manual_edited: boolean;
  error_message: string | null;
}

export interface SourceDetail {
  id: string;
  batch_id: string;
  project_id: string;
  line_no: number;
  input_text: string;
  request_payload: string | null;
  raw_response: string | null;
  cleaned_output_text: string | null;
  request_status: string;
  parse_status: string;
  is_manual_edited: boolean;
  retry_count: number;
  error_message: string | null;
}

export interface Triple {
  id: string;
  project_id: string;
  batch_id: string;
  source_id: string;
  subject: string;
  subject_type: string;
  predicate: string;
  object: string;
  object_type: string;
  status: string;
  is_manual: boolean;
  imported: boolean;
}

export interface BatchProgress {
  batch_id: string;
  status: string;
  total: number;
  processed: number;
  success_count: number;
  request_failed_count: number;
  parse_failed_count: number;
}

export interface ReparseResult {
  source_id: string;
  parse_status: string;
  triple_count: number;
  error_message: string | null;
}

export interface EntityType {
  id: string;
  type_name: string;
  created_at: string;
  updated_at: string;
}

export interface RelationType {
  id: string;
  relation_name: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSchema {
  project_id: string;
  entity_types: EntityType[];
  relation_types: RelationType[];
}

export interface SchemaRefreshResult {
  entity_types: string[];
  relation_types: string[];
}

export interface GraphInitResult {
  project_id: string;
  status: string;
}

export interface GraphImportResult {
  import_log_id: string;
  mode: string;
  status: string;
  total_candidate_count: number;
  created_node_count: number;
  created_relation_count: number;
  deduplicated_count: number;
  failed_count: number;
}

export interface GraphImportLog {
  id: string;
  project_id: string;
  mode: string;
  status: string;
  total_candidate_count: number;
  created_node_count: number;
  created_relation_count: number;
  deduplicated_count: number;
  failed_count: number;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface QAEvidence {
  subject: string;
  subject_type: string;
  predicate: string;
  object: string;
  object_type: string;
  source_text: string;
}

export interface QAAskResult {
  project_id: string;
  question: string;
  answer: string;
  matched_count: number;
  evidence: QAEvidence[];
}

export interface CreateConfigPayload {
  config_type: "extract";
  name: string;
  base_url: string;
  api_key: string;
  model_name: string;
  timeout_seconds: number;
  provider_options: Record<string, unknown> | null;
}

export interface UpdateConfigPayload {
  name?: string;
  base_url?: string;
  api_key?: string;
  model_name?: string;
  timeout_seconds?: number;
  provider_options?: Record<string, unknown> | null;
}

export interface CreateProjectPayload {
  name: string;
  description: string | null;
  extract_config_id: string;
}

export interface UpdateProjectPayload {
  name?: string;
  description?: string | null;
  extract_config_id?: string;
}

export interface CreateTriplePayload {
  subject: string;
  subject_type: string;
  predicate: string;
  object: string;
  object_type: string;
}
