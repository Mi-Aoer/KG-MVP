function makeSuffix(): string {
  const now = new Date();
  const datePart = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(
    now.getDate(),
  ).padStart(2, "0")}`;
  const timePart = `${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(
    2,
    "0",
  )}${String(now.getSeconds()).padStart(2, "0")}`;
  return `${datePart}-${timePart}`;
}

export function buildDemoConfigDraft() {
  return {
    name: `抽取配置-${makeSuffix()}`,
    baseUrl: "",
    apiKey: "",
    modelName: "",
    timeoutSeconds: "180",
    maxTokens: "1024",
    providerOptionsText: "",
  };
}

export function buildDemoProjectDraft(defaultConfigId = "") {
  return {
    name: `项目-${makeSuffix()}`,
    description: "用于管理当前业务数据的抽取与图谱处理流程",
    extractConfigId: defaultConfigId,
  };
}

export const DEMO_SAMPLE_FILE_HINT =
  "支持 UTF-8 编码的 .txt 文件";

export const DEMO_INSTRUCTION = `你是一名军事新闻关系三元组抽取专家。你的任务是从输入文本中抽取关系，并输出 JSON 数组。

实体类型定义：
- Actor：国家、军队、部队、人员、组织、机构、媒体等行动主体。
- Asset：舰艇、飞机、导弹、雷达、基地设施、装备平台，以及报道中的事件性对象。
- Time：日期、时点、时段、相对时间表达。
- Place：国家、城市、海域、基地、地区、地点。
- Number：人数、数量、规模、时长、吨位等数量表达。

关系定义与方向约束：
- tested_by：通常是 Asset -> Actor，表示装备或平台由某组织进行试验、验收、海试、接装训练或测试。
- provided_by：通常是 Asset -> Actor 或 Place，表示该装备由谁提供、出租、交付，或来自哪里。
- provided_to：通常是 Asset -> Actor 或 Place，表示该装备被提供、出租、交付给谁，或交付到哪里。
- deployed_by：通常是 Asset -> Actor，表示该装备或力量由谁部署、派出、操作或掌控。
- deployed_to：通常是 Asset -> Place，表示该装备或力量部署、驶往、驻扎或前往哪里。
- occurs_on：通常是 Asset 或 Actor -> Time，表示该实体在报道事件中与某时间直接关联。
- occurs_at：通常是 Asset 或 Actor -> Place，表示该实体在报道事件中与某地点直接关联。
- has_count：通常是 Actor 或 Asset -> Number，表示人数、数量、规模、时长、吨位等。
- targeted_at：通常是 Actor 或 Asset -> Actor 或 Asset，表示针对、打击、瞄准、牵制等目标关系。
- equipped_with：通常是 Asset -> Asset，表示搭载、配备、换装另一装备或武器。
- incident_with：通常是 Actor 或 Asset -> Actor 或 Asset，表示事故、故障、冲突、伤亡等事件中的直接关联对象。

输出要求：
1. 只输出一个 JSON 数组，不要输出任何解释、注释、Markdown 代码块或额外文本。
2. 数组中的每个元素必须是一个对象，且必须包含且仅包含以下 5 个字段：
   - "subject"
   - "subject_type"
   - "predicate"
   - "object"
   - "object_type"
3. subject_type 和 object_type 必须属于：Actor、Asset、Time、Place、Number。
4. predicate 必须来自给定关系集合。
5. 若没有可抽取关系，输出 []。

以下是新闻文本：`;
