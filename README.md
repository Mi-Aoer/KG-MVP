# 通用领域知识图谱构建系统 2.0

当前仓库的一期目标只做“知识图谱构建闭环”，不包含问答功能。

主链路固定为：

`txt 批量导入 -> 大模型三元组抽取 -> 结果修正 -> schema 生成/维护 -> Neo4j 导入`

当前唯一基准文档：

- `docs/需求说明书_修订版.md`
- `docs/系统设计文档_修订版.md`
- `docs/开发任务拆解书_修订版.md`
- `docs/项目开发进度记录.md`

## 技术栈

- 后端：FastAPI
- 前端：React + Vite 单页应用
- 业务元数据：SQLite
- 图数据库：Neo4j
- 运行方式：本地单机 MVP

## 目录

```text
backend/   FastAPI 后端与 SQLite / Neo4j / LLM 接入
frontend/  React 单页前端
data/      演示样例、测试数据、SQLite 数据文件
docs/      修订版主文档、进度记录、交付补充文档
```

## 环境要求

- Python 3.11
- Node.js 20+
- npm 10+
- 本地 Neo4j 5+

## 后端启动

推荐使用长期稳妥脚本（规避 iCloud `dataless` 占位文件导致的导入卡顿）：

```bash
bash backend/scripts/start_backend_stable.sh
```

可选参数示例：

```bash
KGQA_BACKEND_VENV=$HOME/.venvs/kg-mvp-backend-py311 \
HOST=127.0.0.1 \
PORT=8000 \
RELOAD=1 \
bash backend/scripts/start_backend_stable.sh
```

脚本行为：

- 默认使用项目目录外虚拟环境：`$HOME/.venvs/kg-mvp-backend-py311`
- 首次自动创建 `venv`；`requirements.txt` 变更时自动重新安装依赖
- 启动前检测 `backend/app` 中的 iCloud `dataless` 文件并给出明确报错
- 自动清理 `backend/app/__pycache__`，降低损坏 `pyc` 导致的启动阻塞概率

传统方式（可选）：

```bash
cd backend
source .venv/bin/activate
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

访问地址：

- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认前端会请求 `http://127.0.0.1:8000/api`。
如需修改，使用：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

## Neo4j 启动

确保本机 Neo4j 可访问：

- Browser：`http://localhost:7474`
- Bolt：`bolt://localhost:7687`

默认配置见 `backend/.env.example`：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=xpsdd520
```

## `.env` 示例

`backend/.env.example`

```env
APP_NAME=kg-mvp
APP_ENV=dev
DEBUG=true
SQLITE_URL=sqlite:///../data/app.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=xpsdd520
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## 抽取配置说明

抽取模型配置保存在业务库中，不通过 `.env` 固定写死。
推荐真实验收组合：

- `base_url=https://api.siliconflow.cn/v1`
- `model_name=deepseek-ai/DeepSeek-V3.2`
- `provider_options={"temperature":0.6,"top_p":0.95,"max_tokens":256}`

`api_key` 请在页面或接口创建配置时传入，不要写入 Git 跟踪文件。

## 演示数据

- txt 样例：`data/军事新闻实体关系抽取_前10条_系统导入输入.txt`
- 可直接使用的 instruction：`data/军事新闻实体关系抽取_instruction_系统可直接使用.txt`
- mock 数据集：`data/军事新闻实体关系抽取数据集_1000条.json`

当前 `mock://extract` 逻辑说明：

- 按 `input_text` 匹配军事数据集中的 `input` 返回结果。
- 数据集中原始 `head/head_type/relation/tail/tail_type` 会在 mock 层自动映射为系统标准字段：
  `subject/subject_type/predicate/object/object_type`。
- 若未命中数据集，mock 返回 `[]`。

## 开发验收顺序

建议按下列顺序执行：

1. 启动 Neo4j、后端、前端。
2. 先用 `mock://extract` 完成一遍主链路。
3. 再切换到真实 provider 做 `SiliconFlow + DeepSeek-V3.2` 验收。
4. 完成 `raw_response` 修正、reparse、手工三元组编辑。
5. refresh schema，验证类型/关系维护。
6. 执行 `graph/init`、`graph/import`、`graph/rebuild`。
7. 删除项目，确认 SQLite 与 Neo4j 数据被清理。

## 最小自动化测试

在后端目录执行：

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

当前测试覆盖：

- `parse_service`
- `batch_service`
- `schema_service`
- `graph_service`
- `llm_client`

## 当前交付范围

当前一期只交付图谱构建闭环，不交付以下内容：

- 问答页
- 问答接口
- Cypher 生成与安全执行链路
- 问答日志

如需恢复问答功能，必须新增独立版本的需求、设计、任务和验收文档。

## 接口说明

接口简表见：

- `docs/接口说明简表.md`

Swagger 仍是最完整的在线接口说明入口。

## 常见问题排查

- 前端报跨域：检查 `backend/.env` 中 `CORS_ORIGINS` 是否包含前端地址。
- `graph/init` 失败：先确认 Neo4j Browser 和 Bolt 都可连通。
- 真实抽取输出混入解释文本：优先使用 `deepseek-ai/DeepSeek-V3.2`，不要把 `DeepSeek-R1` 当作当前默认结构化抽取模型。
- `pytest` 无法导入应用：请从 `backend/` 目录执行 `python -m pytest`。
- 前端真实联调失败：先用 mock 配置完成一遍链路，再切换真实 provider 排查。
- mock 抽取大量返回空数组：检查上传 txt 每一行是否与 `data/军事新闻实体关系抽取数据集_1000条.json` 的 `input` 可匹配（至少内容一致）。

## 许可

本仓库附带 `LICENSE` 文件。
