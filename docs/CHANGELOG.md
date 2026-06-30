# Value Chain Map · 设计文档演进 Changelog

记录设计文档从 v0.1 到当前基线的演进。**当前开发基准 = `docs/value_chain_map_design.md`（内容对应 v0.3）。** 历史文档归档在 `history/`，仅供追溯，不再作为开发依据。

| 阶段 | 文档 | 角色 | 日期 |
|---|---|---|---|
| v0.1 | `history/value_chain_research_tool_prd.md` | GPT 基于用户构想生成的初版 PRD | 2026-06-29 |
| 一审 | `history/value_chain_map_revision_notes.md` | Claude 对 v0.1 的修改意见与依据（15 条） | 2026-06-30 |
| v0.2 | `history/value_chain_map_design_v0.2.md` | 按一审重定位后的设计文档 | 2026-06-30 |
| 复审 | `history/value_chain_map_gpt_review_notes.md` | GPT 对 v0.2 的复审 + Claude 二次裁决 | 2026-06-30 |
| v0.3 | `history/value_chain_map_design_v0.3.md` | 合并复审意见后的设计文档 | 2026-06-30 |
| **基线** | **`docs/value_chain_map_design.md`** | **最终版，开发以此为准（= v0.3）** | 2026-06-30 |

---

## v0.3 —— 当前基线（2026-06-30）

合并 GPT 复审意见，并带 Claude 三道裁决护栏。

### 新增 / 恢复
- **恢复 negative screening（结构性排除）为核心价值**：写回成功标准；明确语义"排除 = 下一层低研究优先级，非卖出，可被反证推翻"。
- **新增 `ValueChainStage` 环节节点（P0）** 与 `BELONGS_TO_STAGE` 边：利润池 / 瓶颈 / 弱势改在**环节**粒度判断，避免 HBM/CoWoS/GPU 被混成 Product/Technology。
- **可投资性收敛**：结构画像卡新增 `investability`（标的载体类型 + vehicle_purity）与 `chain_exposure`（业务暴露纯度），把地图收敛到美股可投资标的。
- **画像卡扩字段**：`open_questions`、`handoff`、`tier_rationale`。
- **显式建模 `economic_direction`（谁为谁付钱）**：payer / receiver / payment_type。

### Claude 裁决护栏（对复审意见的收紧）
1. **置信度可排序但不伪精确**：`source_rank` 与 `directness_rank` 保留为**两个独立序数键**，按字典序排序，**严禁加权合成单一分数**。
2. **`economic_direction` 分边强制**：仅 `SUPPLIES_TO` 强制，`COMPETES_WITH` / `MIGRATES_TO` 为 N/A，避免逼出 null。
3. **画像卡防膨胀**：字段标注 `[必填] / [尽力] / [设计]`，区分"schema 完整度"与"MVP 必填"；`tier` 为唯一裁决字段，`bottleneck_status` / `weak_link_status` / `tier_rationale` 仅作支撑与背书，不另造并行状态机。

### 技术选型
- 改为 **relational-first**：Postgres + NetworkX 起步 → Kuzu（Phase 2）→ Neo4j/Memgraph（协作版）。

---

## v0.2 —— 重定位（2026-06-30）

依据 Claude 一审 15 条意见，对 v0.1 做核心重定位。

### 核心变化
- **重定位为五层框架"第二层（行业结构与价值链）地图引擎"**：产出地图与结构名单，不产出买卖结论。
- **新增层间接口契约**：输入 = 第一层需求潮水/利率；输出 = 结构画像卡（StructuralProfileCard）。
- **科技动态结构力量升为一等公民**：技术迁移/S曲线、capex 周期、赢家通吃/集中度、扩产周期。
- **财务数据角色厘清**：只做"跨环节横向比"（利润池），不做公司基本面。
- **打分去公式化**：Bottleneck / Profit Pool / Weak Link 改为证据驱动 checklist + 离散标签。
- **数据源优先级倒置**：transcript / deck 升为 P0，10-K 限定为 identity + 集中度占比。
- **schema 收缩**：P0 收到核心节点/边；BUYS_TO 不双存。
- **去 agent 化**：P0 用确定性流水线 + 2 个 prompt + 人工 review。
- **匿名大客户解析升为一等公民**；**强制 `as_of_date`** 做失效管理。
- **MVP 收窄到一条子链**：HBM → 先进封装 → GPU → 超大厂。
- **技术选型降配**：Kuzu / Postgres+NetworkX 替代 Neo4j。
- 新增**黄金集评估**（20–30 条标注关系跑 precision/recall）。

### 保留 v0.1 的优秀设计
四层 fact/estimate/inference/thesis；production/staging 分离 + LLM 不直接写主图；证据作为独立对象；"证据才是事实来源"原则。

---

## v0.1 —— 初版 PRD（2026-06-29）

GPT 基于用户构想生成的初版产业链研究工具 PRD（VCRG）。

- 提出证据化产业价值链知识图谱、四层证据模型、staging/production 分离、多 agent 架构、商业竞品对标、MVP（AI datacenter）与工程路线图。
- **主要问题（一审指出）**：工程架构过满但投资价值偏虚；边界不清（同时想做地图/瓶颈/利润池/排雷/报告）；数据源优先级误置（10-K 为 P0）；置信度伪精确公式；schema/技术选型对 MVP 过重；多 agent 过早。

---

## 评审脉络一览

```
v0.1 PRD (GPT)
  └─ Claude 一审：重定位为第二层 + 15 条修改
       └─ v0.2 设计
            └─ GPT 复审：恢复排雷 + ValueChainStage + investability 等
                 └─ Claude 二次裁决：接受多数，加 3 道护栏
                      └─ v0.3 = docs/value_chain_map_design.md（开发基线）
```
