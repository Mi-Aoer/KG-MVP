import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  createSourceTriple,
  deleteTriple,
  getBatchProgress,
  getSourceDetail,
  listBatches,
  listBatchSources,
  listSourceTriples,
  reparseSource,
  retryFailed,
  retrySource,
  startExtract,
  updateRawResponse,
  updateTriple,
  uploadBatch,
} from "./api/batch";
import { getErrorMessage } from "./api/client";
import {
  importGraph,
  initGraph,
  listImportLogs,
  rebuildGraph,
} from "./api/graph";
import {
  createConfig,
  createProject,
  deleteConfig,
  deleteProject,
  listConfigs,
  listProjects,
  updateConfig,
  updateProject,
} from "./api/project";
import {
  createEntityType,
  createRelationType,
  deleteEntityType,
  deleteRelationType,
  getProjectSchema,
  refreshProjectSchema,
  renameEntityType,
  renameRelationType,
} from "./api/schema";
import type {
  Batch,
  BatchProgress,
  CreateTriplePayload,
  GraphImportLog,
  ModelConfig,
  Project,
  ProjectSchema,
  SourceDetail,
  SourceSummary,
  TabKey,
  Triple,
} from "./api/types";
import {
  buildDemoConfigDraft,
  buildDemoProjectDraft,
  DEMO_INSTRUCTION,
  DEMO_SAMPLE_FILE_HINT,
} from "./demoDefaults";
import "./App.css";

interface NoticeState {
  tone: "success" | "error";
  text: string;
}

interface ConfigFormState {
  name: string;
  baseUrl: string;
  apiKey: string;
  modelName: string;
  timeoutSeconds: string;
  providerOptionsText: string;
}

interface ProjectFormState {
  name: string;
  description: string;
  extractConfigId: string;
}

interface TripleFormState {
  subject: string;
  subjectType: string;
  predicate: string;
  object: string;
  objectType: string;
}

function createEmptyTripleForm(): TripleFormState {
  return {
    subject: "",
    subjectType: "",
    predicate: "",
    object: "",
    objectType: "",
  };
}

function buildTriplePayload(form: TripleFormState): CreateTriplePayload {
  return {
    subject: form.subject.trim(),
    subject_type: form.subjectType.trim(),
    predicate: form.predicate.trim(),
    object: form.object.trim(),
    object_type: form.objectType.trim(),
  };
}

function parseProviderOptionsText(text: string): Record<string, unknown> | null {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = JSON.parse(trimmed);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("扩展参数必须是 JSON 对象，或留空。");
  }
  return parsed as Record<string, unknown>;
}

function stringifyProviderOptions(value: Record<string, unknown> | null): string {
  if (!value) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}

function formatTime(value: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    hour12: false,
  });
}

function truncateText(value: string, limit = 88): string {
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, limit)}...`;
}

function getProjectStatusTone(status: string): string {
  if (status === "imported") {
    return "success";
  }
  if (status === "initialized") {
    return "warning";
  }
  if (status === "ready") {
    return "info";
  }
  return "muted";
}

function getBatchStatusTone(status: string): string {
  if (status === "success") {
    return "success";
  }
  if (status === "partial_success") {
    return "warning";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "extracting") {
    return "info";
  }
  return "muted";
}

function getSourceLogicalStatus(source: SourceSummary | SourceDetail): string {
  if (source.request_status === "running") {
    return "running";
  }
  if (source.request_status === "failed") {
    return "request_failed";
  }
  if (source.parse_status === "failed") {
    return "parse_failed";
  }
  if (source.is_manual_edited) {
    return "edited";
  }
  if (source.request_status === "success" && source.parse_status === "success") {
    return "success";
  }
  return "pending";
}

function getSourceStatusTone(status: string): string {
  if (status === "success") {
    return "success";
  }
  if (status === "edited") {
    return "warning";
  }
  if (status === "running") {
    return "info";
  }
  if (status === "parse_failed" || status === "request_failed") {
    return "danger";
  }
  return "muted";
}

function formatProjectStatus(status: string): string {
  if (status === "ready") {
    return "待处理";
  }
  if (status === "initialized") {
    return "已初始化";
  }
  if (status === "imported") {
    return "已导入";
  }
  return status;
}

function formatBatchStatus(status: string): string {
  if (status === "uploaded") {
    return "已上传";
  }
  if (status === "extracting") {
    return "处理中";
  }
  if (status === "success") {
    return "处理成功";
  }
  if (status === "partial_success") {
    return "部分成功";
  }
  if (status === "failed") {
    return "处理失败";
  }
  return status;
}

function formatLogicalStatus(status: string): string {
  if (status === "pending") {
    return "待处理";
  }
  if (status === "running") {
    return "处理中";
  }
  if (status === "request_failed") {
    return "请求失败";
  }
  if (status === "parse_failed") {
    return "解析失败";
  }
  if (status === "edited") {
    return "已人工修订";
  }
  if (status === "success") {
    return "处理成功";
  }
  return status;
}

function formatRequestStatus(status: string): string {
  if (status === "pending") {
    return "待处理";
  }
  if (status === "running") {
    return "处理中";
  }
  if (status === "success") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
}

function formatParseStatus(status: string): string {
  if (status === "pending") {
    return "待解析";
  }
  if (status === "success") {
    return "解析成功";
  }
  if (status === "failed") {
    return "解析失败";
  }
  return status;
}

function formatImportMode(mode: string): string {
  if (mode === "incremental") {
    return "增量导入";
  }
  if (mode === "rebuild") {
    return "重建导入";
  }
  return mode;
}

function formatTaskStatus(status: string): string {
  if (status === "pending") {
    return "待处理";
  }
  if (status === "success") {
    return "成功";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
}

function formatBooleanText(value: boolean): string {
  return value ? "是" : "否";
}

function isSourceRetryable(source: SourceSummary | SourceDetail): boolean {
  return source.request_status !== "running";
}

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("project");
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [busyKeys, setBusyKeys] = useState<Record<string, boolean>>({});

  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [configForm, setConfigForm] = useState<ConfigFormState>(() => buildDemoConfigDraft());
  const [projectForm, setProjectForm] = useState<ProjectFormState>(() => buildDemoProjectDraft());
  const [editingConfigId, setEditingConfigId] = useState("");
  const [editingProjectId, setEditingProjectId] = useState("");

  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [instruction, setInstruction] = useState(DEMO_INSTRUCTION);
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const [sourceSummaries, setSourceSummaries] = useState<SourceSummary[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [sourceDetail, setSourceDetail] = useState<SourceDetail | null>(null);
  const [rawResponseDraft, setRawResponseDraft] = useState("");
  const [triples, setTriples] = useState<Triple[]>([]);
  const [newTripleForm, setNewTripleForm] = useState<TripleFormState>(createEmptyTripleForm());
  const [editingTripleId, setEditingTripleId] = useState("");
  const [editingTripleForm, setEditingTripleForm] = useState<TripleFormState>(createEmptyTripleForm());

  const [schema, setSchema] = useState<ProjectSchema | null>(null);
  const [newEntityTypeName, setNewEntityTypeName] = useState("");
  const [newRelationTypeName, setNewRelationTypeName] = useState("");
  const [graphLogs, setGraphLogs] = useState<GraphImportLog[]>([]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;
  const selectedBatch = batches.find((batch) => batch.id === selectedBatchId) ?? null;
  const activeProgress = progress?.batch_id === selectedBatchId ? progress : null;
  const configUsageCountMap = projects.reduce<Record<string, number>>((result, project) => {
    result[project.extract_config_id] = (result[project.extract_config_id] ?? 0) + 1;
    return result;
  }, {});

  function setBusy(key: string, value: boolean) {
    setBusyKeys((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function isBusy(key: string): boolean {
    return Boolean(busyKeys[key]);
  }

  function showSuccess(text: string) {
    setNotice({ tone: "success", text });
  }

  function showError(text: string) {
    setNotice({ tone: "error", text });
  }

  async function runTask<T>(key: string, task: () => Promise<T>): Promise<T | null> {
    setBusy(key, true);
    try {
      return await task();
    } catch (error) {
      showError(getErrorMessage(error));
      return null;
    } finally {
      setBusy(key, false);
    }
  }

  async function loadOverview() {
    const [nextConfigs, nextProjects] = await Promise.all([listConfigs(), listProjects()]);
    setConfigs(nextConfigs);
    setProjects(nextProjects);
    setProjectForm((current) => {
      const nextConfigId =
        current.extractConfigId && nextConfigs.some((config) => config.id === current.extractConfigId)
          ? current.extractConfigId
          : nextConfigs[0]?.id ?? "";
      return {
        ...current,
        extractConfigId: nextConfigId,
      };
    });
    setSelectedProjectId((current) => {
      if (current && nextProjects.some((project) => project.id === current)) {
        return current;
      }
      return nextProjects[0]?.id ?? "";
    });
  }

  async function loadProjectBatches(projectId: string) {
    const nextBatches = await listBatches(projectId);
    setBatches(nextBatches);
  }

  async function loadBatchContext(batchId: string) {
    const batch = batches.find((item) => item.id === batchId) ?? null;
    const nextSources = await listBatchSources(batchId);
    setSourceSummaries(nextSources);

    if (batch?.status === "uploaded") {
      setProgress({
        batch_id: batch.id,
        status: batch.status,
        total: batch.valid_lines,
        processed: batch.success_count + batch.request_failed_count,
        success_count: batch.success_count,
        request_failed_count: batch.request_failed_count,
        parse_failed_count: batch.parse_failed_count,
      });
      return;
    }

    const nextProgress = await getBatchProgress(batchId);
    setProgress(nextProgress);
  }

  async function loadSourceContext(sourceId: string) {
    const [nextDetail, nextTriples] = await Promise.all([
      getSourceDetail(sourceId),
      listSourceTriples(sourceId),
    ]);
    setSourceDetail(nextDetail);
    setRawResponseDraft(nextDetail.raw_response ?? "");
    setTriples(nextTriples);
  }

  async function loadSchemaContext(projectId: string) {
    const [nextSchema, nextLogs] = await Promise.all([
      getProjectSchema(projectId),
      listImportLogs(projectId),
    ]);
    setSchema(nextSchema);
    setGraphLogs(nextLogs);
  }

  async function refreshSelectedBatchState(batchId: string) {
    await loadBatchContext(batchId);
    if (selectedProjectId) {
      await loadProjectBatches(selectedProjectId);
    }
  }

  async function refreshSelectedSourceState(sourceId: string) {
    await loadSourceContext(sourceId);
    if (selectedBatchId) {
      await loadBatchContext(selectedBatchId);
    }
    if (selectedProjectId) {
      const nextProjects = await listProjects();
      setProjects(nextProjects);
    }
  }

  useEffect(() => {
    void (async () => {
      const result = await runTask("load-overview", loadOverview);
      if (result !== null) {
        showSuccess("已加载当前项目与配置。");
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedProjectId) {
      setBatches([]);
      setSelectedBatchId("");
      setSourceSummaries([]);
      setSelectedSourceId("");
      setSourceDetail(null);
      setTriples([]);
      setSchema(null);
      setGraphLogs([]);
      setProgress(null);
      return;
    }

    void runTask("load-project-scoped", async () => {
      await Promise.all([loadProjectBatches(selectedProjectId), loadSchemaContext(selectedProjectId)]);
    });
  }, [selectedProjectId]);

  useEffect(() => {
    if (!batches.length) {
      setSelectedBatchId("");
      setSourceSummaries([]);
      setSelectedSourceId("");
      setSourceDetail(null);
      setTriples([]);
      setProgress(null);
      return;
    }

    if (!selectedBatchId || !batches.some((batch) => batch.id === selectedBatchId)) {
      setSelectedBatchId(batches[0].id);
    }
  }, [batches, selectedBatchId]);

  useEffect(() => {
    if (!selectedBatchId) {
      setSourceSummaries([]);
      setSelectedSourceId("");
      setSourceDetail(null);
      setTriples([]);
      setProgress(null);
      return;
    }

    const batch = batches.find((item) => item.id === selectedBatchId);
    if (batch?.instruction) {
      setInstruction(batch.instruction);
    }

    void runTask("load-batch-context", async () => {
      await loadBatchContext(selectedBatchId);
    });
  }, [selectedBatchId, batches]);

  useEffect(() => {
    if (!sourceSummaries.length) {
      setSelectedSourceId("");
      setSourceDetail(null);
      setTriples([]);
      return;
    }

    if (!selectedSourceId || !sourceSummaries.some((source) => source.id === selectedSourceId)) {
      setSelectedSourceId(sourceSummaries[0].id);
    }
  }, [sourceSummaries, selectedSourceId]);

  useEffect(() => {
    if (!selectedSourceId) {
      setSourceDetail(null);
      setTriples([]);
      return;
    }

    setEditingTripleId("");
    setEditingTripleForm(createEmptyTripleForm());
    void runTask("load-source-context", async () => {
      await loadSourceContext(selectedSourceId);
    });
  }, [selectedSourceId]);

  useEffect(() => {
    const effectiveStatus = activeProgress?.status ?? selectedBatch?.status;
    if (!selectedBatchId || effectiveStatus !== "extracting") {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshSelectedBatchState(selectedBatchId);
    }, 2000);

    return () => {
      window.clearInterval(timer);
    };
  }, [activeProgress?.status, selectedBatch?.status, selectedBatchId]);

  async function handleCreateConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    let providerOptions: Record<string, unknown> | null = null;
    try {
      providerOptions = parseProviderOptionsText(configForm.providerOptionsText);
    } catch (error) {
      showError(getErrorMessage(error));
      return;
    }

    const timeoutSeconds = Number(configForm.timeoutSeconds);
    if (!Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0) {
      showError("超时时间必须是大于 0 的数字。");
      return;
    }

    if (editingConfigId) {
      const payload = {
        name: configForm.name.trim(),
        base_url: configForm.baseUrl.trim(),
        model_name: configForm.modelName.trim(),
        timeout_seconds: timeoutSeconds,
        provider_options: providerOptions,
        ...(configForm.apiKey.trim() ? { api_key: configForm.apiKey.trim() } : {}),
      };
      const updated = await runTask("update-config", () => updateConfig(editingConfigId, payload));
      if (!updated) {
        return;
      }
      await loadOverview();
      setEditingConfigId("");
      setConfigForm(buildDemoConfigDraft());
      showSuccess(`已更新抽取配置：${updated.name}`);
      return;
    }

    const created = await runTask("create-config", () =>
      createConfig({
        config_type: "extract",
        name: configForm.name.trim(),
        base_url: configForm.baseUrl.trim(),
        api_key: configForm.apiKey.trim(),
        model_name: configForm.modelName.trim(),
        timeout_seconds: timeoutSeconds,
        provider_options: providerOptions,
      }),
    );

    if (!created) {
      return;
    }

    await loadOverview();
    setProjectForm((current) => ({
      ...current,
      extractConfigId: created.id,
    }));
    setConfigForm(buildDemoConfigDraft());
    showSuccess(`已创建抽取配置：${created.name}`);
  }

  function handleStartEditConfig(config: ModelConfig) {
    setEditingConfigId(config.id);
    setConfigForm({
      name: config.name,
      baseUrl: config.base_url,
      apiKey: "",
      modelName: config.model_name,
      timeoutSeconds: String(config.timeout_seconds),
      providerOptionsText: stringifyProviderOptions(config.provider_options),
    });
  }

  function resetConfigFormToDemo() {
    setEditingConfigId("");
    setConfigForm(buildDemoConfigDraft());
  }

  async function handleDeleteConfig(config: ModelConfig) {
    const usageCount = configUsageCountMap[config.id] ?? 0;
    if (usageCount > 0) {
      showError(
        `配置“${config.name}”正在被 ${usageCount} 个项目使用，不能删除。请先删除相关项目，或把项目改到其他抽取配置。`,
      );
      return;
    }

    if (!window.confirm(`确认删除配置“${config.name}”吗？`)) {
      return;
    }

    const deleted = await runTask("delete-config", () => deleteConfig(config.id));
    if (!deleted) {
      return;
    }

    await loadOverview();
    if (config.id === editingConfigId) {
      resetConfigFormToDemo();
    }
    showSuccess(`已删除配置：${config.name}`);
  }

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!projectForm.extractConfigId) {
      showError("请先选择抽取配置。");
      return;
    }

    if (editingProjectId) {
      const updated = await runTask("update-project", () =>
        updateProject(editingProjectId, {
          name: projectForm.name.trim(),
          description: projectForm.description.trim() || null,
          extract_config_id: projectForm.extractConfigId,
        }),
      );
      if (!updated) {
        return;
      }
      await loadOverview();
      setEditingProjectId("");
      setProjectForm(buildDemoProjectDraft(updated.extract_config_id));
      showSuccess(`已更新项目：${updated.name}`);
      return;
    }

    const created = await runTask("create-project", () =>
      createProject({
        name: projectForm.name.trim(),
        description: projectForm.description.trim() || null,
        extract_config_id: projectForm.extractConfigId,
      }),
    );

    if (!created) {
      return;
    }

    await loadOverview();
    setSelectedProjectId(created.id);
    setProjectForm(buildDemoProjectDraft(created.extract_config_id));
    setActiveTab("batch");
    showSuccess(`已创建项目：${created.name}`);
  }

  function handleStartEditProject(project: Project) {
    setEditingProjectId(project.id);
    setSelectedProjectId(project.id);
    setProjectForm({
      name: project.name,
      description: project.description ?? "",
      extractConfigId: project.extract_config_id,
    });
  }

  function resetProjectFormToDemo() {
    setEditingProjectId("");
    setProjectForm(buildDemoProjectDraft(configs[0]?.id ?? ""));
  }

  async function handleDeleteProject(project: Project) {
    if (!window.confirm(`确认删除项目“${project.name}”吗？项目相关数据将一并删除。`)) {
      return;
    }

    const deleted = await runTask("delete-project", () => deleteProject(project.id));
    if (!deleted) {
      return;
    }

    if (project.id === selectedProjectId) {
      setSelectedProjectId("");
    }
    await loadOverview();
    if (project.id === editingProjectId) {
      resetProjectFormToDemo();
    }
    showSuccess(`已删除项目：${project.name}`);
  }

  async function handleUploadBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedProjectId) {
      showError("请先在项目与配置标签中选中一个项目。");
      return;
    }
    if (!uploadFile) {
      showError("请先选择一个文本文件。");
      return;
    }

    const created = await runTask("upload-batch", () => uploadBatch(selectedProjectId, uploadFile));
    if (!created) {
      return;
    }

    await loadProjectBatches(selectedProjectId);
    setSelectedBatchId(created.id);
    setUploadFile(null);
    setFileInputKey((current) => current + 1);
    showSuccess(`已上传文件：${created.file_name}`);
  }

  async function handleStartExtract() {
    if (!selectedBatchId) {
      showError("请先选择一个批次。");
      return;
    }
    if (!instruction.trim()) {
      showError("抽取规则不能为空。");
      return;
    }

    const started = await runTask("start-extract", () => startExtract(selectedBatchId, instruction));
    if (!started) {
      return;
    }

    await refreshSelectedBatchState(selectedBatchId);
    showSuccess("已启动抽取任务。");
  }

  async function handleRetryFailed() {
    if (!selectedBatchId) {
      showError("请先选择一个批次。");
      return;
    }

    const result = await runTask("retry-failed", () => retryFailed(selectedBatchId));
    if (!result) {
      return;
    }

    await refreshSelectedBatchState(selectedBatchId);
    showSuccess(`已提交失败记录重试，排队数量：${result.queued ?? 0}`);
  }

  async function handleRetrySource(source: SourceSummary | SourceDetail) {
    const result = await runTask(`retry-source-${source.id}`, () => retrySource(source.id));
    if (!result) {
      return;
    }

    if (selectedBatchId) {
      await refreshSelectedBatchState(selectedBatchId);
    }
    showSuccess("已提交当前记录重试。");
  }

  async function handleSaveRawResponse() {
    if (!sourceDetail) {
      showError("请先选择一条记录。");
      return;
    }
    if (sourceDetail.raw_response === null) {
      showError("当前记录暂无模型返回内容，无法直接编辑。请先重试处理或手动补充三元组。");
      return;
    }

    const updated = await runTask("update-raw-response", () =>
      updateRawResponse(sourceDetail.id, rawResponseDraft),
    );
    if (!updated) {
      return;
    }

    setSourceDetail(updated);
    if (selectedBatchId) {
      await loadBatchContext(selectedBatchId);
    }
    await loadOverview();
    showSuccess("已保存模型返回内容，可继续重新解析。");
  }

  async function handleReparse() {
    if (!sourceDetail) {
      showError("请先选择一条记录。");
      return;
    }

    const result = await runTask("reparse-source", () => reparseSource(sourceDetail.id));
    if (!result) {
      return;
    }

    await refreshSelectedSourceState(sourceDetail.id);
    if (selectedProjectId) {
      await loadSchemaContext(selectedProjectId);
    }
    showSuccess(`重新解析完成，当前有效三元组数：${result.triple_count}`);
  }

  async function handleCreateTriple() {
    if (!selectedSourceId) {
      showError("请先选择一条记录。");
      return;
    }

    const created = await runTask("create-triple", () =>
      createSourceTriple(selectedSourceId, buildTriplePayload(newTripleForm)),
    );
    if (!created) {
      return;
    }

    setNewTripleForm(createEmptyTripleForm());
    await refreshSelectedSourceState(selectedSourceId);
    if (selectedProjectId) {
      await loadSchemaContext(selectedProjectId);
    }
    showSuccess("已新增三元组。");
  }

  async function handleSaveEditedTriple() {
    if (!editingTripleId) {
      return;
    }

    const updated = await runTask("update-triple", () =>
      updateTriple(editingTripleId, buildTriplePayload(editingTripleForm)),
    );
    if (!updated) {
      return;
    }

    setEditingTripleId("");
    setEditingTripleForm(createEmptyTripleForm());
    if (selectedSourceId) {
      await refreshSelectedSourceState(selectedSourceId);
    }
    if (selectedProjectId) {
      await loadSchemaContext(selectedProjectId);
    }
    showSuccess("已更新三元组。");
  }

  async function handleDeleteTriple(triple: Triple) {
    if (!window.confirm("确认删除这条三元组吗？")) {
      return;
    }

    const deleted = await runTask(`delete-triple-${triple.id}`, () => deleteTriple(triple.id));
    if (!deleted) {
      return;
    }

    if (selectedSourceId) {
      await refreshSelectedSourceState(selectedSourceId);
    }
    if (selectedProjectId) {
      await loadSchemaContext(selectedProjectId);
    }
    showSuccess("已删除三元组。");
  }

  async function handleRefreshSchema() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const result = await runTask("refresh-schema", () => refreshProjectSchema(selectedProjectId));
    if (!result) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(
      `类型已刷新：实体类型 ${result.entity_types.length} 项，关系类型 ${result.relation_types.length} 项。`,
    );
  }

  async function handleCreateEntityType() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const created = await runTask("create-entity-type", () =>
      createEntityType(selectedProjectId, newEntityTypeName),
    );
    if (!created) {
      return;
    }

    setNewEntityTypeName("");
    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已新增实体类型：${created.type_name}`);
  }

  async function handleCreateRelationType() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const created = await runTask("create-relation-type", () =>
      createRelationType(selectedProjectId, newRelationTypeName),
    );
    if (!created) {
      return;
    }

    setNewRelationTypeName("");
    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已新增关系类型：${created.relation_name}`);
  }

  async function handleRenameEntityType(entityTypeId: string, currentName: string) {
    const nextName = window.prompt("输入新的实体类型名称：", currentName);
    if (!nextName || nextName.trim() === currentName) {
      return;
    }

    const renamed = await runTask(`rename-entity-${entityTypeId}`, () =>
      renameEntityType(entityTypeId, nextName),
    );
    if (!renamed || !selectedProjectId) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已重命名实体类型：${currentName} -> ${renamed.type_name}`);
  }

  async function handleRenameRelationType(relationTypeId: string, currentName: string) {
    const nextName = window.prompt("输入新的关系类型名称：", currentName);
    if (!nextName || nextName.trim() === currentName) {
      return;
    }

    const renamed = await runTask(`rename-relation-${relationTypeId}`, () =>
      renameRelationType(relationTypeId, nextName),
    );
    if (!renamed || !selectedProjectId) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已重命名关系类型：${currentName} -> ${renamed.relation_name}`);
  }

  async function handleDeleteEntityType(entityTypeId: string, typeName: string) {
    if (!window.confirm(`确认删除实体类型“${typeName}”吗？`)) {
      return;
    }

    const deleted = await runTask(`delete-entity-${entityTypeId}`, () => deleteEntityType(entityTypeId));
    if (!deleted || !selectedProjectId) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已删除实体类型：${typeName}`);
  }

  async function handleDeleteRelationType(relationTypeId: string, relationName: string) {
    if (!window.confirm(`确认删除关系类型“${relationName}”吗？`)) {
      return;
    }

    const deleted = await runTask(`delete-relation-${relationTypeId}`, () =>
      deleteRelationType(relationTypeId),
    );
    if (!deleted || !selectedProjectId) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`已删除关系类型：${relationName}`);
  }

  async function handleInitGraph() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const result = await runTask("graph-init", () => initGraph(selectedProjectId));
    if (!result) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(`图谱初始化完成，当前状态：${formatProjectStatus(result.status)}`);
  }

  async function handleImportGraph() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const result = await runTask("graph-import", () => importGraph(selectedProjectId));
    if (!result) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(
      `图谱导入完成：节点 ${result.created_node_count}，关系 ${result.created_relation_count}，去重 ${result.deduplicated_count}`,
    );
  }

  async function handleRebuildGraph() {
    if (!selectedProjectId) {
      showError("请先选中项目。");
      return;
    }

    const result = await runTask("graph-rebuild", () => rebuildGraph(selectedProjectId));
    if (!result) {
      return;
    }

    await loadSchemaContext(selectedProjectId);
    await loadOverview();
    showSuccess(
      `图谱重建完成：节点 ${result.created_node_count}，关系 ${result.created_relation_count}，失败 ${result.failed_count}`,
    );
  }

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">知识图谱管理平台</p>
          <h1>知识抽取与图谱构建</h1>
          <p className="hero-text">
            统一管理文本导入、知识抽取、结果校对与图谱更新。
          </p>
        </div>
        <div className="hero-summary">
          <StatCard label="抽取配置" value={String(configs.length)} />
          <StatCard label="项目数" value={String(projects.length)} />
          <StatCard label="当前标签" value={getTabLabel(activeTab)} />
          <StatCard
            label="当前项目"
            value={selectedProject ? selectedProject.name : "未选择"}
            tone={selectedProject ? getProjectStatusTone(selectedProject.status) : "muted"}
          />
        </div>
      </header>

      <nav className="tab-bar" aria-label="主功能标签">
        <TabButton
          active={activeTab === "project"}
          onClick={() => setActiveTab("project")}
          label="项目与配置"
        />
        <TabButton
          active={activeTab === "batch"}
          onClick={() => setActiveTab("batch")}
          label="导入与抽取"
        />
        <TabButton
          active={activeTab === "schema"}
          onClick={() => setActiveTab("schema")}
          label="类型与图谱"
        />
      </nav>

      {notice ? (
        <div className={`notice-banner notice-${notice.tone}`}>
          <span>{notice.text}</span>
          <button className="ghost-button" type="button" onClick={() => setNotice(null)}>
            关闭
          </button>
        </div>
      ) : null}

      <main className="panel-stack">
        {activeTab === "project" ? (
          <>
            <div className="two-column-grid">
              <SectionCard
                title={editingConfigId ? "编辑抽取配置" : "新建抽取配置"}
                description={
                  editingConfigId
                    ? "如需保留当前访问密钥，可将该字段留空。"
                    : "填写模型服务地址、访问密钥和模型名称，用于文本抽取。"
                }
                actions={
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={resetConfigFormToDemo}
                  >
                    {editingConfigId ? "取消编辑" : "重置表单"}
                  </button>
                }
              >
                <form className="form-grid" onSubmit={handleCreateConfig}>
                  <label>
                    <span>配置名称</span>
                    <input
                      value={configForm.name}
                      onChange={(event) =>
                        setConfigForm((current) => ({ ...current, name: event.target.value }))
                      }
                      required
                    />
                  </label>
                  <label>
                    <span>服务地址</span>
                    <input
                      value={configForm.baseUrl}
                      onChange={(event) =>
                        setConfigForm((current) => ({ ...current, baseUrl: event.target.value }))
                      }
                      required
                    />
                  </label>
                  <label>
                    <span>访问密钥</span>
                    <input
                      value={configForm.apiKey}
                      onChange={(event) =>
                        setConfigForm((current) => ({ ...current, apiKey: event.target.value }))
                      }
                      placeholder={editingConfigId ? "留空则保持当前密钥不变" : ""}
                      required={!editingConfigId}
                    />
                  </label>
                  <label>
                    <span>模型名称</span>
                    <input
                      value={configForm.modelName}
                      onChange={(event) =>
                        setConfigForm((current) => ({ ...current, modelName: event.target.value }))
                      }
                      required
                    />
                  </label>
                  <label>
                    <span>超时秒数</span>
                    <input
                      value={configForm.timeoutSeconds}
                      onChange={(event) =>
                        setConfigForm((current) => ({
                          ...current,
                          timeoutSeconds: event.target.value,
                        }))
                      }
                      inputMode="numeric"
                      required
                    />
                  </label>
                  <label className="full-span">
                    <span>扩展参数（JSON，可选）</span>
                    <textarea
                      rows={4}
                      value={configForm.providerOptionsText}
                      onChange={(event) =>
                        setConfigForm((current) => ({
                          ...current,
                          providerOptionsText: event.target.value,
                        }))
                      }
                      placeholder='例如：{"temperature":0.2}'
                    />
                  </label>
                  <div className="form-actions full-span">
                    <button
                      className="primary-button"
                      type="submit"
                      disabled={isBusy("create-config") || isBusy("update-config")}
                    >
                      {editingConfigId
                        ? isBusy("update-config")
                          ? "保存中..."
                          : "保存配置修改"
                        : isBusy("create-config")
                          ? "创建中..."
                          : "创建抽取配置"}
                    </button>
                  </div>
                </form>
              </SectionCard>

              <SectionCard
                title={editingProjectId ? "编辑项目" : "新建项目"}
                description="创建项目后，可在该项目下管理文本、抽取结果和图谱数据。"
                actions={
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={resetProjectFormToDemo}
                  >
                    {editingProjectId ? "取消编辑" : "重置表单"}
                  </button>
                }
              >
                <form className="form-grid" onSubmit={handleCreateProject}>
                  <label>
                    <span>项目名称</span>
                    <input
                      value={projectForm.name}
                      onChange={(event) =>
                        setProjectForm((current) => ({ ...current, name: event.target.value }))
                      }
                      required
                    />
                  </label>
                  <label>
                    <span>抽取配置</span>
                    <select
                      value={projectForm.extractConfigId}
                      onChange={(event) =>
                        setProjectForm((current) => ({
                          ...current,
                          extractConfigId: event.target.value,
                        }))
                      }
                      disabled={!configs.length}
                      required
                    >
                      <option value="">请选择抽取配置</option>
                      {configs.map((config) => (
                        <option key={config.id} value={config.id}>
                          {config.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="full-span">
                    <span>项目说明</span>
                    <textarea
                      rows={4}
                      value={projectForm.description}
                      onChange={(event) =>
                        setProjectForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <div className="form-actions full-span">
                    <button
                      className="primary-button"
                      type="submit"
                      disabled={!configs.length || isBusy("create-project") || isBusy("update-project")}
                    >
                      {editingProjectId
                        ? isBusy("update-project")
                          ? "保存中..."
                          : "保存项目修改"
                        : isBusy("create-project")
                          ? "创建中..."
                          : "创建项目"}
                    </button>
                  </div>
                </form>
              </SectionCard>
            </div>

            <div className="two-column-grid">
              <SectionCard title="抽取配置列表" description="管理可用的抽取服务配置。">
                {configs.length ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>名称</th>
                          <th>服务地址</th>
                          <th>模型</th>
                          <th>访问密钥</th>
                          <th>状态</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {configs.map((config) => {
                          const usageCount = configUsageCountMap[config.id] ?? 0;
                          const isConfigInUse = usageCount > 0;

                          return (
                            <tr key={config.id}>
                              <td className="stacked-cell">
                                <strong>{config.name}</strong>
                                {isConfigInUse ? <span>被 {usageCount} 个项目引用，暂不可删除</span> : null}
                              </td>
                              <td className="mono-cell">{config.base_url}</td>
                              <td>{config.model_name}</td>
                              <td className="mono-cell">{config.api_key_masked}</td>
                              <td>
                                <StatusBadge
                                  label={config.is_enabled ? "可用" : "停用"}
                                  tone={config.is_enabled ? "success" : "muted"}
                                />
                              </td>
                              <td>
                                <button
                                  className="ghost-button"
                                  type="button"
                                  onClick={() => handleStartEditConfig(config)}
                                >
                                  编辑
                                </button>
                                <button
                                  className="ghost-button"
                                  type="button"
                                  onClick={() => handleDeleteConfig(config)}
                                  disabled={isBusy("delete-config") || isConfigInUse}
                                  title={isConfigInUse ? "该配置正在被项目使用，无法删除" : undefined}
                                >
                                  删除
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="暂无抽取配置" description="请先新建抽取配置。" />
                )}
              </SectionCard>

              <SectionCard title="项目列表" description="选中项目后，可继续执行导入、校对和图谱操作。">
                {projects.length ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>项目</th>
                          <th>状态</th>
                          <th>配置</th>
                          <th>最近导入</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {projects.map((project) => (
                          <tr
                            key={project.id}
                            className={project.id === selectedProjectId ? "row-selected" : undefined}
                          >
                            <td>
                              <div className="stacked-cell">
                                <strong>{project.name}</strong>
                                <span>{project.description || "无项目说明"}</span>
                              </div>
                            </td>
                            <td>
                              <StatusBadge
                                label={formatProjectStatus(project.status)}
                                tone={getProjectStatusTone(project.status)}
                              />
                            </td>
                            <td>{configs.find((config) => config.id === project.extract_config_id)?.name || project.extract_config_id}</td>
                            <td>{formatTime(project.last_import_at)}</td>
                            <td>
                              <div className="inline-actions">
                                <button
                                  className="ghost-button"
                                  type="button"
                                  onClick={() => setSelectedProjectId(project.id)}
                                >
                                  {project.id === selectedProjectId ? "已选中" : "选中"}
                                </button>
                                <button
                                  className="ghost-button"
                                  type="button"
                                  onClick={() => handleStartEditProject(project)}
                                >
                                  编辑
                                </button>
                                <button
                                  className="ghost-button"
                                  type="button"
                                  onClick={() => handleDeleteProject(project)}
                                  disabled={isBusy("delete-project")}
                                >
                                  删除
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="暂无项目" description="请先创建项目。" />
                )}
              </SectionCard>
            </div>
          </>
        ) : null}

        {activeTab === "batch" ? (
          selectedProject ? (
            <>
              <ContextStrip
                items={[
                  { label: "当前项目", value: selectedProject.name },
                  { label: "状态", value: formatProjectStatus(selectedProject.status) },
                  {
                    label: "抽取配置",
                    value:
                      configs.find((config) => config.id === selectedProject.extract_config_id)?.name ||
                      selectedProject.extract_config_id,
                  },
                  { label: "文件要求", value: DEMO_SAMPLE_FILE_HINT },
                ]}
              />

              <div className="two-column-grid">
                <SectionCard title="上传文本并准备处理" description="上传 .txt 文件后，系统会按行生成待处理记录。">
                  <form className="form-grid" onSubmit={handleUploadBatch}>
                    <label className="full-span">
                      <span>选择文本文件</span>
                      <input
                        key={fileInputKey}
                        type="file"
                        accept=".txt,text/plain"
                        onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                      />
                    </label>
                    <label className="full-span">
                      <span>抽取规则</span>
                      <textarea
                        rows={16}
                        value={instruction}
                        onChange={(event) => setInstruction(event.target.value)}
                      />
                    </label>
                    <div className="form-actions full-span">
                      <button className="primary-button" type="submit" disabled={isBusy("upload-batch")}>
                        {isBusy("upload-batch") ? "上传中..." : "上传文件"}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => setInstruction(DEMO_INSTRUCTION)}
                      >
                        恢复系统预设
                      </button>
                    </div>
                  </form>
                </SectionCard>

                <SectionCard
                  title="处理批次与进度"
                  description="选择一个批次后，可开始处理或重试失败项。处理过程中会自动更新进度。"
                >
                  <div className="stacked-block">
                    <div className="inline-actions">
                      <button
                        className="primary-button"
                        type="button"
                        onClick={handleStartExtract}
                        disabled={!selectedBatchId || isBusy("start-extract")}
                      >
                        {isBusy("start-extract") ? "提交中..." : "开始处理"}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={handleRetryFailed}
                        disabled={!selectedBatchId || isBusy("retry-failed")}
                      >
                        {isBusy("retry-failed") ? "提交中..." : "重试失败项"}
                      </button>
                    </div>
                    <div className="progress-grid">
                      <StatCard label="批次数" value={String(batches.length)} />
                      <StatCard label="当前批次" value={selectedBatch?.file_name || "未选择"} />
                      <StatCard
                        label="批次状态"
                        value={formatBatchStatus(activeProgress?.status || selectedBatch?.status || "-")}
                        tone={getBatchStatusTone(activeProgress?.status || selectedBatch?.status || "")}
                      />
                      <StatCard
                        label="处理进度"
                        value={
                          activeProgress
                            ? `${activeProgress.processed}/${activeProgress.total}`
                            : selectedBatch
                              ? `${selectedBatch.success_count + selectedBatch.request_failed_count}/${selectedBatch.valid_lines}`
                              : "-"
                        }
                      />
                    </div>
                    {batches.length ? (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>文件</th>
                              <th>状态</th>
                              <th>有效行</th>
                              <th>成功</th>
                              <th>请求失败</th>
                              <th>解析失败</th>
                            </tr>
                          </thead>
                          <tbody>
                            {batches.map((batch) => (
                              <tr
                                key={batch.id}
                                className={batch.id === selectedBatchId ? "row-selected" : undefined}
                                onClick={() => setSelectedBatchId(batch.id)}
                              >
                                <td>{batch.file_name}</td>
                              <td>
                                <StatusBadge
                                  label={formatBatchStatus(batch.status)}
                                  tone={getBatchStatusTone(batch.status)}
                                />
                              </td>
                                <td>{batch.valid_lines}</td>
                                <td>{batch.success_count}</td>
                                <td>{batch.request_failed_count}</td>
                                <td>{batch.parse_failed_count}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="还没有批次" description="上传一个 txt 文件后，这里会显示批次列表。" />
                    )}
                  </div>
                </SectionCard>
              </div>

              <SectionCard title="文本记录" description="选择一条记录后，可查看处理结果、错误信息和三元组详情。">
                {sourceSummaries.length ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>行号</th>
                          <th>逻辑状态</th>
                          <th>请求状态</th>
                          <th>解析状态</th>
                          <th>文本</th>
                          <th>操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sourceSummaries.map((source) => {
                          const logicalStatus = getSourceLogicalStatus(source);
                          return (
                            <tr
                              key={source.id}
                              className={source.id === selectedSourceId ? "row-selected" : undefined}
                            >
                              <td>{source.line_no}</td>
                              <td>
                                <StatusBadge
                                  label={formatLogicalStatus(logicalStatus)}
                                  tone={getSourceStatusTone(logicalStatus)}
                                />
                              </td>
                              <td>{formatRequestStatus(source.request_status)}</td>
                              <td>{formatParseStatus(source.parse_status)}</td>
                              <td title={source.input_text}>{truncateText(source.input_text, 90)}</td>
                              <td>
                                <div className="inline-actions">
                                  <button
                                    className="ghost-button"
                                    type="button"
                                    onClick={() => setSelectedSourceId(source.id)}
                                  >
                                    查看
                                  </button>
                                  <button
                                    className="ghost-button"
                                    type="button"
                                    onClick={() => handleRetrySource(source)}
                                    disabled={!isSourceRetryable(source)}
                                  >
                                    单条重试
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="暂无文本记录" description="请先上传并选择一个批次。" />
                )}
              </SectionCard>

              <div className="two-column-grid">
                <SectionCard title="记录详情与模型返回" description="如解析失败，可先修改模型返回内容，再重新解析。">
                  {sourceDetail ? (
                    <div className="stacked-block">
                      <div className="detail-grid">
                        <DetailBlock label="行号" value={String(sourceDetail.line_no)} />
                        <DetailBlock
                          label="逻辑状态"
                          value={formatLogicalStatus(getSourceLogicalStatus(sourceDetail))}
                        />
                        <DetailBlock label="请求状态" value={formatRequestStatus(sourceDetail.request_status)} />
                        <DetailBlock label="解析状态" value={formatParseStatus(sourceDetail.parse_status)} />
                        <DetailBlock label="重试次数" value={String(sourceDetail.retry_count)} />
                        <DetailBlock
                          label="人工修订"
                          value={formatBooleanText(sourceDetail.is_manual_edited)}
                        />
                      </div>
                      <label>
                        <span>输入文本</span>
                        <textarea rows={4} value={sourceDetail.input_text} readOnly />
                      </label>
                      <label>
                        <span>请求内容</span>
                        <textarea rows={8} value={sourceDetail.request_payload || ""} readOnly />
                      </label>
                      <label>
                        <span>模型返回</span>
                        <textarea
                          rows={10}
                          value={rawResponseDraft}
                          onChange={(event) => setRawResponseDraft(event.target.value)}
                        />
                      </label>
                      <label>
                        <span>解析结果</span>
                        <textarea rows={8} value={sourceDetail.cleaned_output_text || ""} readOnly />
                      </label>
                      <label>
                        <span>错误信息</span>
                        <textarea rows={6} value={sourceDetail.error_message || ""} readOnly />
                      </label>
                      <div className="inline-actions">
                        <button
                          className="primary-button"
                          type="button"
                          onClick={handleSaveRawResponse}
                          disabled={isBusy("update-raw-response")}
                        >
                          {isBusy("update-raw-response") ? "保存中..." : "保存模型返回"}
                        </button>
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={handleReparse}
                          disabled={isBusy("reparse-source")}
                        >
                          {isBusy("reparse-source") ? "重新解析中..." : "重新解析"}
                        </button>
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() => handleRetrySource(sourceDetail)}
                          disabled={!isSourceRetryable(sourceDetail)}
                        >
                          单条重试
                        </button>
                      </div>
                    </div>
                  ) : (
                    <EmptyState title="未选择记录" description="请从上方列表选择一条记录。" />
                  )}
                </SectionCard>

                <SectionCard title="三元组编辑器" description="支持手动新增、编辑、删除，仅展示当前记录的有效三元组。">
                  {selectedSourceId ? (
                    <TripleEditor
                      triples={triples}
                      newTripleForm={newTripleForm}
                      editingTripleId={editingTripleId}
                      editingTripleForm={editingTripleForm}
                      createBusy={isBusy("create-triple")}
                      updateBusy={isBusy("update-triple")}
                      onNewChange={(field, value) =>
                        setNewTripleForm((current) => ({ ...current, [field]: value }))
                      }
                      onEditChange={(field, value) =>
                        setEditingTripleForm((current) => ({ ...current, [field]: value }))
                      }
                      onCreate={handleCreateTriple}
                      onBeginEdit={(triple) => {
                        setEditingTripleId(triple.id);
                        setEditingTripleForm({
                          subject: triple.subject,
                          subjectType: triple.subject_type,
                          predicate: triple.predicate,
                          object: triple.object,
                          objectType: triple.object_type,
                        });
                      }}
                      onCancelEdit={() => {
                        setEditingTripleId("");
                        setEditingTripleForm(createEmptyTripleForm());
                      }}
                      onSaveEdit={handleSaveEditedTriple}
                      onDelete={handleDeleteTriple}
                    />
                  ) : (
                    <EmptyState title="未选择记录" description="选中一条记录后，即可在这里管理三元组。" />
                  )}
                </SectionCard>
              </div>
            </>
          ) : (
            <EmptyState title="未选中项目" description="请先在“项目与配置”中创建并选中一个项目。" />
          )
        ) : null}

        {activeTab === "schema" ? (
          selectedProject ? (
            <>
              <ContextStrip
                items={[
                  { label: "当前项目", value: selectedProject.name },
                  { label: "状态", value: formatProjectStatus(selectedProject.status) },
                  { label: "最近导入", value: formatTime(selectedProject.last_import_at) },
                ]}
              />

              <div className="two-column-grid">
                <SectionCard
                  title="刷新类型"
                  description="根据当前项目中的有效三元组补充实体类型与关系类型。"
                >
                  <div className="stacked-block">
                    <div className="progress-grid">
                      <StatCard label="实体类型" value={String(schema?.entity_types.length ?? 0)} />
                      <StatCard label="关系类型" value={String(schema?.relation_types.length ?? 0)} />
                    </div>
                    <button
                      className="primary-button"
                      type="button"
                      onClick={handleRefreshSchema}
                      disabled={isBusy("refresh-schema")}
                    >
                      {isBusy("refresh-schema") ? "刷新中..." : "刷新类型"}
                    </button>
                  </div>
                </SectionCard>

                <SectionCard title="图谱操作" description="先初始化图谱，再执行导入。数据变更后可使用重建更新图谱。">
                  <div className="stacked-block">
                    <div className="inline-actions">
                      <button
                        className="primary-button"
                        type="button"
                        onClick={handleInitGraph}
                        disabled={isBusy("graph-init")}
                      >
                        {isBusy("graph-init") ? "初始化中..." : "初始化图谱"}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={handleImportGraph}
                        disabled={isBusy("graph-import")}
                      >
                        {isBusy("graph-import") ? "导入中..." : "导入图谱"}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={handleRebuildGraph}
                        disabled={isBusy("graph-rebuild")}
                      >
                        {isBusy("graph-rebuild") ? "重建中..." : "重建图谱"}
                      </button>
                    </div>
                    <p className="muted-note">
                      当前项目状态：<strong>{formatProjectStatus(selectedProject.status)}</strong>
                      。图谱初始化完成后，可继续执行导入或重建。
                    </p>
                  </div>
                </SectionCard>
              </div>

              <div className="two-column-grid">
                <SectionCard title="实体类型维护" description="支持新增、改名、删除。删除前会检查是否仍被三元组引用。">
                  <div className="stacked-block">
                    <div className="inline-form">
                      <input
                        value={newEntityTypeName}
                        onChange={(event) => setNewEntityTypeName(event.target.value)}
                        placeholder="新增实体类型名称"
                      />
                      <button
                        className="primary-button"
                        type="button"
                        onClick={handleCreateEntityType}
                        disabled={isBusy("create-entity-type")}
                      >
                        新增
                      </button>
                    </div>
                    {schema?.entity_types.length ? (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>名称</th>
                              <th>更新时间</th>
                              <th>操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            {schema.entity_types.map((entityType) => (
                              <tr key={entityType.id}>
                                <td>{entityType.type_name}</td>
                                <td>{formatTime(entityType.updated_at)}</td>
                                <td>
                                  <div className="inline-actions">
                                    <button
                                      className="ghost-button"
                                      type="button"
                                      onClick={() =>
                                        handleRenameEntityType(entityType.id, entityType.type_name)
                                      }
                                    >
                                      改名
                                    </button>
                                    <button
                                      className="ghost-button"
                                      type="button"
                                      onClick={() =>
                                        handleDeleteEntityType(entityType.id, entityType.type_name)
                                      }
                                    >
                                      删除
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="暂无实体类型" description="请先刷新类型或手动新增一个实体类型。" />
                    )}
                  </div>
                </SectionCard>

                <SectionCard title="关系类型维护" description="关系改名会同步更新引用该关系的三元组关系名称。">
                  <div className="stacked-block">
                    <div className="inline-form">
                      <input
                        value={newRelationTypeName}
                        onChange={(event) => setNewRelationTypeName(event.target.value)}
                        placeholder="新增关系类型名称"
                      />
                      <button
                        className="primary-button"
                        type="button"
                        onClick={handleCreateRelationType}
                        disabled={isBusy("create-relation-type")}
                      >
                        新增
                      </button>
                    </div>
                    {schema?.relation_types.length ? (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>名称</th>
                              <th>更新时间</th>
                              <th>操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            {schema.relation_types.map((relationType) => (
                              <tr key={relationType.id}>
                                <td>{relationType.relation_name}</td>
                                <td>{formatTime(relationType.updated_at)}</td>
                                <td>
                                  <div className="inline-actions">
                                    <button
                                      className="ghost-button"
                                      type="button"
                                      onClick={() =>
                                        handleRenameRelationType(
                                          relationType.id,
                                          relationType.relation_name,
                                        )
                                      }
                                    >
                                      改名
                                    </button>
                                    <button
                                      className="ghost-button"
                                      type="button"
                                      onClick={() =>
                                        handleDeleteRelationType(
                                          relationType.id,
                                          relationType.relation_name,
                                        )
                                      }
                                    >
                                      删除
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <EmptyState title="暂无关系类型" description="请先刷新类型或手动新增一个关系类型。" />
                    )}
                  </div>
                </SectionCard>
              </div>

              <SectionCard title="导入日志" description="展示当前项目的增量导入和重建日志。">
                {graphLogs.length ? (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>时间</th>
                          <th>模式</th>
                          <th>状态</th>
                          <th>候选数</th>
                          <th>节点</th>
                          <th>关系</th>
                          <th>去重</th>
                          <th>失败</th>
                        </tr>
                      </thead>
                      <tbody>
                        {graphLogs.map((log) => (
                          <tr key={log.id}>
                            <td>{formatTime(log.created_at)}</td>
                            <td>{formatImportMode(log.mode)}</td>
                            <td>
                              <StatusBadge label={formatTaskStatus(log.status)} tone={getBatchStatusTone(log.status)} />
                            </td>
                            <td>{log.total_candidate_count}</td>
                            <td>{log.created_node_count}</td>
                            <td>{log.created_relation_count}</td>
                            <td>{log.deduplicated_count}</td>
                            <td>{log.failed_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState title="暂无导入日志" description="执行图谱导入或重建后，这里会显示日志。" />
                )}
              </SectionCard>
            </>
          ) : (
            <EmptyState title="未选中项目" description="请先在“项目与配置”中选中一个项目，再进行类型维护和图谱操作。" />
          )
        ) : null}
      </main>
    </div>
  );
}

function getTabLabel(tab: TabKey): string {
  if (tab === "project") {
    return "项目与配置";
  }
  if (tab === "batch") {
    return "导入与抽取";
  }
  return "类型与图谱";
}

function TabButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={active ? "tab-button tab-button-active" : "tab-button"}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function SectionCard({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <h2>{title}</h2>
          <p className="section-description">{description}</p>
        </div>
        {actions ? <div className="section-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

function StatCard({
  label,
  value,
  tone = "muted",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
    </div>
  );
}

function ContextStrip({
  items,
}: {
  items: Array<{
    label: string;
    value: string;
  }>;
}) {
  return (
    <section className="context-strip" aria-label="当前上下文">
      {items.map((item) => (
        <div key={item.label} className="context-pill">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-block">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}

function StatusBadge({ label, tone }: { label: string; tone: string }) {
  return <span className={`status-badge tone-${tone}`}>{label}</span>;
}

function TripleEditor({
  triples,
  newTripleForm,
  editingTripleId,
  editingTripleForm,
  createBusy,
  updateBusy,
  onNewChange,
  onEditChange,
  onCreate,
  onBeginEdit,
  onCancelEdit,
  onSaveEdit,
  onDelete,
}: {
  triples: Triple[];
  newTripleForm: TripleFormState;
  editingTripleId: string;
  editingTripleForm: TripleFormState;
  createBusy: boolean;
  updateBusy: boolean;
  onNewChange: (field: keyof TripleFormState, value: string) => void;
  onEditChange: (field: keyof TripleFormState, value: string) => void;
  onCreate: () => void;
  onBeginEdit: (triple: Triple) => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onDelete: (triple: Triple) => void;
}) {
  return (
    <div className="stacked-block">
      {triples.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>主体</th>
                <th>主体类型</th>
                <th>关系</th>
                <th>客体</th>
                <th>客体类型</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {triples.map((triple) => {
                const isEditing = triple.id === editingTripleId;
                return (
                  <tr key={triple.id}>
                    <td>
                      {isEditing ? (
                        <input
                          value={editingTripleForm.subject}
                          onChange={(event) => onEditChange("subject", event.target.value)}
                        />
                      ) : (
                        triple.subject
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          value={editingTripleForm.subjectType}
                          onChange={(event) => onEditChange("subjectType", event.target.value)}
                        />
                      ) : (
                        triple.subject_type
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          value={editingTripleForm.predicate}
                          onChange={(event) => onEditChange("predicate", event.target.value)}
                        />
                      ) : (
                        triple.predicate
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          value={editingTripleForm.object}
                          onChange={(event) => onEditChange("object", event.target.value)}
                        />
                      ) : (
                        triple.object
                      )}
                    </td>
                    <td>
                      {isEditing ? (
                        <input
                          value={editingTripleForm.objectType}
                          onChange={(event) => onEditChange("objectType", event.target.value)}
                        />
                      ) : (
                        triple.object_type
                      )}
                    </td>
                    <td>
                      <div className="inline-actions">
                        {isEditing ? (
                          <>
                            <button
                              className="ghost-button"
                              type="button"
                              onClick={onSaveEdit}
                              disabled={updateBusy}
                            >
                              {updateBusy ? "保存中..." : "保存"}
                            </button>
                            <button className="ghost-button" type="button" onClick={onCancelEdit}>
                              取消
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="ghost-button" type="button" onClick={() => onBeginEdit(triple)}>
                              编辑
                            </button>
                            <button className="ghost-button" type="button" onClick={() => onDelete(triple)}>
                              删除
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="暂无三元组" description="可手动新增一条三元组，或先修正模型返回内容后重新解析。" />
      )}

      <div className="subsection">
        <h3>手动新增三元组</h3>
        <div className="form-grid triple-grid">
          <label>
            <span>主体</span>
            <input
              value={newTripleForm.subject}
              onChange={(event) => onNewChange("subject", event.target.value)}
            />
          </label>
          <label>
            <span>主体类型</span>
            <input
              value={newTripleForm.subjectType}
              onChange={(event) => onNewChange("subjectType", event.target.value)}
            />
          </label>
          <label>
            <span>关系</span>
            <input
              value={newTripleForm.predicate}
              onChange={(event) => onNewChange("predicate", event.target.value)}
            />
          </label>
          <label>
            <span>客体</span>
            <input
              value={newTripleForm.object}
              onChange={(event) => onNewChange("object", event.target.value)}
            />
          </label>
          <label>
            <span>客体类型</span>
            <input
              value={newTripleForm.objectType}
              onChange={(event) => onNewChange("objectType", event.target.value)}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="primary-button" type="button" onClick={onCreate} disabled={createBusy}>
            {createBusy ? "新增中..." : "新增三元组"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
