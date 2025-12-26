# 联网研报最小 MVP 规划文档

> 目标：在现有“智能研报”功能基础上，增加**可选的联网检索能力**，让本地 / 云端模型在生成研报时，能够基于**实时互联网信息**进行分析，同时保证可验证性与稳定性。

---

## 一、现状梳理（基于当前代码结构）

### 1. 后端结构

- 主要研报相关代码位置（已在项目中确认）：
  - 路由：`src/api/routes/report_generator_api.py`
  - 服务：`src/services/report_generator/service.py`
  - Provider 体系：`src/providers/factory.py`、`src/providers/base.py` 及具体 Handler
  - 热点话题：`src/services/hot_topics/service.py`（命名推断，需按实际文件确认）
- 后端通过 `backend_main.py` 将 `report_generator_api.router` 挂载到：
  - `prefix="/api/v1/reports"`

### 2. 当前研报生成逻辑的关键特点

- `ReportGeneratorService` 中已经存在“网络搜索摘要”相关文案，例如：
  - 注释：
    - “调用Ollama Local LLM来根据搜索结果生成研报内容。”
  - Prompt 片���：
    - “以下是相关的网络搜索摘要作为参考资料：\n\n”
- 但在当前代码中：
  - 尚未发现**必然进行外部 HTTP 搜索 / 抓取**的实现；
  - 更像是“为未来的网络搜索预留了占位文案”，当前主要仍是**模型基于 topic + 结构化提示词直接生成研报**。
- 因此，现在的“智能研报”本质是：
  - **离线大模型生成 + 固定结构的系统提示**；
  - 暂无保证“研报内容一定来源于实时互联网信息”的机制。

> 以上结论基于对现有 Python 源码的静态搜索与阅读，而非运行时行为推断。

---

## 二、MVP 的功能目标与非目标

### 1. 功能目标

1. 在生成研报前，后端能够：
   - 根据研报主题 `topic` 调用一个**统一的网络搜索服务**；
   - 获取若干条与主题相关的**简短摘要 + 标题 + 来源 URL**；
   - 将这些信息整合为“网络知识摘要”，作为额外上下文注入到 LLM 提示词中。

2. 支持两类模型：
   - **本地模型（如 Ollama）**：通过已有 Provider 体系调用，例如 `gemma3:4b`；
   - **云端模型**：做法与当前云端 Provider 一致，只在 Prompt 中多加入“网络摘要”。

3. 在网络不可用或搜索失败时：
   - **不影响研报生成主流程**，而是自动降级为“纯模型生成”；
   - 同时在提示词中显式告诉模型“未获取到可靠网络信息，请避免虚构具体数据/来源”。

### 2. 非目标（MVP 阶段刻意不做）

1. 不做复杂的多轮检索 / RAG 向量索引，仅做**单次 Web 搜索 + 结果摘要**；
2. 不在前端增加复杂配置（MVP 阶段可以默认 `use_web=True` 或后端配置开关）；
3. 不追求覆盖所有信息源，只要能从一个稳定的搜索 / 新闻 API 获得简要信息即可；
4. 不实现长周期缓存 / 离线任务调度（后续可以在 data 目录中增加搜索缓存）。

---

## 三、整体架构设计

### 1. 新增组件概览

在现有架构基础上新增一个“网络搜索服务层”：

```text
前端（智能研报页面）
    ↓  POST /api/v1/reports/...
FastAPI 路由：report_generator_api
    ↓  调用 ReportGeneratorService
ReportGeneratorService
    1) 调用 WebSearchService.web_search_summary(topic)
    2) 将 summary 注入到 LLM Prompt
    3) 通过 providers 调用本地/云端模型
    ↓
Provider Handler (Ollama / Cloud)
    ↓
模型输出研报 Markdown
```

### 2. 新增模块建议

- 新建模块：`src/services/report_generator/web_search_service.py`
  - 职责：
    - 对外暴露一个简单的异步函数：
      - `async def web_search_summary(topic: str) -> str`
    - 内部基于 `httpx.AsyncClient` 调用一个 Web 搜索 / 新闻 API；
    - 把返回的若干条结果格式化为 Markdown 列表，附带来源链接；
    - 异常和空结果时，返回明确的 fallback 文本，而不是抛异常。

> httpx 的异步用法参考其官方文档 v0.28.x：
> - 官方文档 URL：https://www.python-httpx.org/async/
> - 推荐写法：`async with httpx.AsyncClient() as client:` / `await client.get(...)`。

- 在 `src/services/report_generator/service.py` 中：
  - 注入 `web_search_summary` 的调用逻辑；
  - 调整 `system_prompt` / `user_prompt`，在合适位置插入搜索摘要文本。

### 3. 对现有系统的影响

- 与现有的 `providers` 层保持解耦：
  - Web 搜索只产生一段**纯文本摘要**，不直接与特定模型绑定；
  - Provider 层的职责仍然是“把 prompt 发送给具体模型并返回结果”。

- 对现有 API 契约影响极小：
  - 前端请求体不必修改（MVP 阶段可默认开启联网搜索）；
  - 响应结构保持现状：依旧返回 `report_content: str`（Markdown）。

---

## 四、WebSearchService 设计细节

### 1. 函数签��与输入输出

```python
async def web_search_summary(topic: str) -> str:
    """根据研报主题进行一次网络搜索，返回 Markdown 格式的摘要文本。
    - 输入：主题字符串，如 "人工智能的最新进展"。
    - 输出：适合直接注入到 LLM Prompt 的 Markdown 文本，包含标题、简要摘要和来源 URL。
    - 失败 or 空结果：返回带有明确信息的 fallback 文本，而不是抛异常。
    """
```

### 2. 内部逻辑（伪流程）

1. 构造搜索请求：
   - 可以使用一个简单的 HTTP 搜索 API（MVP 阶段可配置在 `.env` 或 `config` 中）。
   - 拼接查询参数：`q=topic`、`lang=zh`、`limit=N` 等。

2. 发起异步请求（基于 httpx）：
   - `async with httpx.AsyncClient(timeout=...) as client:`
   - `resp = await client.get(search_url, params=...)`
   - 检查 `resp.status_code` 与 `resp.json()` 结构。

3. 提取并格式化结果：
   - 对每条结果，提取：
     - `title`（标题）
     - `snippet` / `summary`（摘要）
     - `url`（来源链接）
   - 转为 Markdown 列表，例如：

     ```markdown
     - [标题1](https://example.com/1)：摘要1...
     - [标题2](https://example.com/2)：摘要2...
     ```

4. 错误处理与回退逻辑：
   - 网络异常 / 超时 / 4xx / 5xx：
     - 记录错误日志（不会中断整体研报生成）；
     - 返回文本：如“当前未能从网络获取到与主题『X』相关的可靠摘要，请模型仅基于已有知识进行概括，并避免给出具体日期或未验证的数据源”。

### 3. 配置与安全

- 在 `config` 或 `.env` 中增加：
  - 搜索 API 的基址：`WEB_SEARCH_API_BASE`；
  - API Key：`WEB_SEARCH_API_KEY`（如需要）；
  - 默认返回条数：`WEB_SEARCH_RESULT_LIMIT`。

- 不在日志中输出完整 URL + Query（避免潜在敏感信息泄漏），仅记录必要的统计信息与错误码。

---

## 五、研报生成服务改造方案

### 1. 与现有 ReportGeneratorService 集成

在 `ReportGeneratorService` 的研报生成主函数中（例如 `generate_report` 或类似方法），增加如下步骤：

1. 在构造 Prompt 之前调用：

   ```python
   # 伪代码
   web_summary = await web_search_summary(request.topic)
   ```

2. 更新 Prompt 设计：

   - `system_prompt` 中强调：
     - 模型需要基于“下方网络搜索摘要 + 自身已有知识”进行分析；
     - 引用网络信息时，尽量在段落中通过自然语言提及来源（如“根据某科技媒体 2025 年报道...”）；
     - 避免虚构不存在的机构/时间/数据。

   - `user_prompt` 中插入搜索摘要区域，例如：

     ```text
     研报主题："{topic}"

     以下是与该主题相关的网络搜索摘要，请在撰写研报时优先参考：

     {web_summary}

     请基于上述资料和你的专业知识，按照指定结构撰写完整的 Markdown 格式研报。
     ```

3. 回退场景处理：

   - 若 `web_summary` 是回退文本（未获取到实际链接 / 标题）：
     - Prompt 中在该段显式说明，让模型谨慎表述，并避免伪造来源；
     - 整个生成过程仍然照常进行。

### 2. 本地 / 云端模型共用逻辑

- `ReportGeneratorService` 不需要区分“本地 Ollama / 云端 API”，只需：
  - 通过现有 Provider Factory 按配置得到一个 handler；
  - 把 `system_prompt + user_prompt` 传给 handler。

- Provider 层仅负责：
  - 将 prompt 转为对应模型 API 调用格式；
  - 返回生成的 Markdown 文本，不关心搜索来源。

---

## 六、可验证性与风险控制

### 1. 可验证性设计

1. **保留原始来源 URL**：
   - 搜索摘要中用 `[标题](URL)` 格式，使人工可以快速跳转验证；
2. **区分“基于搜索”与“模型推断”**：
   - 在 Prompt 中要求模型，在提到具体数据 / 事件时，优先引用出现在搜索摘要中的内容；
   - 对未在摘要中出现的信息使用更模糊的表述（如“近几年”、“有研究指出”等）。

### 2. 失败与边界情况

- 网络不可用 / API Key 失效：
  - WebSearchService 记录错误日志，返回回退文本；
  - 研报生成功能不受影响，只是信息新鲜度下降。

- 搜索结果噪声过多：
  - 可在后续迭代中增加：
    - 结果去重；
    - 基于简单规则过滤广告/低质量站点。

---

## 七、后续迭代方向（超出 MVP 范围，仅做规划）

1. **前端加入“是否启用联网”开关**：
   - 在智能研报页面增加“使用网络数据”复选框；
   - 在后端请求模型中加入 `use_web: bool` 字段。

2. **引入本地缓存与增量更新**：
   - 将同一主题在一定时间窗口内的搜索结果缓存到 `data/` 目录；
   - 减少对外搜索 API 调用，提升响应速度。

3. **向量检索 / 文档库集成**：
   - 将搜索结果进一步向量化，并与本地文档（如上传的 PDF、研报历史）结合做 RAG；
   - 需要引入额外依赖（如 `faiss` / `chromadb` / `qdrant`）。

4. **针对领域的专用信���源适配器**：
   - 为财经、科技等具体场景编写专门的信息源适配器（券商 API、新闻源等）；
   - 在 WebSearchService 内部根据 `topic` 分类路由不同信息源。

---

## 八、实施优先级建议

1. **P0：打通最小搜索链路**
   - 新建 `web_search_service.py`，使用一个公开搜索 API 或占位接口；
   - `ReportGeneratorService` 接入 `web_search_summary`，实现最小可用版本；
   - 确认在正常 / 网络异常时，研报均可生成。

2. **P1：Prompt 调优与安全性增强**
   - 优化 system / user prompt 文案，减少模型幻觉；
   - 在日志中记录“使用了多少条搜索结果”、“是否命中缓存”等信息。

3. **P2：前端控制与配置管理**
   - 前端加入“开启联网”开关；
   - 后端支持通过配置关闭联网（例如在无网环境部署时直接走离线模式）。

4. **P3：信息源扩展与缓存机制**
   - 针对不同主题类型扩展更多信息源；
   - 引入缓存层与简单的质量过滤逻辑。

---

> 本文档仅规划架构与实现思路，不包含具体 API Key 或外部服务选择。实际落地时需结合公司合规要求与部署环境选择合适的信息源与鉴权方式。