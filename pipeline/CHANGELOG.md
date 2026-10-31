# CHANGELOG — Pipeline 代码版本记录

## v2 (2026-04-14) — 泛化结构质量检查

基于 seed001 QA 分析，将发现的问题模式编码为可泛化的 pipeline 规则。
所有修改适用于任何 story graph，不限于特定故事。

### director_agent.py
- **新增反模式规则**（第 6 条）：
  - 禁止漏斗收束（所有选项收束到同一节点且无后续差异）
  - 禁止伪选择（所有选项指向同一 target_node_id 且 delta≤1）
  - 数值系统必须落地（≥50% 选择点有 value_effects，结局有 ending_condition）
  - 结局多样性（正常结局≥3，由不同数值组合触发）
  - 死结局不能断连
  - 强分支延续效应（收束后需 auto_route 分化）
- **新增门控字段说明**（第 7 条）：
  - `gate_condition`：数值门控，限制选项可用性
  - `gate_branch`：条件分支路由
  - `auto_route`：分支路径自动路由
- **新增质量自检清单**：6 条生成后自检规则
- **结局数要求**从 2-4 → 3-5
- **数值属性**从可选 → 必选

### story_graph_schema.py
- `ChoiceOption` 新增 `gate_condition`, `gate_branch`, `locked_hint` 字段
- `StoryNode` 新增 `auto_route` 字段
- `ValueSystem` 新增 `routing_rules` 字段，`attributes` 改为接受 dict（兼容详细配置）
- `StoryGraph.validate()` 新增 6 条结构性检查：
  - `_check_pseudo_choices`：伪选择检测
  - `_check_funnel_convergence`：漏斗收束检测
  - `_check_value_system_usage`：数值系统引用检测
  - `_check_ending_diversity`：结局多样性检测
  - `_check_dead_end_connectivity`：死结局连通性检测
  - `_check_choice_impact`：选择数值影响检测

### auditor.py
- `RuleAuditor.audit()` 新增 `_check_structural_quality()` 方法
- 包含 5 类自动检测：
  - `pseudo_choice`：伪选择（severity=warning）
  - `funnel_convergence`：漏斗收束（severity=warning）
  - `value_system_unused`：数值属性未引用（severity=warning）
  - `ending_no_condition`：结局无门控条件（severity=warning）
  - `ending_insufficient`：结局数量不足（severity=warning）
  - `low_value_impact`：选择数值影响不足（severity=warning）

### generate_viz.py
- 边标签显示 `value_effects`（绿色）
- 门控条件显示虚线 + 锁图标（黄色）
- 详情面板显示 `gate_condition`、`gate_branch`、`auto_route` 信息
- 新增结局类型标签：`cold_ending`、`bittersweet_ending`
- 图例新增"数值门控"图标

### 验证结果

V1 (seed001 原始) 检测出 5 个问题：
- 1x pseudo_choice（node_04）
- 3x funnel_convergence（node_02, node_08a, node_08b）
- 1x ending_insufficient（仅 2 个结局）

V2 (seed001 修复后) 全部通过：0 个问题。

---

## v1 (2026-04-14) — 初始版本

原始 pipeline 代码，备份为 `*_v1.py`。

已知局限：
- validate() 只检查基础连通性（6 条规则）
- 无结构质量检查
- Director prompt 无反模式约束
- 无 gate_condition / auto_route 支持
