互动小说生成系统 — 设计文档

一、系统定位

基于故事种子（seed），自动生成具有分支结构、数值系统、后果回声的互动小说数据。
核心思路：分离「规划」和「写作」。Director 做全局规划输出 Story Graph，Writer 只看局部上下文生成叙事文本。

二、架构演进

2.1 现有系统（旧版 — 即兴制）

三阶段流水线：Seed → SP 生成（3 次 LLM） → Rollout（实时多轮对话） → 评估

核心思路：给叙事者大纲 + pacing 规则，让 narrator LLM 和 user simulator LLM 实时跑多轮对话，故事在对话中实时生成。

已知问题：
- 结局检测 bug：靠关键词匹配，经常检测不到
- 结尾截断：98% 进度强制结束，高潮没落地
- 分支覆盖不足：3 个 decision_point → 4 个结局，不够
- "前面的选项对于大结局没有影响，要不直死要不就是都收束到了最后一个选项"

为什么不能在现有系统上改：
1. 分支爆炸 — 目标 20-30 选择点 + 30 死结局，LLM-as-judge 实时检测无法扩展
2. 控制粒度 — 需要精确到每个节点的文本，不是百分比 pacing
3. Context 爆炸 — 30 死结局 + 20 选择点轻松超 30K tokens

结论：Rollout 层需要完全重写。Seed 层资产可复用。

2.2 新系统（5+1 Agent 剧本制）

核心改变：从「即兴制」到「剧本制」。提前写好完整故事树，rollout 是演出不是创作。

Agent 角色：
1. Director Agent（1个，一次性）
   输入：Seed 数据
   输出：完整 Story Graph（JSON）
   Context：< 10K tokens 输入，5-15K tokens 输出

2. Branch Writer Agent（N个，并行）
   输入：world bible ~2K + Graph 摘要 ~1K + 本分支详情 ~3K + SP Obfuscation
   输出：本分支完整叙事文本
   Context 恒定 ≈ 6-8K tokens

3. Dead End Worker（30个，批量并行）
   输入：场景 ~500 tokens + 角色状态 + 死因标签
   输出：5-10 行死结局文本
   Context < 1K tokens

4. Pearl String Worker（N个，并行）
   输入：原版文本 + 选择差异描述
   输出：变体文本（改写不重写）

5. PostWriteValidator（规则引擎，零 LLM 成本）
   检测 AI 写作特征：段落均匀度、填充词密度、套路化转折、感官堆砌
   检测到 → 标记 → 触发定向改写 → 再检测 → 循环

6. Auditor Agent（1个，后置检查）
   Phase 1 规则检查（零 LLM）：道具追踪、时间线、角色在场、名称一致
   Phase 2 LLM 审计（仅存疑项）：线索连续性、角色状态、信息边界

2.3 本地 Pipeline 实现

代码路径：<PROJECT_ROOT>/pipeline/

文件结构：
  pipeline.py           — 主入口（Seed → Director → Writers → Auditor → Output）
  story_graph_schema.py — Story Graph 数据结构（StoryGraph, Node, Choice, Branch, ValueDimension 等）
  director_agent.py     — Director Agent（seed → story graph）
  writers.py            — BranchWriter / DeadEndWriter / PearlStringWriter / PostWriteValidator
  auditor.py            — RuleAuditor（结构/连续性/角色检查）

运行方式：
  python3 pipeline.py --mode offline  # 手写示例验证流程
  python3 pipeline.py --mode llm --seed-file data/seed.txt --api-base ... --api-key ...

输出：
  story_graph.json   — 结构化故事图
  narratives.json    — 各节点叙事文本
  audit_report.json  — 审计报告
  story_readable.txt — 人类可读故事文本

三、核心机制

3.1 Story Graph Schema

节点类型（NodeType）：narrative / choice / branch_point / dead_end / ending / merge_point
分支类型（BranchType）：strong / pearl_string

关键数据结构：
- Node: node_id, title, act, node_type, scene_description, choices, next_nodes, value_conditions
- Choice: text, target_node_id, is_dead_end, value_changes
- Branch: branch_id, branch_type, source_node_id, node_ids, merge_node_id
- ValueDimension: name, initial, description, range

3.2 累积数值系统

引入隐藏数值维度（2-4个，由故事主题决定），每次选择影响多个维度。
结局由数值组合决定，不是最后一个选择决定。

数值如何影响故事：
- 解锁条件：某些选项只在特定数值范围内出现
- 文本变体：同一节点根据数值显示不同文本
- 结局分流：高勇气+高洞察 → 真相大白结局；高勇气+低洞察 → 英勇牺牲结局

3.3 后果回声系统

在 Story Graph 中标注 echo_points：后续节点显式回调前期选择。

Echo 类型：
- dialogue_echo：NPC 对话中提及
- environment_echo：环境描写中体现
- consequence_echo：直接剧情后果
- mood_echo：氛围/语气变化

每个选择点至少 1 个 echo_point。

3.4 阶梯式结局矩阵

结局不只是"死/活"，而是阶梯式分布：
- true_ending：所有谜题解开
- good_ending：主要矛盾解决，部分悬念保留
- neutral_ending：活着但代价不小
- bad_ending：失去重要的东西
- hidden_ending：满足特殊条件解锁

3.5 信息边界

每个事实绑定 witnesses 列表（知情者），确保角色只在知道某信息的前提下才能引用。
Auditor 检查：角色 X 引用事实 F，但 X 不在 witnesses 列表 → 标记为信息泄露。

四、三种分支类型

1. 珍珠串分支（Pearl String）
   特征：选择不同 → 微叙事差异 → 强制收束回主线
   处理：Branch Writer 写原版 → Pearl String Worker 生成变体
   成本：每点 ≈ 1 次轻量 LLM 调用

2. 强分支（Strong Branch）
   特征：完全不同的世界线，可能永不收束
   处理：Director 规划 → 每条世界线独立 Branch Writer
   控制：2-4 条，避免指数膨胀

3. 数值类分支（Value-based）
   特征：选择影响隐藏数值 → 结局按阈值分流
   处理：Director 定义 value_system → 每个选择点标注数值影响
   成本：极低，主要在 Director 阶段

五、Rollout 平台 分布式实现

5.1 架构：multi_round_agent（User CC + Worker CC）

使用 Rollout 平台 User Simulator 模式（multi_round_agent），双 CC 实例协作：

  User CC（Orchestrator）         Worker CC（Executor）
  ┌──────────────────┐           ┌──────────────────┐
  │ 接收 seed         │           │ 接收 CLAUDE.md    │
  │ 分步推进 pipeline  │──tmux──→ │ 执行 pipeline 步骤 │
  │ 验证每步输出       │←──tmux──│ 生成文件输出       │
  │ 处理错误/重试      │           │ 报告完成/问题      │
  └──────────────────┘           └──────────────────┘

通信机制：
- User CC 通过 tmux-mcp 发送指令给 Worker CC
- Worker CC 在 tmux session 中执行，User CC 通过 capture-pane 读取输出
- 需要 CC 版本 ≥ 2.1.51

工作流：
  Turn 1: User → "开始 Step 1，生成 Story Graph" → Worker 生成 story_graph.json
  Turn 2: User 验证 Graph → "OK，进入 Step 2" → Worker 生成 narratives.json
  Turn 3: User 验证叙事 → "进入 Step 3 审计" → Worker 生成 audit_report.json
  Turn 4: User 检查审计 → 如有 error 要求修复 → Worker 修复 → 最终确认

5.2 数据格式（seeds.jsonl）

每行一个 seed：
  {
    "id": "seed_001",
    "seed_content": "## 故事种子：维多利亚侦探悬疑\n...",
    "config": {
      "max_branches": 3,
      "max_dead_ends": 10,
      "language": "zh",
      "max_rounds": 30,
      "timeout": 7200
    }
  }

seed_content：纯文本，包含故事类型/时代/地点/概要/主角/关键NPC/期望分支。
config：可选，控制生成参数。

5.3 Snippet 实现（novel_snippet.py）

路径：<ROLLOUT_PLATFORM>/novel_snippet.py

核心逻辑：
1. 读取 seed record
2. 写入 seed_content → /tmp/seed.txt
3. 生成 Worker CLAUDE.md → workspace（包含完整 pipeline 指令和 Story Graph schema）
4. 生成 User system prompt → /tmp/user_sp.txt
5. 调用 args.multi_round_agent.run(query, max_rounds, timeout, with_traj, user_kwargs, worker_kwargs)
6. 收集 /tmp/output/ 下的输出文件
7. 返回结果 dict

关键 kwargs：
  user_kwargs = {"extra_args": "--system-prompt-file /tmp/user_sp.txt"}
  worker_kwargs = {"workspace": "/tmp/novel_workspace"}

5.4 提交配置

提交脚本：<ROLLOUT_PLATFORM>/submit_novel.py

agents_config：
  [
    {"name": "user",   "agent_type": "claude-code-tmux", "model_id": MODEL_ID, "version": "2.1.51"},
    {"name": "worker", "agent_type": "claude-code-tmux", "model_id": MODEL_ID, "version": "2.1.51"}
  ]

挂载配置：
  pipeline 代码目录挂载到 /mnt/pipeline（readOnly，供 Worker 参考 schema）

其他参数：
  image: registry.example.com/base/rollout-base:0.0.5
  tool_tool_template: <tool-template>
  is_sync: true（从共享存储同步 seeds.jsonl）
  volume_name: example-volume

5.5 注册流程

1. 将 novel_snippet.py 注册到 Rollout 平台，获取 process_snippet_id
2. 将 snippet_id 填入 submit_novel.py
3. 准备好 seeds.jsonl（放到共享存储）
4. 运行 submit_novel.py 提交任务

5.6 并发与成本估算

每个 seed 需要 1 对 User+Worker CC 实例，执行时间预估 30-60 分钟/seed。

  seeds 数量    并发    总时间（估）
  2（当前）     2       30-60 min
  10           5       60-120 min
  30           10      90-180 min

成本主要来自 CC 的 LLM 调用。每个 seed 预估：
- Director: ~15K tokens（1 次大调用）
- Writers: ~50K tokens（多个分支 × 多个节点）
- Auditor: ~10K tokens
- User orchestration: ~5K tokens
- 总计 ~80K tokens/seed

六、Rubric 体系

6.1 设计阶段（Director/Writer 输出质量把关）

A. 选择点设计质量
  - 选择点密度：每 5-8 叙事节点至少 1 个有意义选择点
  - 选择区分度：每选项导向可感知的不同反馈
  - 选择策略性：不能是明显好坏的二选一，必须是有代价的权衡
  - 选择表达力：选项让玩家感到代表态度/价值观

B. 叙事结构质量
  - 收束自然度：分支汇合不能生硬跳转
  - 累积效应：前期选择应影响后期
  - 死结局因果链：可追溯到具体选择+情境
  - 节奏控制：按阶段合理分配选择点密度

C. 反馈丰富度
  - 分段反馈：数值系统阈值分区有差异化反馈
  - 过程反馈：选择后叙事有对选择的回应
  - 累积反馈：数值在关键节点展示累积效果

6.2 评测阶段（最终产出评分）

单条 Trajectory 新增维度：
  - 选择意义感（高权重）
  - 分支探索欲（中权重）
  - 主题一致性（高权重）
  - 过程丰富度（中权重）
  - 收束满意度（高权重）

七、StoryGraphExecutor（Rollout 框架集成，代码未包含在本仓库）

路径：<ROLLOUT_FRAMEWORK>/scaffolds/impl/rp/story_graph_executor.py

三阶段 Scaffold，运行时追踪 Story Graph 状态：

Phase 1 — TASK_INIT（解析+初始化）
  - 解析 SP 中的 story_graph 字段
  - 初始化 StoryGraphState：当前节点、数值、echo 索引、知识边界
  - 构建叙事上下文并注入 system message

Phase 2 — PRE_LLM（注入叙事上下文）
  - 根据当前节点构建叙事上下文（当前场景、可选选项、数值状态、待触发 echo）
  - 注入为 system message 或 metadata

Phase 3 — TURN_COMPLETE（检测+推进）
  - 从 LLM 输出中检测选择（选项字母匹配 → 关键词重叠 → 超时回退）
  - 推进节点、更新数值、触发 echo
  - 检测结局条件
  - 自动推进（advance_interval 轮无选择时自动前进）

在 rp_rollout_synthesizer.py 中自动接入：SP 有 story_graph 字段时激活。

八、复用矩阵

模块            复用   说明
Seed 数据源      直接   TextAdventure story graph 最适配
SP Obfuscation  直接   20+ 维度注入 Branch Writer
用户行为画像     参考   画像可影响选择偏好
评测框架         适配   prompt 需适配新结构
Bench Seeds     直接   30 seeds 输入 Director
提交框架         部分   Rollout 平台 框架复用，snippet 替换
结局检测         不用   Graph 预定义
Pacing          不用   Director 预定义
LLM-as-judge    不用   不需实时判断

九、待决事项

1. Snippet 注册 — 需要在 Rollout 平台 注册 novel_snippet.py 获取 snippet_id
2. Seed 扩充 — 当前只有 2 个 seed，需要补充到 10-30 个
3. API 模型选择 — User/Worker CC 用什么模型（Opus/Sonnet）
4. 输出后处理 — Rollout 平台 输出如何聚合和评测
5. Pipeline 代码依赖 — Worker CC 是否需要跑 pipeline.py 还是纯 prompt 驱动

---
路径索引：
  Pipeline 代码:  <PROJECT_ROOT>/pipeline/
  Rollout Snippet:  <ROLLOUT_PLATFORM>/novel_snippet.py
  提交脚本:      <ROLLOUT_PLATFORM>/submit_novel.py
  Seed 数据:     <PROJECT_ROOT>/data/seeds.jsonl
  原始设计文档:   <PROJECT_ROOT>/pipeline/pipeline.md

最后更新: 2026-04-14
