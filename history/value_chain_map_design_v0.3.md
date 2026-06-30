# 行业结构与价值链研究工具 · 设计文档 v0.3

**项目代号**：Value Chain Map（VCM，原 VCRG）
**文档版本**：v0.3（在 v0.2 基础上，合并 GPT 复审意见与 Claude 二次裁决）
**日期**：2026-06-30
**定位**：科技股五层分析框架中 **第二层（行业结构与价值链）** 的地图引擎

> **v0.3 相对 v0.2 的变化**
> 1. 恢复 **negative screening / 结构性排除** 为第二层核心价值，改写成功标准。
> 2. P0 schema 增加 **ValueChainStage** 节点（环节级建模），新增 `BELONGS_TO_STAGE` 边。
> 3. 结构画像卡新增 `investability`、`chain_exposure`、`open_questions`，并以 `tier` 为唯一裁决字段。
> 4. 显式建模 `economic_direction`（谁为谁付钱），仅对 `SUPPLIES_TO` 强制。
> 5. 置信度 UI 去小数，内部保留 **两个独立序数 rank**（严禁合成单一分数）。
> 6. Phase 0 改为 **relational-first**（Postgres/SQLite + NetworkX + Cytoscape），Kuzu/Neo4j 推后。
>
> 评审与裁决依据见 `value_chain_map_revision_notes.md`（Claude 一审）与 `value_chain_map_gpt_review_notes.md`（GPT 复审）。

---

## 1. 在五层框架中的定位

科技股分析分五层：① 宏观与流动性 ② **行业结构与价值链** ③ 商业模式与护城河 ④ 公司基本面 ⑤ 估值与定价，最终收窄到个股决策。

**本工具只做第二层。** 第二层的训练目标是：看懂价值链——**利润最终沉淀在谁手里（往往不是最显眼的那一家）**，并理解科技独有的结构性力量：摩尔定律、资本开支周期、技术采纳 S 曲线、平台赢家通吃。

> 它是地图 + 地形强弱判断，不是最终买卖信号。

它负责把公司分为 `consider / watch / structurally_excluded`，作为第三、四、五层的输入；它不下买卖结论。

---

## 2. 一句话定义

构建一个面向美股的 **证据化产业链地图引擎**，回答四个第二层核心问题：

1. **地形**：一条链上有哪些环节，谁供给谁、谁竞争谁、谁替代谁？
2. **结构位置**：谁是瓶颈、谁是利润沉淀点、谁是被上下游挤压的弱势环节？
3. **结构动力**：需求从哪注入、沿链怎么传导、技术迁移会把利润从哪个环节挪到哪个环节？
4. **取舍分层**：哪些公司值得进入下一层深挖，哪些应暂缓或结构性排除？

产出 = 可视化地图（交互界面）+ 每条边的证据 + **结构画像卡（标准输出）**。

> 地图是交互界面，结构画像卡是标准输出。

---

## 3. 范围边界（IN / OUT）

| 维度 | 本工具负责（IN，第二层） | 交给别的层（OUT） |
|---|---|---|
| 价值链结构 | 供给/竞争/替代/瓶颈/弱势 | —— |
| 利润池 | **跨环节横向比**毛利/营业利润率/ROIC，定位利润沉淀点 | 单公司估值（第五层） |
| 护城河 | **环节级结构性假设**（高切换成本/赢家通吃倾向） | 公司级护城河深度与可被颠覆性（第三层） |
| 基本面 | 仅用聚合/对比财务指标作结构信号 | 三表勾稽、NRR、40 法则、SBC 稀释、单位经济（第四层） |
| 宏观 | 不分析，仅作输入接入 | 利率/流动性判断（第一层） |
| 负面筛选 | **结构性排除弱势公司**（低优先级，非卖出） | 最终回避/卖出决策 |
| 最终动作 | 产出分层候选名单 | 个股买卖决策 |

**判定规则**：用财务数据时，是在比较"环节之间"（→第二层，保留）还是分析"一家公司内部"（→交出去）。

---

## 4. 产品目标与成功标准

### 4.1 核心目标

1. **价值链可视化**：以图结构展示公司、环节、产品、技术、终端市场及其关系。
2. **利润池定位**：跨环节横向对比，回答"谁赚走了钱"。
3. **瓶颈与弱势识别**：以证据 checklist 标出瓶颈环节与被双向挤压的弱势环节。
4. **技术迁移刻画**：表达"某技术换代把利润从 A 环节搬到 B 环节"，并标注 S 曲线位置。
5. **结构性排除（negative screening）**：识别低毛利、同质化、客户集中、上游强势、下游压价、替代品多的弱势公司，标记为 `watch` 或 `structurally_excluded`。
6. **可投资性收敛**：把价值链节点收敛到美股可投资标的，标注暴露纯度。
7. **证据链管理**：每条关系边绑定来源、原文、时间、置信标签、review 状态。
8. **结构画像输出**：为每家公司生成可移交下一层的结构画像卡。

### 4.2 非目标

不做：自动交易、买卖推荐、短期股价预测、全市场覆盖、公司基本面深挖、估值、复制 Bloomberg/FactSet 数据库。

### 4.3 成功标准（v0.3 改写）

> 看完一条链的地图，使用者能说清：
> 1. 这条链有哪些关键环节；
> 2. 谁供给谁、谁竞争谁、谁替代谁；
> 3. 利润主要沉淀在哪些环节；
> 4. 哪些环节是瓶颈，哪些环节是弱势；
> 5. 技术迁移正在把利润从哪里移到哪里；
> 6. **哪些公司值得进入下一层深挖，哪些应暂缓或结构性排除**；
> 7. 上述每一句话都有可追溯证据。

不以"产生 alpha"为成功标准（那是整条工具矩阵的事）；但**结构性排除是本工具直接、稳定的价值**。

---

## 5. 层间接口契约（核心）

### 5.1 输入接口（其他层 → 本工具）

- **第一层 → 需求潮水状态**：当前 hyperscaler capex 周期处于扩张/收缩、利率环境松紧。MVP 可简化为一个手动设置的全局参数 + 几条 capex 指引证据。决定地图顶端注入的需求强度。

### 5.2 输出接口（本工具 → 三/四/五层）：结构画像卡

结构画像卡是本项目**第一核心交付物**，是工具矩阵的咬合点。

**设计原则：区分"schema 设计完整度"与"MVP 必填要求"**——schema 字段齐全，但 MVP 只强制填写低成本、高确定性的字段，避免卡片退化成一堆 `unknown`。

```yaml
StructuralProfileCard:        # [必填] = MVP 必填；[尽力] = 有则填；[设计] = 进 schema，MVP 可空
  ticker: string              # [必填]
  company_name: string        # [必填]
  chain: string               # [必填] 如 "AI datacenter / HBM-packaging-GPU"
  value_chain_stage: string   # [必填] 所处环节，如 "advanced packaging"

  structural_position: string # [必填] 一句话定性
  profit_pool_tier: high | medium | low | unclear      # [必填] 跨环节相对
  bottleneck_status: bottleneck | potential_bottleneck | not_bottleneck | unclear   # [必填]
  weak_link_status: weak_link | potential_weak_link | not_weak_link | unclear        # [必填]

  key_dependencies:
    upstream: string          # [必填]
    downstream: string        # [必填]

  investability:              # [必填] 二级市场收敛，成本低
    status: direct_us_listed | adr | foreign_listed | private | segment_inside_large_company | no_clean_vehicle
    ticker: string | null
    vehicle_purity: high | medium | low | unclear   # 标的纯度：这只股票是否干净表达该节点

  chain_exposure:             # [尽力] 业务暴露：该链占公司经济多少
    exposure_type: pure_play | meaningful_segment | minor_segment | unclear
    estimated_revenue_exposure: unknown | low | medium | high
    evidence_ids: [string]

  tech_migration_risk:        # [尽力] 无则空
    threat: string
    direction: string         # 利润从哪个环节移向哪个环节
    s_curve_stage: early | ramping | mature | unclear
    layer: fact | estimate | inference | thesis

  structural_thesis: string   # [必填] 纯文本
  open_questions: [string]     # [必填] 交给下一层验证的问题清单

  handoff:                     # [必填] 纯文本
    layer3: string             # 护城河需验证什么
    layer4: string             # 基本面需验证什么
    layer5: string             # 估值需关注什么

  tier: consider | watch | structurally_excluded   # [必填] 唯一裁决字段
  tier_rationale:              # [必填] tier 的结构化背书（不另设并行状态机）
    reasons: [string]          # 如 "低毛利环节"、"客户集中度高"、"上游更强势"
    override_conditions: [string]  # 如 "估值极低"、"技术迁移受益证据出现"、"客户结构改善"

  evidence_ids: [string]      # [必填]
  as_of_date: date            # [必填]
```

**`tier` 语义（重要）**：
- `consider`：结构位置较强，建议进入下一层深挖。
- `watch`：结构中性或有未决问题，待观察。
- `structurally_excluded`：**当前结构位置弱，下一层除非发现强反证（估值极端便宜 / 结构改善 / 技术迁移受益），否则低优先级。不等于卖出，不等于永久拉黑。**

`tier` 是唯一裁决字段；`bottleneck_status` / `weak_link_status` 是支撑它的结构判断，`tier_rationale` 是它的理由背书，三者不重复造状态机。

---

## 6. 科技独有结构性力量（一等公民）

静态供应商网络是 FactSet/Bloomberg 已有的低差异化产物。VCM 的差异化在于建模下列**动态力量**——它们正是利润池会"移动"的原因。

| 力量 | 建模方式 | 服务的判断 |
|---|---|---|
| **技术路线迁移 / S 曲线**（最重要） | `MIGRATES_TO` 边，带 `as_of` 与 S 曲线阶段；如 DDR→HBM、可插拔→CPO、风冷→液冷、铜→光 | 利润在环节间迁移；护城河被新技术绕过 |
| **资本开支周期** | 全局"需求潮水"信号注入链顶；节点标早/晚周期受益 | 需求脉冲沿链传导 |
| **赢家通吃 / 集中度** | 环节/公司标市占率集中度（前三份额 / HHI） | 利润沉淀点、定价权候选 |
| **扩产周期 / 摩尔定律** | 节点属性 `expansion_lead_time`（先进封装/HBM/电力设备约 2–3 年） | 瓶颈核心特征 |

第二层要表达的不是 `NVDA supplies GPU to hyperscalers`，而是：

```
hyperscaler capex 上升 → GPU 需求上升 → HBM 需求上升 → CoWoS 产能紧张
→ advanced packaging 成为瓶颈 → 利润/议价权向特定瓶颈环节扩散
```

---

## 7. 概念模型

### 7.1 节点类型（P0 共 6 类）

| 节点 | P0 | 说明 / 示例 |
|---|---|---|
| Company | ✅ | 上市/非上市公司：NVDA, TSM, MU, COHR, VRT |
| **ValueChainStage** | ✅ | **价值链环节**：HBM、advanced packaging、GPU、AI server、hyperscaler。利润池/瓶颈/弱势均在此粒度判断 |
| Product | ✅ | 产品/组件：H100, HBM3E, CoWoS, 800G module |
| Technology | ✅ | 技术路线：advanced packaging, CPO, liquid cooling |
| EndMarket | ✅ | 终端需求：AI datacenter |
| Document / Evidence | ✅ | 证据来源 |
| Segment / Facility / Commodity / Event / AnalystThesis / Security | 推后 | —— |

> **为什么 P0 必须有 ValueChainStage**：第二层很多判断是"环节到环节"而非"公司到公司"。若没有它，HBM / CoWoS / GPU / 光模块会被迫混成 Product 或 Technology，使利润池横向比较、瓶颈分析、弱势识别都不自然。

### 7.2 边类型（P0 共 6 种）

| 边 | P0 | 方向 | 含义 |
|---|---|---|---|
| SUPPLIES_TO | ✅ | company → company | 供应（单向存储，反向查询生成；**强制带 economic_direction**） |
| BELONGS_TO_STAGE | ✅ | product/company → stage | 归属环节 |
| SERVES_MARKET | ✅ | stage/company/product → market | 终端市场暴露 |
| PRODUCES | ✅ | company → product | 生产 |
| COMPETES_WITH | ✅ | company ↔ company | 竞争 |
| MIGRATES_TO | ✅ | technology/product → technology/product | 技术迁移/替代（带 S 曲线阶段） |
| DEPENDS_ON / USES_TECHNOLOGY / IMPACTS / HAS_THESIS 等 | 推后 | | |

### 7.3 边属性（Edge schema v0.3）

```yaml
Edge:
  edge_id: string
  relationship_type: SUPPLIES_TO | BELONGS_TO_STAGE | SERVES_MARKET | PRODUCES | COMPETES_WITH | MIGRATES_TO
  source_node_id: string
  target_node_id: string

  layer: fact | estimate | inference | thesis
  confidence_label: high | medium | low          # UI 只显示标签
  confidence_reason: string                       # 一句话：为什么是这个标签

  # 内部排序用（不在 UI 显示，严禁合成单一分数，仅作两级独立序数排序键）
  source_rank: int          # SEC_filing=5, deck=4, transcript=4, press=3, news=2, low_quality_web=1
  directness_rank: int      # explicitly_named=5, anonymous_but_quantified=4, strongly_implied=3, weakly_implied=2, speculative=1

  economic_direction:       # SUPPLIES_TO 强制；COMPETES_WITH / MIGRATES_TO 不适用(N/A)
    payer: node_id | null
    receiver: node_id | null
    payment_type: capex | opex | component_cost | service_fee | license_fee | revenue_share | manufacturing_service_fee | unknown

  as_of_date: date          # 证据发布日，强制；用于失效提示
  status: candidate | confirmed | deprecated | rejected
  evidence_ids: [string]
  concentration_pct: string | null   # 如客户占 23%
  created_by: llm_agent | human | import
  notes: string
```

> **排序但不伪精确**：`source_rank` 与 `directness_rank` 仅用于排序/筛选，按字典序（先 source 后 directness）比较，**绝不线性加权合成 0.73 这类分数**。

### 7.4 证据模型（P0 字段）

```yaml
Evidence:
  evidence_id: string
  source_type: SEC_filing | transcript | presentation | press | news
  title: string
  published_at: datetime
  url | accession_number: string | null
  excerpt: string
  excerpt_hash: string
  extraction_method: rule | llm | human
```

### 7.5 图层（继承四层）

```
Layer 0 Identity：company / ticker / CIK / 别名 / 并购史
Layer 1 Fact：有直接 excerpt 支持的关系
Layer 2 Estimate：多源推断的占比/暴露
Layer 3 Inference：传导路径、利润池迁移、技术替代影响
Layer 4 Thesis：人工/agent 的结构性论点
```

UI 必须让 inference/thesis 边**视觉虚化**，与 fact 边明显区分。

---

## 8. 系统架构

```mermaid
flowchart TD
    A[Sources: transcript/deck P0 · 10-K · XBRL] --> B[Parse & Chunk]
    B --> C[LLM 结构化抽取 + 校验]
    C --> D[Entity Resolution]
    D --> E[Evidence Binding]
    E --> F[Staging Graph]
    F --> G[人工 Review]
    G --> H[Production Graph (Postgres + NetworkX)]
    H --> I[结构分析: 利润池/瓶颈/弱势/技术迁移]
    H --> J[结构画像卡生成]
    H --> K[可视化 UI]
    I --> J
```

**模块**：Source Manager / Document Parser / Relation Extractor（含校验）/ Entity Resolver / Evidence Store / Graph Store / Review Console / Structural Analytics / Profile Card Generator / UI。

---

## 9. LLM 使用（去 agent 化）

### 9.1 P0：确定性流水线

```
文档输入 → parse/chunk → LLM 抽取候选边 → LLM 校验候选边是否被原文支持
→ staging graph → 人工 review → production graph
```

P0 只需两个 prompt（抽取 + 校验）+ 人工 review。Planner / Source Discovery / Diff / Report Writer 等多 agent 推后到 P1+。理由：早期最大风险是关系幻觉，不是 agent 能力不足；可控流水线更易 debug、评估、迭代。

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
    "economic_direction": {"payer": "Microsoft", "receiver": "NVIDIA", "payment_type": "component_cost"},
    "as_of_date": "2026-04-25"
  }]
}
```

**禁止**：无 evidence 的 fact 边；把推理写成事实；改写 likely/may/could 为确定关系；自动覆盖人工确认边；丢弃旧版本。

---

## 10. 结构分析能力（只打结构位置分）

只保留三个**纯结构分**，全部为**证据驱动 checklist**，不输出加权小数。

### 10.1 Profit Pool（利润池）
跨同链环节横向排名：毛利率 / 营业利润率 / ROIC + 集中度。输出热力图与排名，**纯比较，不预设买卖**。映射到画像卡 `profit_pool_tier`。

### 10.2 Bottleneck（瓶颈）
checklist（命中几项 + 原文）：供给受限 / 扩产周期长 / 集中度高 / 下游明确提到 supply constraint / 短期无替代 / 客户愿预付或签长协。映射 `bottleneck_status`。

### 10.3 Weak Link（弱势）
checklist：低毛利 / 上下游双向强势 / 产品同质化 / 价格接受者 / 单一大客户或单一产品 / 替代品多。映射 `weak_link_status`，并作为 `tier = structurally_excluded` 的主要依据。

> 展示形式：`Bottleneck 4/6 命中` + 每项对应 excerpt，而非 `0.71`。
> 可比较性来自结构化排序字段（`bottleneck_hits`、`weak_link_hits`、`profit_pool_tier`、`confidence_label`、`source_rank`、`directness_rank`），UI 可排序，底层不假装有精确分数。

### 10.4 路径与传导
```
capex 上修 → AI datacenter buildout → GPU 需求 → HBM 需求 → 先进封装需求 → 电力/散热需求
```
每条路径返回：path nodes/edges、layer、置信标签、证据、暴露的美股公司、可能受益/受损方、技术迁移影响、open questions。

---

## 11. 数据源（优先级倒置）

| 数据源 | 优先级 | 用途 |
|---|---|---|
| Earnings call transcript | **P0（手动导入）** | 瓶颈、定价权、供需、客户评论、capex 指引、技术路线——对结构判断最有用 |
| Investor presentation / deck | **P0（手动导入）** | 产品、客户行业、TAM、产业链图、技术路线 |
| SEC XBRL Company Facts | **P0** | 跨环节横向财务对比（利润池） |
| SEC 10-K / 10-Q | P0（限定用途） | identity 层 + 客户集中度占比（ASC 280）+ 风险因素 |
| Press / News | P1 | 订单、客户切换、供应链事件（需来源质量评分） |
| Wikipedia / Wikidata | P1 | 实体冷启动、别名、并购 |

> **工程约束**：P0 支持**手动上传** transcript / deck / 公开 PDF；定期抓取与增量监控推到 P1。理由：高质量 transcript 可能付费、公开格式不稳定、deck 解析难度高。

### 11.1 匿名大客户解析（一等公民）

ASC 280 常只披露"某客户占 23%"而不披露名字。`某客户占 X%` 是 10-K 最可靠的产业链信号。建模为匿名节点：

```
AnonymousMajorCustomer_<CompanyX>_FY2025  (concentration_pct: 23%)
```

| 情况 | 图层 |
|---|---|
| 公司明确披露客户名 | fact |
| 只披露 "Customer A accounted for X%" | fact（客户匿名） |
| 外部消息推测 Customer A 是某公司 | estimate / inference |
| LLM 猜测 | **不得进入 fact** |

---

## 12. 技术选型（relational-first）

| 层 | 推荐 | 原因 |
|---|---|---|
| 语言 | Python | 生态最佳 |
| 关系/图存储 | **PostgreSQL（边存为表）+ NetworkX（内存图算法）** | MVP 核心是 evidence/review/metadata，属关系型负载；50–500 边规模 NetworkX 足够 |
| 图算法 | NetworkX / igraph | 中心性、路径、集中度 |
| 向量召回（可选） | pgvector | 文档 chunk 检索 |
| 文档解析 | Docling + Unstructured | PDF/HTML/PPT/表格 |
| 抽取 | Pydantic schema + LLM structured output | 强约束、易校验 |
| 前端 | React + Cytoscape.js | 交互式图谱 |
| 部署 | 本地优先 / Docker Compose | 个人版离线可用 |

**阶段性图存储路线**：

| 阶段 | 方案 |
|---|---|
| Phase 0 | SQLite / Postgres + NetworkX |
| Phase 1 | Postgres + NetworkX + Cytoscape.js |
| Phase 2 | Kuzu（嵌入式图查询，按需） |
| 多人协作版 | Neo4j / Memgraph |

> 原则：**先 relational-first，再 graph-enhanced。** Neo4j / 多 agent / Qdrant / Prefect 推迟到协作版。

---

## 13. MVP 设计（收窄到一条子链）

### 13.1 范围
**一条子链打透**：`HBM → 先进封装(CoWoS) → GPU → AI Server → 超大厂`。技术迁移（HBM3E→HBM4、CoWoS 产能、可插拔→CPO）与瓶颈（HBM、先进封装扩产周期）都典型，最能展示动态建模价值。

### 13.2 交付物（按价值排序）
1. **这条链的利润池热力图**（谁赚走钱）——最快出价值。
2. **瓶颈 / 弱势 checklist**（证据驱动）+ **结构性排除名单**。
3. **技术迁移视图**（利润正往哪移）——核心差异化。
4. 可视化图 + 点击边看原文证据。
5. **每家公司结构画像卡**（含 tier 与 handoff）——工具矩阵接口。

### 13.3 P0 功能
- seed list 入库（~30 节点 + 环节）；transcript/deck 手动导入 + 10-K/XBRL 拉取；文档解析；LLM 抽取候选边（两段式 + 校验）；evidence 绑定；Postgres+NetworkX 入库；staging review console；图可视化 + 边证据；利润池横向比；结构性排除标记；结构画像卡生成（含 investability / tier）。

### 13.4 P1 / P2
- P1：每周 filings/news 增量监控、graph diff、失效提示、技术迁移视图自动更新、结构分 checklist 自动化、chain_exposure 估算。
- P2：link prediction、多子链/多行业 schema、事件传播、API export、与三/四/五层工具接口联调、Kuzu 迁移。

---

## 14. 数据质量与评估

### 14.1 抽取质量指标
Faithfulness（原文支持）、Precision、Recall、Entity Resolution Accuracy、Layer Correctness、Temporal Correctness。

### 14.2 黄金集（尽早建）
针对 HBM→封装→GPU 子链，人工标注 **20–30 条黄金关系**；每次改 prompt 跑 precision/recall，判断抽取在变好还是变坏。

### 14.3 置信标签（去公式、可排序）
- UI 显示：离散 `high / medium / low` + `confidence_reason` 一句话。
- 内部：`source_rank`（来源类型）与 `directness_rank`（表述直接性）两个**独立序数**字段，仅用于排序/筛选，**严禁合成单一分数**。

### 14.4 失效管理
每条边带 `as_of_date`；UI 默认提示"该关系最后验证于 N 个月前"，超阈值标灰待复核。

---

## 15. UI 草案

- **多视图**：Company view / Stage chain view / End market view / Bottleneck view / Profit pool view（按毛利/ROIC 着色）/ Tech migration view（利润迁移）/ Weak link view / **Exclusion view（高亮 structurally_excluded）**。
- **边详情面板**：relationship、layer（视觉虚化区分）、confidence label + reason、economic_direction（谁付谁）、as_of 与失效提示、concentration、evidence excerpts、review status。
- **结构画像卡面板**：每家公司一张卡，含 `tier`、`tier_rationale`、`investability`、`open_questions`、`handoff`。

---

## 16. 关键设计决策

1. **定位为第二层地图引擎 + 地形强弱判断**——产出地图与结构分层名单，含结构性排除，但不产出买卖结论。
2. **动态结构力量优先于静态供应商网络**——技术迁移/S曲线/capex周期/集中度是核心差异化。
3. **环节（ValueChainStage）是利润池/瓶颈/弱势判断的天然粒度**——P0 必备。
4. **财务数据只作跨环节横向比**——利润池属第二层；公司内部分析交第四/五层。
5. **打分去公式化**——结构位置分用证据 checklist + 离散标签；可排序但不伪精确（两 rank 独立、不合成）。
6. **economic_direction 显式建模**——表达"谁为谁付钱"，仅 SUPPLIES_TO 强制。
7. **可投资性收敛**——`investability` + `chain_exposure` 把地图收敛到美股可投资且暴露纯的标的。
8. **结构画像卡是工具矩阵的咬合点**——区分 schema 完整度与 MVP 必填，`tier` 为唯一裁决字段。
9. **relational-first**——Postgres + NetworkX 起步，图库推后。
10. **production/staging 分离、四层证据模型、LLM 不直接写主图**——继承 v0.1/v0.2。

---

## 17. 风险与应对

| 风险 | 应对 |
|---|---|
| LLM 幻觉关系 | evidence mandatory + staging + 人工 review |
| 公开数据不完整 | 区分 anonymous/estimated；transcript/deck 为 P0 提升关系密度 |
| 沦为静态供应商图（无差异化） | 技术迁移/集中度/capex 周期建成一等公民 |
| 越界做了第四/五层 | 严守 IN/OUT 边界；财务仅作横向比 |
| 置信度伪精确 | 离散标签 + 理由；两 rank 独立不合成 |
| 画像卡字段膨胀成 unknown 堆 | 区分 schema 完整度与 MVP 必填；`tier` 唯一裁决 |
| 关系失效 | as_of_date + 失效提示 |
| 概念暴露不纯 | chain_exposure + investability.vehicle_purity |
| 把 structurally_excluded 误读为卖出 | 明确语义：低研究优先级，可被反证推翻 |
| transcript 获取成本 | P0 允许手动导入；商业源推后 |
| 工程过重 | relational-first + 确定性流水线 + 单子链 |

---

## 18. 工程路线图

- **Phase 0（1–2 周）技术验证**：拉 5–10 家公司 transcript/10-K/XBRL → 解析 → LLM 抽取 + 校验 → Postgres+NetworkX 入库 → Cytoscape 展示 → 点击边看 evidence。
- **Phase 1（3–6 周）单子链 MVP**：HBM→封装→GPU 子链 ~30 节点 + 环节；利润池热力图；瓶颈/弱势 checklist + 结构性排除；技术迁移视图；结构画像卡（含 investability/tier）；review console；黄金集评估。
- **Phase 2（6–10 周）增量与接口**：每周监控 + diff + 失效提示；与三/四/五层工具的输入/输出接口；chain_exposure 估算；多子链扩展；按需迁 Kuzu。
- **Phase 3（10 周+）多行业**：半导体设备、电力设备、光模块、电池等子链；link prediction；API export；多人协作版迁 Neo4j/Memgraph。

---

## 19. 最终建议

VCM 的目标不是独立做投资决策，而是在五层框架中稳定承担第二层职责：

> **把混沌的科技行业叙事，压缩成一张可追溯、可更新、可交棒的结构地图，并给出 consider / watch / structurally_excluded 的结构分层。**

推进原则：
1. 不从全市场开始，从 HBM→封装→GPU 一条链打透。
2. 不让 LLM 直接写主图，必须 staging + review。
3. 不只画公司关系，要有环节、技术迁移、利润池、瓶颈、弱势。
4. 不追求自动结论，先追求证据化、可视化、可审计、可排除。
5. 不把关系强度伪精确化，必须显示置信标签与来源。
6. 不把商业研报全文作为可分发数据，优先公开源与用户自有许可数据。
7. 第一版目标不是 alpha，而是提高产业链理解速度、定位利润、并稳定排除弱势环节。
