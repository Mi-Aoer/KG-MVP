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
    name: `CMeIE演示抽取配置-${makeSuffix()}`,
    baseUrl: "mock://extract",
    apiKey: "demo-key",
    modelName: "mock-cmeie-v2",
    timeoutSeconds: "60",
    providerOptionsText: "",
  };
}

export function buildDemoProjectDraft(defaultConfigId = "") {
  return {
    name: `CMeIE演示项目-${makeSuffix()}`,
    description: "使用 CMeIE 前10条样例与数据驱动 mock 的一期演示项目",
    extractConfigId: defaultConfigId,
  };
}

export const DEMO_SAMPLE_FILE_HINT =
  "建议上传 data/CMeIE-V2_前10条_系统导入输入.txt 作为演示样例。";

export const DEMO_INSTRUCTION = `你是一个医学文本三元组抽取助手。请从给定文本中抽取所有能够被原文直接支持的关系三元组，并严格按要求输出。

输出要求：
1. 只输出一个 JSON 数组，不要输出任何解释、注释、Markdown 代码块或额外文本。
2. 数组中的每个元素都必须是一个对象，且只能包含以下 5 个字段：
   - "subject"
   - "subject_type"
   - "predicate"
   - "object"
   - "object_type"
3. 输出示例：
[
  {
    "subject": "失眠症",
    "subject_type": "疾病",
    "predicate": "辅助治疗",
    "object": "引导意象和冥想",
    "object_type": "其他治疗"
  }
]
4. 如果文本中没有可以确定的关系，输出空数组：[]

抽取规则：
1. 所有三元组都必须能从原文中直接找到依据，不允许凭常识补充、猜测或改写。
2. subject 和 object 必须尽量使用原文中的连续片段。
3. 同一条完全重复的三元组只保留一次。
4. 如果句子是否定、排除、不确定或仅作可能性描述，则不要抽取该关系。
5. 实体类型和关系类型使用简洁中文描述，例如：疾病、症状、药物、检查、其他治疗、临床表现、病因、辅助治疗、检查方法等。
6. 如果文本中包含多个明确关系，应全部分别输出。
7. 不要返回键名缩写，不要使用 s、p、o，必须使用完整字段名：
   subject、subject_type、predicate、object、object_type。

现在请只根据输入文本内容输出结果 JSON 数组。`;
