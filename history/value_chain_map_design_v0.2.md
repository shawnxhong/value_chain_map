# 行业结构与价值链研究工具 · 设计文档 v0.2

**项目代号**：Value Chain Map（VCM，原 VCRG）  
**文档版本**：v0.2（基于 v0.1 重定位修订）  
**日期**：2026-06-30  
**定位**：科技股五层分析框架中 **第二层（行业结构与价值链）** 的专用工具

> v0.2 相对 v0.1 的核心变化：**从"通用产业链投资工具"收窄为"第二层地图引擎"**。它产出证据化的产业链地图与公司结构分层名单，并通过标准化接口交棒给第三/四/五层工具。修改逐条依据见 `value_chain_map_revision_notes.md`。

---

## 1. 在五层框架中的定位

科技股分析分五层：① 宏观与流动性 ② **行业结构与价值链** ③ 商业模式与护城河 ④ 公司基本面 ⑤ 估值与定价，最终收窄到个股决策。

**本工具只做第二层。** 第二层的训练目标是：看懂价值链——**利润最终沉淀在谁手里（往往不是最显眼的那一家）**，并理解科技独有的结构性力量：摩尔定律、资本开支周期、技术采纳 S 曲线、平台赢家通吃。

本工具不追求 alpha，不下买卖结论。它是地图，不是罗盘。

---

## 2. 一句话定义

构建一个面向美股的 **证据化产业链地图引擎**，回答三个第二层核心问题：

1. **地形**：一条链上有谁，谁供给谁、谁竞争谁、谁替代谁？
2. **结构位置**：谁是瓶颈、谁是利润沉淀点、谁是被上下游挤压的弱势环节？
3. **结构动力**：需求从哪注入、沿链怎么传导、技术迁移会把利润从哪个环节挪到哪个环节？

产出 = 可视化地图 + 每条边的证据 + 每家公司的"结构画像卡"（移交下一层）。

---

## 3. 范围边界（IN / OUT）

| 维度 | 本工具负责（IN） | 交给别的层（OUT） |
|---|---|---|
| 价值链结构 | 供给/竞争/替代/瓶颈/弱势 | —— |
| 利润池 | **跨环节横向比**毛利/营业利润率/ROIC，定位利润沉淀点 | 单公司估值（第五层） |
| 护城河 | **环节级结构性假设**（高切换成本/赢家通吃倾向） | 公司级护城河深度与可被颠覆性（第三层） |
| 基本面 | 仅用聚合/对比财务指标作结构信号 | 三表勾稽、NRR、40 法则、SBC 稀释、单位经济（第四层） |
| 宏观 | 不分析，仅作输入接入 | 利率/流动性判断（第一层） |
| 最终动作 | 产出分层候选名单 | 个股买卖决策 |

**判定规则**：用财务数据时，是在比较"环节之间"（→第二层，保留）还是分析"一家公司内部"（→交出去）。

---

## 4. 产品目标与成功标准

### 4.1 核心目标

1. **价值链可视化**：以图结构展示公司、产品、技术、终端市场及其关系。
2. **利润池定位**：跨环节横向对比，回答"谁赚走了钱"。
3. **瓶颈与弱势识别**：以证据 checklist 标出供给受限/扩产慢/集中度高的瓶颈，与被双向挤压的弱势环节。
4. **技术迁移刻画**：表达"某技术换代把利润从 A 环节搬到 B 环节"，并标注 S 曲线位置。
5. **证据链管理**：每条关系边绑定来源、原文、时间、置信标签、review 状态。
6. **结构画像输出**：为每家公司生成可移交下一层的结构画像卡。

### 4.2 非目标

不做：自动交易、买卖推荐、短期股价预测、全市场覆盖、公司基本面深挖、估值、复制 Bloomberg/FactSet 数据库。

### 4.3 成功标准（重写）

> 看完一条链的地图，使用者能说清：**谁强谁弱、利润在谁手里、利润正往哪移**——且每一句话都有可追溯出处。

不再以"产生 alpha / 排雷"为成功标准（那是整条工具矩阵的事）。

---

## 5. 层间接口契约（v0.2 新增，核心）

### 5.1 输入接口（其他层 → 本工具）

- **第一层 → 需求潮水状态**：当前 hyperscaler capex 周期处于扩张/收缩、利率环境松紧。MVP 可简化为一个手动设置的全局参数 + 几条 capex 指引证据。决定地图顶端注入的需求强度。

### 5.2 输出接口（本工具 → 三/四/五层）：结构画像卡

每个公司节点产出一张结构化卡片，是本工具最该打磨的交付物：

```yaml
StructuralProfileCard:
  ticker: COHR
  chain: "AI datacenter / optical"
  structural_position: "瓶颈下游受益者（800G 光模块，供给偏紧）"
  profit_pool_tier: medium          # high / medium / low（跨环节相对）
  key_dependencies:
    upstream: "InP / EML 激光芯片（少数供给）"
    downstream: "少数超大厂订单（客户集中度高）"
  tech_migration_risk:              # 服务于"护城河被技术绕过"
    threat: "CPO 共封装光学可能 2–3 年内绕过可插拔模块"
    layer: inference
  structural_thesis: "capex 受益 + 短期供给瓶颈，但客户集中度高 + 技术替代悬顶"
  handoff:
    layer3: "验证护城河深度与可颠覆性"
    layer4: "客户集中度对利润的实际冲击"
    layer5: "—"
  tier: watch                       # consider / watch / structurally_excluded
  evidence_ids: [ev_101, ev_102, ev_103]
```

`tier` 三档把地图收敛成下一步动作：**值得细看 / 待观察 / 结构性排除**。

---

## 6. 科技独有结构性力量（v0.2 一等公民）

v0.1 把图建成静态供应商网络（FactSet/Bloomberg 已有，低差异化）。v0.2 将下列**动态力量**提升为核心建模对象——它们正是利润池会"移动"的原因。

| 力量 | 建模方式 | 服务的判断 |
|---|---|---|
| **技术路线迁移 / S 曲线**（最重要） | `MIGRATES_TO` 边，带 `as_of` 与 S 曲线阶段（早期/陡升/成熟）；如 DDR→HBM、可插拔→CPO、风冷→液冷、铜→光 | 利润在环节间迁移；护城河被新技术绕过 |
| **资本开支周期** | 全局"需求潮水"信号注入链顶；节点标早周期/晚周期受益 | 需求脉冲沿链传导 |
| **赢家通吃 / 集中度** | 每环节标市占率集中度（前三份额 / HHI） | 利润沉淀点、定价权候选 |
| **扩产周期 / 摩尔定律** | 节点属性 `expansion_lead_time`（如先进封装/HBM/电力设备 2–3 年） | 瓶颈核心特征 |

---

## 7. 概念模型（精简）

### 7.1 节点类型（P0 仅前 5 类）

| 节点 | P0 | 示例 |
|---|---|---|
| Company | ✅ | NVDA, TSM, MU, COHR, VRT |
| Product | ✅ | H100, HBM3E, CoWoS, 800G module |
| EndMarket | ✅ | AI datacenter |
| Technology | ✅ | advanced packaging, CPO, liquid cooling |
| Document / Evidence | ✅ | 10-K, transcript, deck |
| Segment / Facility / Commodity / Event / AnalystThesis / Security | 推后 | —— |

### 7.2 边类型（P0 仅 5 种）

| 边 | P0 | 方向 | 含义 |
|---|---|---|---|
| SUPPLIES_TO | ✅ | supplier → customer | 供应（单向存储，反向查询时生成，**不双存 BUYS_FROM**） |
| COMPETES_WITH | ✅ | company ↔ company | 竞争 |
| SERVES_MARKET | ✅ | company/product → market | 终端市场暴露 |
| PRODUCES | ✅ | company → product | 生产 |
| MIGRATES_TO | ✅ | technology/product → technology/product | 技术迁移/替代（带 S 曲线阶段） |
| DEPENDS_ON / USES_TECHNOLOGY / IMPACTS / HAS_THESIS 等 | 推后 | | |

### 7.3 边属性（P0 精简至核心）

```yaml
edge_id: string
relationship_type: enum
source_node_id: string
target_node_id: string
layer: enum                 # fact / estimate / inference / thesis
confidence_label: enum      # high / medium / low（不存连续分数）
confidence_reason: string   # 一句话：为什么是这个标签
as_of_date: date            # 证据发布日，用于失效提示（强制）
status: enum                # candidate / confirmed / deprecated / rejected
evidence_ids: [string]
# 以下按需，非 P0 必填：
concentration_pct: range | null   # 占比/集中度（如客户占 23%）
created_by: enum            # llm_agent / human / import
notes: string
```

### 7.4 证据模型（P0 字段）

```yaml
Evidence:
  evidence_id: string
  source_type: enum     # SEC_filing / transcript / presentation / press / news
  title: string
  published_at: datetime
  url | accession_number: string | null
  excerpt: string
  excerpt_hash: string
  extraction_method: enum  # rule / llm / human
```

### 7.5 图层（保留 v0.1 的四层）

```
Layer 0 Identity：company / ticker / CIK / 别名 / 并购史
Layer 1 Fact：有直接 excerpt 支持的关系
Layer 2 Estimate：多源推断的占比/暴露
Layer 3 Inference：传导路径、利润池迁移、技术替代影响
Layer 4 Thesis：人工/agent 的结构性论点
```

UI 必须让 inference/thesis 边**视觉虚化**，与 fact 边明显区分。

---

## 8. 系统架构（精简）

```mermaid
flowchart TD
    A[Sources: transcript/deck P0 · 10-K · XBRL] --> B[Parse & Chunk]
    B --> C[LLM 结构化抽取 + 校验]
    C --> D[Entity Resolution]
    D --> E[Evidence Binding]
    E --> F[Staging Graph]
    F --> G[人工 Review]
    G --> H[Production Graph (Kuzu/Postgres)]
    H --> I[结构分析: 利润池/瓶颈/弱势/技术迁移]
    H --> J[结构画像卡生成]
    H --> K[可视化 UI]
    I --> J
```

**模块**：Source Manager / Document Parser / Relation Extractor（含校验）/ Entity Resolver / Evidence Store / Graph Store / Review Console / Structural Analytics / Profile Card Generator / UI。

---

## 9. LLM 使用（去 agent 化）

### 9.1 P0：确定性流水线，不做多 agent 编排

P0 只需两个 prompt + 人工 review：

1. **抽取 prompt**：从 chunk 输出结构化候选边（含 evidence excerpt、layer、confidence_label、reasoning）。
2. **校验 prompt**：检查每条候选边是否被 excerpt 真实支持；禁止把 likely/may 改写为确定关系。

→ staging → 人工 review → production。Planner / Source Discovery / Diff / Analyst 等多 agent **推后到 P1+**。

### 9.2 LLM 输出契约

```json
{
  "candidate_edges": [{
    "source": "Microsoft",
    "target": "NVIDIA",
    "relationship_type": "SUPPLIES_TO",
    "layer": "inference",
    "evidence_ids": ["ev_123"],
    "confidence_label": "low",
    "confidence_reason": "MSFT 披露 AI capex 增长，但未披露对 NVDA 的直接采购比例",
    "as_of_date": "2026-04-25"
  }]
}
```

**禁止**：无 evidence 的 fact 边；把推理写成事实；改写不确定措辞；自动覆盖人工确认边；丢弃旧版本。

---

## 10. 结构分析能力（重写：只打结构位置分）

只保留三个**纯结构分**，全部为**证据驱动 checklist**，不输出加权小数。

### 10.1 Profit Pool（利润池）
跨同链环节横向排名：毛利率 / 营业利润率 / ROIC + 集中度。输出为热力图与排名，**纯比较，不预设买卖**。

### 10.2 Bottleneck（瓶颈）
checklist（命中几项 + 原文）：供给受限 / 扩产周期长 / 集中度高 / 下游明确提到 supply constraint / 短期无替代 / 客户愿预付或签长协。

### 10.3 Weak Link（弱势）
checklist：低毛利 / 上下游双向强势 / 产品同质化 / 价格接受者 / 单一大客户或单一产品 / 替代品多。

> 展示形式：`Bottleneck 4/6 命中` + 每项对应 excerpt，而非 `0.71`。三分共同支撑结构画像卡的 `profit_pool_tier` 与 `tier`。

### 10.4 路径与传导
```
capex 上修 → AI datacenter buildout → GPU 需求 → HBM 需求 → 先进封装需求 → 电力/散热需求
```
每条路径返回：path nodes/edges、layer、置信标签、证据、暴露的美股公司、可能受益/受损方、技术迁移影响、open questions。

---

## 11. 数据源（优先级倒置）

| 数据源 | v0.2 优先级 | 用途 |
|---|---|---|
| Earnings call transcript | **P0** | 瓶颈、定价权、供需、客户评论——对结构判断最有用 |
| Investor presentation / deck | **P0** | 产品、客户行业、TAM、产业链图、技术路线 |
| SEC XBRL Company Facts | **P0** | 跨环节横向财务对比（利润池） |
| SEC 10-K / 10-Q | P0（限定用途） | identity 层 + 客户集中度占比（ASC 280）+ 风险因素 |
| Press / News | P1 | 订单、客户切换、供应链事件（需来源质量评分） |
| Wikipedia / Wikidata | P1 | 实体冷启动、别名、并购 |

### 11.1 匿名大客户解析（一等公民）

ASC 280 常只披露"某客户占 23%"而不披露名字。`某客户占 X%` 是 10-K 最可靠的产业链信号。建模为：

```
AnonymousMajorCustomer_<CompanyX>_FY2025  (concentration_pct: 23%)
```

后续用 transcript/deck/news 尝试解析真实身份；**LLM 猜测不得直接写入 fact 层**，只能进 estimate/inference。

---

## 12. 技术选型（MVP 降配）

| 层 | v0.2 推荐 | 原因 |
|---|---|---|
| 语言 | Python | 生态最佳 |
| 图存储 | **Kuzu**（嵌入式）或 Postgres+NetworkX | 50–500 边规模下 Neo4j 过重；零运维，匹配个人研究者 |
| 图算法 | NetworkX / igraph | 中心性、路径、集中度 |
| 关系数据 | PostgreSQL（+ pgvector 可选） | 文档元数据、review 状态、向量召回 |
| 文档解析 | Docling + Unstructured | PDF/HTML/PPT/表格 |
| 抽取 | Pydantic schema + LLM structured output | 强约束、易校验 |
| 前端 | React + Cytoscape.js | 交互式图谱 |
| 部署 | 本地优先 / Docker Compose | 个人版离线可用 |

> Neo4j / Memgraph / LangGraph 多 agent / Qdrant / Prefect 等推迟到协作版（团队场景）。

---

## 13. MVP 设计（收窄到一条子链）

### 13.1 范围
**一条子链打透**：`HBM → 先进封装(CoWoS) → GPU → 超大厂`。技术迁移（HBM3E→HBM4、CoWoS 产能、可插拔→CPO）与瓶颈（HBM、先进封装扩产周期）都典型，最能展示动态建模价值。

### 13.2 交付物（按价值排序）
1. **这条链的利润池热力图**（谁赚走钱）——最快出价值，几乎不靠图。
2. **瓶颈 / 弱势 checklist**（证据驱动）。
3. **技术迁移视图**（利润正往哪移）——核心差异化。
4. 可视化图 + 点击边看原文证据。
5. **每家公司结构画像卡**——工具矩阵接口。

### 13.3 P0 功能
- seed list 入库（~30 节点）；transcript/deck 手动导入 + 10-K/XBRL 拉取；文档解析；LLM 抽取候选边（两段式 + 校验）；evidence 绑定；Kuzu 入库；staging review console；图可视化 + 边证据；利润池横向比；结构画像卡生成。

### 13.4 P1 / P2
- P1：每周 filings/news 增量监控、graph diff、失效提示、技术迁移视图自动更新、结构分 checklist 自动化。
- P2：link prediction、多子链/多行业 schema、事件传播、API export、与三/四/五层工具的接口联调。

---

## 14. 数据质量与评估

### 14.1 抽取质量指标
Faithfulness（原文支持）、Precision、Recall、Entity Resolution Accuracy、Layer Correctness、Temporal Correctness。

### 14.2 黄金集（尽早建）
针对 HBM→封装→GPU 子链，人工标注 **20–30 条黄金关系**；每次改 prompt 跑 precision/recall，判断抽取在变好还是变坏。

### 14.3 置信标签（去公式）
离散 high / medium / low，由两维决定：
- 来源类型：SEC filing > deck > transcript > news；
- 表述直接性：直接命名 > 匿名占比 > 推断。

附 `confidence_reason` 一句话。**不输出连续小数**（避免伪精确）。

### 14.4 失效管理
每条边带 `as_of_date`；UI 默认提示"该关系最后验证于 N 个月前"，超阈值标灰待复核。

---

## 15. UI 草案

- **多视图**：Company view / Product chain view / End market view / Bottleneck view / Profit pool view（按毛利/ROIC 着色）/ **Tech migration view（利润迁移）** / Weak link view。
- **边详情面板**：relationship、layer（视觉虚化区分）、confidence label + reason、as_of 与失效提示、economic direction、concentration、evidence excerpts、review status。
- **结构画像卡面板**：每家公司一张卡，含 tier 与 handoff 建议。

---

## 16. 关键设计决策

1. **定位为第二层地图引擎**——产出地图与结构名单，不产出买卖结论；最终个股决策由五层矩阵整体完成。
2. **动态结构力量优先于静态供应商网络**——技术迁移/S曲线/capex周期/集中度是核心，否则与商业数据库无差异。
3. **财务数据只作跨环节横向比**——利润池属第二层；公司内部分析交第四/五层。
4. **打分去公式化**——结构位置分用证据 checklist + 离散标签，反对伪精确。
5. **MVP 用嵌入式图库 + 确定性流水线**——降低工程与运维成本，先证明价值。
6. **结构画像卡是工具矩阵的咬合点**——优先打磨。
7. **production/staging 分离、四层证据模型、LLM 不直接写主图**——继承自 v0.1。

---

## 17. 风险与应对（按重定位调整）

| 风险 | 应对 |
|---|---|
| LLM 幻觉关系 | evidence mandatory + staging + 人工 review |
| 公开数据不完整 | 区分 anonymous/estimated；transcript/deck 为 P0 提升关系密度 |
| 沦为静态供应商图（无差异化） | 把技术迁移/集中度/capex 周期建成一等公民 |
| 越界做了第四/五层 | 严守 IN/OUT 边界；财务仅作横向比 |
| 置信度伪精确 | 离散标签 + 理由，不显示小数 |
| 关系失效 | as_of_date + 失效提示 |
| transcript 获取成本 | P0 允许手动导入；商业源推后 |
| 工程过重 | Kuzu + 确定性流水线 + 单子链 |

---

## 18. 工程路线图

- **Phase 0（1–2 周）技术验证**：拉 5–10 家公司 transcript/10-K/XBRL → 解析 → LLM 抽取 + 校验 → Kuzu 入库 → Cytoscape 展示 → 点击边看 evidence。
- **Phase 1（3–6 周）单子链 MVP**：HBM→封装→GPU 子链 ~30 节点；利润池热力图；瓶颈/弱势 checklist；技术迁移视图；结构画像卡；review console；黄金集评估。
- **Phase 2（6–10 周）增量与接口**：每周监控 + diff + 失效提示；与三/四/五层工具的输入/输出接口；多子链扩展。
- **Phase 3（10 周+）多行业**：半导体设备、电力设备、光模块、电池等子链；link prediction；API export。

---

## 19. 给评审的问题清单

1. 重定位为"第二层地图引擎"、成功标准改为"说清强弱/利润位置/利润迁移且句句有出处"——是否认同？
2. 结构画像卡字段是否完备？作为层间接口是否够用？
3. 技术迁移/S曲线/capex周期/集中度作为一等公民，是否同意优先于静态供应商网络？
4. transcript/deck 为 P0 在工程获取上是否可行？
5. schema 收缩到 5 节点 5 边是否过激？哪些应更早加回？
6. 打分去公式化是否牺牲可比较性？如何在不伪精确下支持排序？
7. MVP 单子链选 HBM→封装→GPU 是否合适？
