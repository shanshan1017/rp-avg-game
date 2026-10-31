一、现状：旧版「即兴制」互动小说系统
1. 架构概览
三阶段流水线：
Seed → SP 生成（3 次 LLM 调用）→ Rollout（实时多轮对话）→ 评估
核心思路：「即兴制」
给 narrator LLM 一个大纲 + pacing 规则，让它和 user simulator LLM 实时跑多轮对话，故事在对话中实时生成。
代码位置：<LEGACY_ROLLOUT_REPO>/interactive_novel
核心文件：snippet_sp_gen.py / snippet_novel.py / submit_novel_pipeline.py
2. 数据流详细
【Stage 1: SP 生成】
- Call 1 — 从 seed 生成 narrative_outline（大纲）
- Call 2 — 从 outline 生成 system_prompt + opening_message
- Call 3 — 生成 user_prompt_template（用户行为指令）
- 输出字段：system_prompt, opening_message, user_prompt_template, narrative_outline, sp_obfuscation, user_character
【Stage 2: Rollout】
- narrator LLM + user simulator LLM 多轮对话（默认 max 50 轮）
- 每轮：build_pacing_guidance() 按进度百分比动态注入叙事节奏
  - 前40%: 铺垫
  - 40-70%: 冲突
  - 70-90%: 高潮
  - 90%+: 收束
- 结局检测：关键词匹配（"故事结束" "THE END" "全剧终"等）
- 分支检测：LLM-as-judge 实时判断用户在 decision_point 的选择
【Stage 3: 评估】
5 个维度：上下文一致性 / Pacing 遵循度 / 用户画像一致性 / NPC 承接与钩子 / 结局质量
3. 叙事结构类型
类型
展开方式
说明
linear（线性）
1 seed → 1 rollout
标准四幕结构
branching（分支）
1 seed → 4 rollouts
3 个 decision_point + 4 个 ending
multi_pov（多视角）
1 seed → 3 rollouts
3 个 pov_character 各一条
4. 可复用资产
(a) Seed 数据源（直接复用）
- TextAdventure ⭐️ — 天然具有完整 story graph，最适配分支叙事
- AI Dungeon — SP 丰富，带大世界观
- 完整小说（番茄/Wattpad）— 完整剧情，适合扩展
(b) SP Obfuscation 维度（直接复用，20+ 维度）
维度
可选值
writing_style
chat / light_rp / standard_rp / novel / literary
response_length
medium / long / very_long
action_depth
none / minimal / normal / rich / literary
thought_depth
none / subtle / moderate / deep
environment_depth
none / brief / moderate / immersive
sensory_depth
none / occasional / rich
paragraph_count
single / few / several
action_marker
asterisk / parenthesis / bracket / angle / none
dialogue_marker
quotes / guillemet / chinese_quotes / none
register
formal / neutral / colloquial / literary
(c) 用户行为画像（参考复用）
ultra_casual（2-8字）/ casual（8-25字）/ moderate（25-40字）/ engaged（40-80字）
(d) 评测框架（参考复用）
5 个评估维度的 prompt 设计和流程可参考，但需要适配新的分支结构。
(e) Bench 数据（参考复用）
中文 15 seeds（v2） + 英文 15 seeds，覆盖 linear / branching / multi_pov
5. 已知问题
(a) 结局检测 bug：branching 模式下靠关键词匹配结局，经常检测不到，导致故事无法正常结束。文档原话：「亟待解决，应该调用 LLM，不然结束不了」。
(b) 结尾截断：98% 进度时强制结束，高潮没落地（case: Head of State rollout）。
(c) 分支覆盖不足：branching 只有 3 个 decision_point → 4 个结局，远不能满足复杂分支叙事需求。
(d) multi_pov 角色选择 bug：角色选择没有 follow 用户模拟器的性格；最初的 SP 没有 follow 用户选择。
二、问题 / 瓶颈 — 为什么不能在现有系统上改
核心矛盾：架构假设不同。
- 现有系统 = 即兴制（improvisation）：给叙事者大纲，让它实时发挥
- 目标系统 = 剧本制（scripted）：提前写好完整故事树，rollout 是演出不是创作
三个具体矛盾
1. 分支爆炸
- 现有：3 个决策点 → 4 个结局
- 目标：20-30 个选择点 → 30 个死结局 + 多个正常结局
- LLM-as-judge 实时检测无法扩展到 30 个决策点。
2. 控制粒度不匹配
- 现有：pacing 百分比引导
- 目标：精确到每个节点的文本，每个选项的措辞
3. Context 爆炸
30 个死结局 + 20 个选择点 + 强分支世界线 → 轻松超过 30K tokens
结论：Rollout 层需要完全重写。Seed 层和 SP 生成层的资产可以复用。
三、目标架构：5+1 Agent 剧本制系统
核心思路：分离「规划」和「写作」。
Director 做一次性全局规划，输出 Story Graph。
每个 Writer 只看自己负责的局部 + 全局 Graph 摘要，context 恒定大小。
1. Director Agent（1 个，一次性调用）
输入： Seed 数据（story graph / 小说摘要 / 世界观）
输出： 完整 Story Graph（JSON 结构）
Story Graph 包含：主线骨架、强分支弧线、选择点定义、死结局触发条件、数值系统、收束规则、角色列表 + 道具 + 伏笔
关键设计：输出是结构化数据（JSON/YAML），不是叙事文本。Context 估算：输入 < 10K tokens，输出 5-15K tokens。
2. Branch Writer Agent（N 个，并行）
每个强分支分配一个独立 Writer。
输入（恒定大小）：world bible ~2K + Graph 摘要 ~1K + 本分支详情 ~3K + SP Obfuscation
输出：本分支完整叙事文本
关键设计：每个 Writer context ≈ 6-8K tokens，不随分支数量增长。
3. Dead End Worker（30 个，批量并行）
输入：场景 ~500 tokens + 角色状态 + 死因标签
输出：5-10 行死结局文本
关键设计：30 个完全并行，单个 context < 1K tokens。
4. Pearl String Worker（N 个，并行）
处理珍珠串分支：选择不同但最终收束回同一节点。
输入：原版文本 + 选择差异描述
输出：变体文本（保剧情不变，改措辞/氛围）
关键设计：基于原版改写，不是重写。速度快、成本低。
5. PostWriteValidator（规则引擎，零 LLM 成本） 🆕
参考 TheDream 的 PostWriteValidator 和 avoid-ai-writing 规则库设计。
在所有 Writer 输出后、Auditor 前置的纯规则质量门。
检测维度：
- 段落长度均匀度：AI 生成的段落长度偏均匀，真实写作差异更大
- 填充词密度：检测 AI 高频填充词（"然而"、"不禁"、"缓缓"、"目光中闪过"等）
- 套路化转折：开头总结 + 转折词 + 新信息的固定模式
- 感官描写堆砌：连续使用三种以上感官描写
- 情绪词过载：同一段落 3+ 个情绪形容词
工作流程：
检测到 AI 特征 → 标记问题段落 → 自动触发定向改写 → 再检测 → 循环直到通过
关键设计：检测阶段完全不调用 LLM，只在需要改写时才触发 LLM 调用。
6. Auditor Agent（1 个，后置检查） 🔄升级
输入： 所有 Writer 的输出 + Story Graph
检查策略：分层审计（规则先行 + LLM 兜底）
参考 TheDream 的 33 维度审计 pipeline。用规则层过滤 60-70% 的明确通过/不通过项，只让模糊案例进入 LLM 审计。
Phase 1 — 规则检查（零 LLM 成本）：
- 道具追踪：钥匙在哪拿的、在哪用的、每条路线道具链是否完整
- 时间线顺序：事件发生顺序是否自洽（不能先用再拿）
- 角色在场检查：对话参与者是否在当前场景中
- 名称一致性：角色/地点名在各分支中是否统一（正则匹配）
- 死结局因果检查：死因标签与选择点选项是否对应
Phase 2 — LLM 审计（仅对 Phase 1 存疑项）：
- 线索连续性：A 分支提到的道具在 B 分支是否矛盾？
- 角色状态一致：角色在不同分支的知识/状态是否冲突？
- 死结局合理性：死因与选择的因果关系是否成立？
- 信息边界隔离：角色是否泄露了不该知道的信息？
信息边界隔离详设计： 🆕
参考 TheDream Observer 的 witnesses 列表机制。
每个事实绑定 witnesses 列表（知情者），确保角色只在知道某信息的前提下才能引用。
实现方式：从 Story Graph + Writer 输出中提取结构化事实表：
事实
首次出现节点
witnesses（知情者）
密室有暗门
node_7（书房搜索）
主角, 管家
凶手是园丁
node_15（花园线索）
主角（仅走该分支时）
Auditor 逐分支扫描：如果角色 X 引用了事实 F，但 X 不在 F 的 witnesses 列表中 → 标记为信息泄露违规。
输出： 问题列表 + 修改建议
四、三种分支类型的处理方式
1. 珍珠串分支（Pearl String）
- 特征：选择不同 → 微叙事差异 → 强制收束回主线
- 处理：Branch Writer 写原版 → Pearl String Worker 生成变体
- 成本：每点 ≈ 1 次轻量 LLM 调用
2. 强分支（Strong Branch）
- 特征：完全不同的世界线，可能永不收束
- 处理：Director 规划 → 每条世界线独立 Branch Writer
- 风险控制：建议 2-4 条，避免指数膨胀
3. 数值类分支（Value-based）
- 特征：选择影响隐藏数值 → 结局按阈值分流
- 处理：Director 定义 value_system → 每个选择点标注数值影响
- 成本：极低，主要在 Director 阶段
五、与现有系统的复用矩阵
模块
复用
说明
Seed 数据源
✅ 直接
TextAdventure story graph 最适配
SP Obfuscation
✅ 直接
20+ 维度注入 Branch Writer
用户行为画像
🔶 参考
画像可影响选择偏好
评测框架
🔶 适配
prompt 需适配新结构
Bench Seeds
✅ 直接
30 seeds 输入 Director
提交框架
🔶 部分
Rollout 平台 框架复用，snippet 替换
结局检测
❌
Graph 预定义
Pacing
❌
Director 预定义
LLM-as-judge
❌
不需实时判断
六、实施计划
Phase 0: Story Graph Schema 设计（1-2 天）
定义 JSON Schema + 手写 example graph 验证
Phase 1: Director Agent（2-3 天）
system prompt + seed→graph 转化 + 3-5 seed 测试
Phase 2: Branch Writer + Dead End Worker（3-4 天）
graph→writer context 切分 + 并行写作 + 端到端测试
Phase 2.5: PostWriteValidator（1 天） 🆕
AI 写作特征规则库 + 检测→改写循环 + 通过阈值
Phase 3: Auditor + 集成（2-3 天） 🔄升级
规则层检查 + 信息边界隔离 + LLM 审计层 + 6 agent 串联 + Rollout 平台 接入
Phase 4: 评测适配（1-2 天）
评测 prompt 适配 + 分支覆盖率指标
总估时：10-16 天（不含调优和迭代）
七、开放问题
1. 用户交互形式 — 是否支持选项外自由输入？
2. 强分支数量上限 — 建议 2-4 条
3. 数值系统复杂度 — 可视化 vs 纯隐藏？
4. Seed 适配 — 小说类 seed 无现成 graph，需转化层
5. 多语言 — Director graph 语言无关，Writer 按语言切分
八、参考项目与工具 🆕
以下开源项目在架构设计中提供了关键参考：
TheDream
GitHub: https://github.com/Narcooo/thedream
AI 互动叙事 + 长篇小说写作平台，10 Agent pipeline。
借鉴点：
- 6 阶段 pipeline（Writer → Observer → Auditor → Normalizer）
- 33 维度连续性审计 → 本方案 Auditor 分层审计
- PostWriteValidator AI 痕迹检测 → 本方案 PostWriteValidator
- Observer 事实提取 + witnesses 信息边界 → 本方案 Auditor 信息边界隔离
- Fate 系统、PList 角色压缩、场景模板零成本分类
AI-Novel-Writing-Assistant
GitHub: https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant
AI 辅助小说写作工具，Web UI。
借鉴点：多模型切换、章节管理、风格控制 UI/UX
Dramamancer
论文：arxiv 2601.18785
Storylets + LLM 组合叙事框架。
借鉴点：语义条件替代硬编码分支，场景+事件+条件 schema 可参考 Story Graph schema
lifesim
GitHub: https://github.com/dfy37/lifesim
AI 人生模拟游戏。
借鉴点：数值系统驱动叙事分支的实现方式
avoid-ai-writing
GitHub: https://github.com/conorbronsdon/avoid-ai-writing
481 行 AI 写作特征检测指南。
借鉴点：词汇/句式/结构层面 AI 特征识别规则，直接用于 PostWriteValidator 规则库
九、故事线质量 Rubric 体系
基于「个性化选项玩法」设计理论（参考：《纸面推演：个性化选项玩法》），提出以下 Rubric 体系，分为设计阶段（Director/Writer 输出质量把关）和评测阶段（最终产出评分）两层。
9.1 核心概念框架
两种选项范式
范式
定义
反馈时机
个性化程度
制作成本
分支选项
每次选择直接决定走向
即时
低
线性增长
组合选项
多次选择累积形成组合，大后期见分晓
延迟
高
指数增长（需分类控制）
当前系统的三种分支类型映射：
- 珍珠串分支 → 典型的分支选项（即时微差异 → 收束）
- 强分支 → 分支选项的极端形态（完全不同世界线）
- 数值类分支 → 组合选项（选择影响隐藏数值 → 阈值分流）
设计指导：纯分支选项的个性化天花板低，建议在数值类分支中引入组合选项逻辑，让多次小选择的累积效应驱动结局差异。
两种个性化方向
方向
定义
资源投入重心
适用分支类型
过程个性化
不同路径 → 相同（或相似）结局，体验差异在旅途中
中段节点文本
珍珠串分支
结果个性化
相似路径 → 不同结局
结局文本 + 数值系统
数值类分支、强分支
大多数系统在两者之间取平衡，很少能同时最大化。本系统的架构天然适合「过程个性化为主 + 结果个性化兜底」：
- 珍珠串分支 + Branch Writer 提供丰富的过程变体（低成本）
- 数值系统 + 强分支提供有限但有意义的结局差异（高成本，控制在 2-4 条）
9.2 设计阶段 Rubric（Director/Writer 输出质量把关）
以下维度在 Auditor Agent 中作为检查项使用，Phase 1 规则检查 + Phase 2 LLM 审计。
A. 选择点设计质量
维度
评判标准
检查方式
选择点密度
每 5-8 个叙事节点至少出现 1 个有意义的选择点；选择点之间有足够的叙事铺垫
规则：统计 Graph 中选择节点间距
选择区分度
每个选择点的选项必须导向可感知的不同反馈（不能只是换个措辞说同一件事）
LLM：对比同一选择点的不同选项输出，相似度 > 阈值则不通过
选择策略性
选项不能是「明显好坏」的二选一，必须是有代价的权衡
LLM：评估选项是否存在明显优劣
选择表达力
选项措辞是否让玩家感到「这代表了我的态度/价值观」，而非「选 A 看剧情 1 选 B 看剧情 2」
LLM：评估选项文本的角色代入感
B. 叙事结构质量
维度
评判标准
检查方式
收束自然度
分支汇合时不能生硬跳转（"无论如何你回到了主线"），需要有逻辑桥接
LLM：检查收束节点前后文本的因果连贯性
累积效应
前期选择应影响后期选项/文本/角色关系，不能完全无关
规则：检查 Graph 中是否有 value_system 跨节点引用
死结局因果链
死结局的触发必须可追溯到具体选择 + 情境，不能是随机惩罚
规则+LLM：已在 Auditor Phase 1 中
节奏控制
按叙事阶段（铺垫→冲突→高潮→收束）合理分配选择点密度和情感强度
规则：统计各阶段选择点分布
C. 反馈丰富度
维度
评判标准
检查方式
分段反馈
组合选项不需要每种组合都写独立内容，但需要按分类给出差异化反馈
规则：检查数值系统的阈值分区是否覆盖有意义的差异
过程反馈
每次选择后，叙事文本中应有对该选择的直接或间接回应（角色反应、环境变化、氛围转换）
LLM：检查选择后续文本是否 acknowledge 了选择内容
累积反馈
数值类分支在关键节点应展示累积效果（角色态度变化、可用选项变化）
规则：检查 value_system 触发点是否有对应文本变化
9.3 评测阶段 Rubric（最终产出评分）
适用于单条 trajectory 评估（SP_Rubric 框架）和 trajectory 对比评估（domain_rubric pairwise）。
单条 Trajectory 评估维度
在现有 5 维度（上下文一致性 / Pacing 遵循度 / 用户画像一致性 / NPC 承接与钩子 / 结局质量）基础上，新增以下维度：
维度
评分标准
权重建议
选择意义感
回看整条路径，玩家的选择是否实质性地塑造了经历？还是走了一条「无论怎么选都差不多」的路？
高
分支探索欲
读完这条路径后，是否想知道「如果当时选了另一个会怎样」？（反映选择点设计的吸引力）
中
主题一致性
选择内容、叙事走向、结局是否都服务于核心主题？还是选择与故事主线割裂？
高
过程丰富度
即使目标结局相同，这条路径的体验是否因选择不同而有独特记忆点？
中
收束满意度
分支汇合或结局到来时，是否有「因果回收」的满足感？还是感觉被强行推向了预设终点？
高
Pairwise 对比评估引导维度
用于 domain_rubric 的 critic 提取原则引导方向：
当两条 trajectory 基于同一 Story Graph 但走不同路径时，评估重点：
1. 哪条路径的选择点更让人感到「这个选择有意义」？
2. 哪条路径更好地展示了「不同选择带来不同体验」？
3. 哪条路径的收束（汇合/结局）更自然、更有因果回收感？
4. 哪条路径更好地维持了主题一致性？
5. 哪条路径让人更想探索另一种可能性？
9.4 与 Pipeline 的集成点
Rubric 维度
检查时机
负责 Agent
选择点密度/分布
Director 输出 Story Graph 后
Auditor Phase 1（规则）
选择区分度/策略性/表达力
Branch Writer 输出文本后
Auditor Phase 2（LLM）
收束自然度
Pearl String Worker 输出后
Auditor Phase 2（LLM）
累积效应
Director 输出后 + Writer 输出后
Auditor Phase 1（value_system 引用检查）
反馈丰富度
Writer 输出后
Auditor Phase 2（LLM）
主题一致性
全链路
Auditor Phase 2（LLM）
AI 写作痕迹
Writer 输出后
PostWriteValidator（规则）
9.5 主题共鸣兜底机制
研究表明：即使玩法机制不完善，玩家因认同主题而接受不完整的体验。主题是选项系统的「安全网」。
设计建议：
- Director 在 Story Graph 中显式声明 theme_statement（核心主题陈述）
- 每个选择点的选项设计应服务于主题探索（不同选项代表对主题的不同态度）
- Auditor 检查：所有分支路径是否都在探索同一主题的不同面向？偏离主题的分支需要标记
- 适合「个性化选项」形式的高潜力题材：心理悬疑（模拟思维过程）、法庭论辩（言语交锋）、侦察审讯（信息博弈）、情感沟通（表达方式探索）
9.6 参考来源
- 《纸面推演：个性化选项玩法》 https://news.qq.com/rain/a/20250110A01MZB00
- 《Standard Patterns in Choice-Based Games》（分支收束式 + 任务式结构模型）
- 《WST》（We Should Talk）个性化组合选项实践案例
十、核心机制增强方案
基于现有架构分析和问题诊断（"前面的选项对于大结局没有影响，要不直死要不就是都收束到了最后一个选项"），提出以下增强机制。

---
10.1 累积数值系统（Cumulative Value System）
问题
当前选择是"一次性"的：选 A 走分支 A，选 B 走分支 B，选择之间没有累积效应。导致每个选择要么直接导致死结局，要么对最终结局无影响。
方案
引入隐藏数值维度，每次选择影响多个维度的数值。结局由数值组合决定，而非单次选择。
数值维度示例：
维度
说明
取值范围
courage
勇气/冒险倾向
0-100
trust
信任/合作倾向
0-100
morality
道德/正义感
0-100
insight
洞察/细心程度
0-100
数值如何影响故事：
1. 解锁条件：某些选项只在特定数值范围内出现
  - 例：courage >= 70 时出现"独自闯入废弃工厂"选项
2. 文本变体：同一节点根据数值显示不同文本
  - 例：trust >= 60 → NPC 主动分享线索；trust < 40 → NPC 隐瞒关键信息
3. 结局分流：结局由数值组合决定，不是最后一个选择决定
  - 例：高勇气+高洞察 → 真相大白结局；高勇气+低洞察 → 英勇牺牲结局
在 Story Graph 中的表示：
{
  "value_system": {
    "dimensions": [
      {"name": "courage", "initial": 50, "description": "面对危险时的态度"},
      {"name": "trust", "initial": 50, "description": "对他人的信任程度"},
      {"name": "morality", "initial": 50, "description": "道德选择的倾向"}
    ],
    "thresholds": [
      {"condition": "courage >= 70 AND trust >= 60", "unlock": "redemption_arc"},
      {"condition": "morality < 30", "unlock": "dark_ending"}
    ]
  }
}
关键设计： 数值维度由 Director Agent 根据故事主题自动生成（不是固定的 courage/trust/morality），确保维度与故事内容紧密相关。

---
10.2 后果回声系统（Consequence Echo System）
问题
即使有分支，玩家也感觉"选什么都一样"——因为之前的选择从未在后续叙事中被提及。
方案
在 Story Graph 中标注 echo_points：后续节点中显式回调前期选择的位置。
Echo 类型：
类型
说明
示例
dialogue_echo
NPC 对话中提及
"还记得你在森林里放走的那个人吗？他现在是..."
environment_echo
环境描写中体现
之前选择烧毁桥梁 → 后面需要过河时桥已不存在
consequence_echo
直接剧情后果
之前救了某 NPC → 该 NPC 在关键时刻出现帮忙
mood_echo
氛围/语气变化
之前选择了残忍选项 → 后续 NPC 对你态度冷淡
在 Story Graph 中的表示：
{
  "echo_points": [
    {
      "source_node": "chapter_1_choice_2",
      "source_option": "A",
      "target_node": "chapter_3_scene_5",
      "echo_type": "dialogue_echo",
      "echo_instruction": "NPC 小雪提到玩家之前在森林中的选择，语气中带有感激"
    },
    {
      "source_node": "chapter_2_choice_1",
      "source_option": "B",
      "target_node": "chapter_4_climax",
      "echo_type": "consequence_echo",
      "echo_instruction": "之前被放走的嫌疑人成为关键证人"
    }
  ]
}
实现要点：
- Director 在生成 Story Graph 时，必须为每个选择点指定至少 1 个 echo_point
- Branch Writer 收到 echo_instruction 后，将其自然融入叙事文本
- Auditor 检查：每个选择点是否都有至少一个后续 echo？echo 内容是否与选择内容逻辑一致？

---
10.3 阶梯式结局矩阵（Graduated Ending Matrix）
问题
当前结局只有"死"和"活"两种。活着的路线全部收束到同一个结局，玩家感觉选择无意义。
方案
用 结局类型 x 变体 矩阵替代二元结局。
结局类型矩阵：
类型
变体
触发条件示例
完美结局
真相大白 / 全员存活 / 隐藏彩蛋
高洞察+高信任+关键线索全收集
正常结局
胜利但有代价 / 和解但留遗憾
中等数值组合
苦涩结局
牺牲换胜利 / 真相但失去挚友
高勇气+低信任 或 高道德+低洞察
开放结局
未解之谜 / 新的开始
特定数值区间
死结局
30 种不同死法（保留现有）
特定选择触发
在 Story Graph 中的表示：
{
  "ending_matrix": {
    "types": [
      {
        "type": "perfect",
        "variants": [
          {"name": "truth_revealed", "condition": "insight >= 80 AND trust >= 70"},
          {"name": "everyone_lives", "condition": "morality >= 80 AND courage >= 60"}
        ]
      },
      {
        "type": "bittersweet",
        "variants": [
          {"name": "sacrifice", "condition": "courage >= 90 AND trust < 50"},
          {"name": "truth_but_loss", "condition": "insight >= 70 AND morality < 40"}
        ]
      },
      {
        "type": "dead_end",
        "variants": [
          {"name": "betrayal_death", "trigger": "chapter_2_choice_3_option_C"},
          {"name": "trap_death", "trigger": "chapter_3_choice_1_option_A AND insight < 30"}
        ]
      }
    ]
  }
}
关键设计： 死结局保留"单选触发"机制（即时反馈），非死结局由累积数值决定（延迟反馈）。两者结合实现"短期选择有风险，长期选择有意义"。

---
10.4 语义条件系统（Semantic Conditions）
问题
硬编码分支（if choice==A → node_5）不灵活，且无法处理组合效应。
方案
参考 Dramamancer 框架，用语义条件替代硬编码。
从硬编码到语义：
硬编码方式：
{"choice": "A", "next_node": "node_5"}
{"choice": "B", "next_node": "node_6"}
语义方式：
{
  "conditions": [
    {"if": "player.demonstrated(compassion) >= 0.7", "unlock": "redemption_arc"},
    {"if": "player.has_item(ancient_key) AND insight >= 60", "unlock": "secret_chamber"},
    {"if": "npc.trust(protagonist) >= 0.8", "unlock": "confession_scene"}
  ]
}
实现层次：
Phase 1（当前可做）：用数值阈值条件（courage >= 70）模拟语义条件，在 Rollout 中用规则引擎判断。
Phase 2（中期）：引入 LLM 语义评估，对玩家行为做向量化编码，用余弦相似度判断条件是否满足。

---
10.5 Auditor 修复闭环（Fix Loop）
问题
当前 Auditor 只做检查不做修复。发现问题后需要人工介入。
方案
Writer → Auditor 检查 → 发现问题 → 生成定向改写指令 → Writer 重写问题段落 → Auditor 再检 → 通过/放弃
流程：
1. Writer 输出文本
2. Auditor 检查（规则 + LLM）
3. 如有问题，生成具体改写指令：
  - "chapter_2_scene_3 中角色 A 引用了 chapter_3 才揭露的信息，请移除该引用"
  - "death_end_7 的死因与选择无因果关系，请添加因果链"
4. Writer 收到指令，只改写问题段落（不重写全文）
5. Auditor 再检改写部分
6. 最多循环 2 次，仍不通过则标记 human review
成本控制：
- 第一轮 Auditor：全量检查
- 修复轮 Auditor：只检查改写部分 + 改写部分与上下文的衔接
- 每轮改写只传问题段落 + 上下文窗口（约 2K tokens），不传全文

---
10.6 混合区域模式（Hybrid Scripted + Improvised）
问题
纯剧本制控制力强但灵活性差，纯即兴制灵活但不可控。
方案
在 Story Graph 中标注每个区域的类型：
类型
说明
适用场景
scripted
完全预写，rollout 按剧本演
关键剧情节点、结局、重要转折
guided
给 LLM 大纲 + 约束，即兴发挥
日常探索、支线任务、闲聊
free
纯即兴，只给世界观约束
开放探索区域
在 Story Graph 中的表示：
{
  "nodes": [
    {"id": "ch1_opening", "type": "scripted", "text": "..."},
    {"id": "ch1_explore", "type": "guided", "outline": "玩家探索小镇，可能遇到 3 个 NPC", "constraints": ["不能提前揭露凶手"]},
    {"id": "ch2_climax", "type": "scripted", "text": "..."},
    {"id": "ch2_aftermath", "type": "free", "world_rules": ["小镇已封锁", "警察在巡逻"]}
  ]
}

---
10.7 信息不对称建模（Information Asymmetry）
问题
角色经常"无意识"地引用了他们不该知道的信息（信息泄露），破坏悬疑感。
方案
在 Story Graph 中显式追踪每个实体的 knowledge_state：
{
  "knowledge_tracking": {
    "facts": [
      {
        "fact_id": "secret_passage",
        "description": "密室后面有暗门",
        "first_revealed": "chapter_2_search_scene",
        "witnesses": ["protagonist", "butler"]
      },
      {
        "fact_id": "real_killer",
        "description": "真正的凶手是园丁",
        "first_revealed": "chapter_4_revelation",
        "witnesses": ["protagonist"]
      }
    ]
  }
}
Auditor 检查规则： 如果某角色在对话中提到某 fact，检查该角色是否在 witnesses 列表中。不在则标记为信息泄露错误。

---
10.8 完整 Story Graph Schema
以下是整合所有增强机制后的 Story Graph 完整结构：
{
  "story_graph": {
    "metadata": {
      "title": "午夜庄园",
      "theme_statement": "信任的代价：你愿意为真相付出什么？",
      "genre": "mystery",
      "estimated_playtime": "30-45 min",
      "total_endings": 8
    },
    "value_system": {
      "dimensions": [
        {"name": "trust", "initial": 50, "description": "对庄园中其他人的信任"},
        {"name": "insight", "initial": 50, "description": "对案件真相的洞察力"},
        {"name": "courage", "initial": 50, "description": "面对危险时的勇气"}
      ]
    },
    "characters": [
      {
        "id": "butler",
        "name": "管家老陈",
        "initial_knowledge": ["secret_passage", "master_schedule"],
        "trust_threshold": {"share_clue": 60, "betray": 20}
      }
    ],
    "nodes": [
      {
        "id": "ch1_arrival",
        "type": "scripted",
        "chapter": 1,
        "text_brief": "玩家到达庄园，被告知不能离开",
        "next": ["ch1_explore"]
      },
      {
        "id": "ch1_explore",
        "type": "guided",
        "chapter": 1,
        "outline": "玩家自由探索庄园一楼",
        "constraints": ["不能进入二楼", "管家会跟随"],
        "next": ["ch1_choice_1"]
      },
      {
        "id": "ch1_choice_1",
        "type": "choice_point",
        "chapter": 1,
        "prompt": "你听到二楼传来异响",
        "options": [
          {
            "label": "A) 不顾管家阻止，冲上二楼",
            "value_changes": {"courage": 15, "trust": -10},
            "next": "ch1_upstairs_discovery"
          },
          {
            "label": "B) 假装没听到，暗中观察管家反应",
            "value_changes": {"insight": 15, "trust": 5},
            "next": "ch1_observe_butler"
          },
          {
            "label": "C) 直接问管家二楼有什么",
            "value_changes": {"trust": 10, "courage": -5},
            "next": "ch1_ask_butler"
          }
        ],
        "echo_points": [
          {
            "target_node": "ch3_confrontation",
            "echo_type": "dialogue_echo",
            "instruction": "管家提到玩家在第一晚的行为，态度取决于 trust 值"
          }
        ]
      }
    ],
    "ending_matrix": {
      "types": [
        {
          "type": "perfect",
          "name": "真相大白",
          "condition": "insight >= 80 AND trust >= 60",
          "brief": "你找到所有线索，揭露真凶，所有人安全"
        },
        {
          "type": "bittersweet",
          "name": "代价之胜",
          "condition": "courage >= 80 AND insight >= 50 AND trust < 40",
          "brief": "你揭露了真相，但因不信任所有人而孤身犯险，管家为你挡刀"
        },
        {
          "type": "normal",
          "name": "勉强脱身",
          "condition": "courage >= 50 AND insight >= 40",
          "brief": "你活着离开了庄园，但部分真相仍是谜"
        },
        {
          "type": "open",
          "name": "未解之谜",
          "condition": "insight < 40 AND courage >= 60",
          "brief": "你逃出庄园，但什么都没搞清楚"
        }
      ]
    },
    "knowledge_tracking": {
      "facts": [
        {"fact_id": "secret_passage", "description": "二楼有暗门通往地下室", "first_revealed": "ch1_upstairs_discovery", "witnesses": ["protagonist"]},
        {"fact_id": "master_will", "description": "庄园主人修改过遗嘱", "first_revealed": "ch2_study_search", "witnesses": ["protagonist", "butler"]}
      ]
    }
  }
}

---
10.9 实施优先级
优先级
机制
影响
复杂度
建议 Phase
P0
累积数值系统
直接解决"选择无影响"问题
中
Phase 0
P0
阶梯式结局矩阵
直接解决"结局收束"问题
中
Phase 0
P0
后果回声系统
增强选择反馈感
低
Phase 0
P1
语义条件
增强灵活性
高
Phase 1
P1
Auditor 修复闭环
提升质量
中
Phase 1
P2
混合区域模式
增强多样性
中
Phase 2
P2
信息不对称建模
增强悬疑感
中
Phase 2
P2
Story Graph 完整 Schema
基础设施
已包含在 P0 中
Phase 0

---
10.10 与现有代码的集成点
模块
当前代码
改动说明
SP Maker
interactive_fiction.py
新增 InteractiveFictionGraphMode，生成 Story Graph JSON（含 value_system + echo_points + ending_matrix）
Rollout
rp_rollout/
新增 Story Graph 执行引擎，按节点推进 + 数值追踪 + echo 注入
Evaluator
rubric_evaluator/
新增选择意义感、收束满意度等评估维度
Auditor
新增
实现分层审计 + 修复闭环
生成链路Pipeline
互动小说生成 Pipeline — QA 质量保证文档
最后更新：2026-04-14 v2
负责人：—

---
一、系统概述
1.1 架构
5+1 Agent 剧本制互动小说生成系统。核心思路：分离「规划」和「写作」。
- Director Agent：Seed → 完整 Story Graph（JSON）
- Branch Writer：每条分支独立生成叙事文本
- Dead End Worker：批量生成死结局短文本
- Pearl String Worker：主线变体改写
- PostWriteValidator：AI 写作痕迹检测
- Auditor：结构 + 连续性 + 信息边界 + 结构质量审计
1.2 代码位置
模块
路径
Pipeline 代码
<PROJECT_ROOT>/pipeline/
Rollout Snippet
<ROLLOUT_PLATFORM>/novel_snippet.py
提交脚本
<ROLLOUT_PLATFORM>/submit_novel.py
Seed 数据
<PROJECT_ROOT>/data/
输出目录
<PROJECT_ROOT>/outputs/
设计文档
<PROJECT_ROOT>/docs/interactive_novel_design.md
QA 测试脚本
<PROJECT_ROOT>/qa/test_pipeline.py
1.3 版本历史
版本
日期
变更
v1
2026-04-14
初始版本：基础连通性检查（6条规则），无结构质量检查
v2
2026-04-14
泛化结构质量检查：6条反模式规则、门控字段、质量自检清单

---
二、QA 检查项
2.1 Seed 数据格式
检查项
级别
标准
文件格式
ERROR
每行合法 JSON
必需字段
ERROR
必须包含 id、seed_content
seed_content 长度
ERROR
>= 50 字符
config 字段
WARNING
推荐包含 max_branches、max_dead_ends、language
Seed 数据示例：
{
  "id": "seed_001",
  "seed_content": "## 故事种子：维多利亚侦探悬疑\n...",
  "config": {
    "max_branches": 3,
    "max_dead_ends": 10,
    "language": "zh"
  }
}
2.2 Story Graph 结构
基础结构
检查项
级别
标准
文件格式
ERROR
合法 JSON
必需字段
ERROR
必须有 nodes、entry_node_id
推荐字段
WARNING
title、genre、characters、branches、value_system
节点数量
ERROR
>= 10 个节点
选择节点
ERROR
>= 2 个选择点
死结局
ERROR
>= 1 个死结局
正常结局
ERROR
>= 3 个正常结局（v2 要求，原 >= 1）
角色列表
WARNING
>= 2 个角色
图连通性
检查项
级别
标准
入口节点存在
ERROR
entry_node_id 在 nodes 中
BFS 可达性
ERROR
从入口出发，不可达节点占比 <= 10%
选项目标存在
ERROR
所有 choice 的 target_node_id 在 nodes 中
选择点有选项
ERROR
每个 choice 类型节点至少 2 个选项
无孤立节点
WARNING
除入口外，每个节点有前驱
分支系统
检查项
级别
标准
分支类型标注
WARNING
每个分支有 branch_type（strong/pearl_string/value_based）
分支节点存在
ERROR
分支引用的 node_ids 全部存在
死结局有死因
WARNING
每个 dead_end 节点有 death_cause 或 death_description_hint
结局有类型
WARNING
每个 ending 节点有 ending_type
死结局可达
WARNING
每个 dead_end 的 prev_nodes 中至少一个前驱的 next_nodes 包含该死结局（v2 新增）
数值系统（v2 强制要求）
检查项
级别
标准
维度定义
ERROR
value_system 必须包含 attributes（v2 从可选改为必选）
维度完整性
WARNING
每个维度有 name + initial/range
阈值可达
WARNING
通过正常路径可以触达各结局的数值阈值
属性被引用
WARNING
定义的属性必须被至少一个选项的 value_effects 引用（v2 新增）
结局有门控
WARNING
ending 节点应有 ending_condition 引用数值属性（v2 新增）
v2 结构质量检查（泛化反模式检测）
以下 6 项检查适用于任何 story graph，由 StoryGraph.validate() 和 Auditor._check_structural_quality() 自动执行：
检查项
类别标签
级别
标准
伪选择检测
pseudo_choice
WARNING
所有选项指向同一 target_node_id 且 max value_effect delta <= 1 → 选择无实质影响
漏斗收束检测
funnel_convergence
WARNING
分支后所有路径收束到同一节点，且合流后无 auto_route 分化、无差异化 facts
数值系统引用
value_system_unused
WARNING
value_system 中定义的属性必须被 value_effects 引用，否则属于数值空转
结局多样性
ending_insufficient
WARNING
正常结局 >= 3 个，且 ending_type 种类 > 1（结局不能同质化）
结局门控条件
ending_no_condition
WARNING
有数值系统时，ending 节点应有 ending_condition 以实现数值分流
选择数值影响
low_value_impact
WARNING
<= 50% 的选择点没有 value_effects → 前期选择对后续无数值积累
死结局连通性
dead_end_connectivity
WARNING
dead_end 节点的 prev_nodes 中至少一个前驱的 next_nodes 包含该节点
v2 验证效果：v1 版 seed001 检出 5 个问题（1x pseudo_choice, 3x funnel_convergence, 1x ending_insufficient），v2 修复后 0 个。
2.3 v2 新增 Schema 字段
ChoiceOption 新增字段
字段
类型
说明
gate_condition
dict or null
数值门控条件，限制选项可用性（如 {"clues": ">=5"}）
gate_branch
dict or null
条件分支路由（含 condition, true_target, false_target）
locked_hint
str
条件不满足时显示的提示文本
StoryNode 新增字段
字段
类型
说明
auto_route
dict or null
分支路径自动路由（如 {"branch_a": "node_x", "branch_b": "node_y"}）
ValueSystem 新增字段
字段
类型
说明
routing_rules
list
条件路由规则列表
2.4 Director Prompt 规则（v2）
第 6 条（反模式规则）：
1. 禁止漏斗收束 — 所有选项收束到同一节点且无后续差异
2. 禁止伪选择 — 所有选项指向同一 target_node_id 且 delta <= 1
3. 数值系统必须落地 — >= 50% 选择点有 value_effects，结局有 ending_condition
4. 结局多样性 — 正常结局 >= 3，由不同数值组合触发
5. 死结局不能断连 — prev_nodes 必须与前驱 next_nodes 双向一致
6. 强分支延续效应 — 收束后需 auto_route 分化
第 7 条（门控字段说明）：gate_condition / gate_branch / auto_route 的用法和格式
质量自检清单（生成后 6 条）：
1. 是否存在伪选择
2. 是否存在漏斗收束
3. 数值属性是否全部被 value_effects 引用
4. 结局是否 >= 3 且有 ending_condition
5. 死结局 prev_nodes 双向连通
6. = 50% 选择点有 value_effects
2.5 叙事文本
覆盖率
检查项
级别
标准
节点覆盖率
ERROR (< 50%) / WARNING (< 70%)
narratives.json 覆盖 story_graph 中的节点
选择节点有选项文本
WARNING
choice 类型节点的叙事包含 choices_text 或 choice_presentation
文本长度
节点类型
最小长度
最大长度
普通叙事节点
50 字符
5000 字符
死结局节点
20 字符
5000 字符
正常结局节点
100 字符
5000 字符
AI 写作痕迹检测
检查项
级别
标准
填充词密度
WARNING
<= 0.3 次/千字
段落均匀度
WARNING
段落长度变异系数 >= 0.25（太均匀 = AI 特征）
检测的填充词（中文）：然而 / 不禁 / 心中暗想 / 一股 / 莫名的 / 不由得 / 显然 / 毫无疑问 / 值得注意的是 / 事实上 / 缓缓 / 微微 / 轻轻 / 淡淡 / 默默 / 目光中闪过 / 嘴角微扬 / 仿佛 / 似乎 / 宛如 / 犹如 / 恍若 / 与此同时 / 在这一刻 / 就在此时 / 深吸一口气 / 紧握双拳 / 攥紧了拳头
检测的填充词（英文）：However / Moreover / Furthermore / It's worth noting / couldn't help but / a sense of / In fact
2.6 审计报告
检查项
级别
标准
文件存在
ERROR
audit_report.json 已生成
结构性错误
WARNING
无 severity=error 的结构性问题
AI 写作检测
WARNING
AI 写作痕迹 <= 3 处
审计覆盖的检查类别：
- 结构完整性（graph_integrity）
- 道具线索追踪（item_tracking）
- 角色在场检查（character_presence）
- 名称一致性（name_consistency）
- 死结局因果链（dead_end_causality）
- 叙事覆盖（narrative_coverage）
- 时间线顺序（timeline）
- 结构质量（structural_quality）— v2 新增，含伪选择/漏斗收束/数值空转/结局门控/结局数量/数值影响

---
三、Rollout 平台 分布式执行 QA
3.1 Snippet 接口
检查项
级别
标准
calculate 函数存在
ERROR
Rollout 平台 入口必须叫 calculate（不是 process）
process 函数存在
ERROR
per-record 处理逻辑
calculate 是 async
WARNING
应为 async def
Worker CLAUDE.md 模板
ERROR
WORKER_CLAUDE_MD 变量存在
User System Prompt
ERROR
USER_SYSTEM_PROMPT 变量存在
multi_round_agent 调用
ERROR
process 中调用 multi_round_agent.run
3.2 提交配置
检查项
级别
标准
SNIPPET_ID
ERROR
已设置为 3919
共享存储路径前缀
ERROR
以 data/ 开头（不是 users/）
agents_config
ERROR
包含 user + worker 两个 agent
agent_type
ERROR
claude-code-tmux
volume_name
ERROR
example-volume
成功检测逻辑
ERROR
使用 data.task_id 判断
3.3 已知踩坑记录
问题
根因
修复
"文件中没有找到 calculate 函数"
snippet 只有 process 没有 calculate
添加 async def calculate() 聚合函数
seed_001.jsonl not exist
共享存储路径缺少 data/ 前缀
DEFAULT_INPUT_PATH 改为 data/users/...
误报提交失败
Rollout 平台 API 返回 status=0 不是 code=0
改为检查 data.task_id
budget 额度不足
726191D8 已超额
换用 B5F5397A budget code
Director 输出截断
~25k chars JSON 触发 max_tokens
提升 max_tokens 到 32000
Writer JSON 解析失败
LLM JSON 转义不规范
多层修复：_repair_json + _parse_json_robust
snippet 更新未生效
本地修改但未重新注册到 Rollout 平台
需通过 Rollout 平台 Web UI 重新上传 snippet

---
四、输出文件清单
每个 seed 应产出以下文件：
文件
必需
说明
story_graph.json
是
结构化故事图
narratives.json
是
各节点叙事文本
audit_report.json
推荐
审计报告
story_readable.txt
可选
人类可读故事文本
world_bible.txt
可选
世界观摘要
graph_summary.txt
可选
图结构摘要
输出目录命名规范：output_llm_v{N}（v2 → v3 → v4 → v5 递增）

---
五、可视化（v2 新增）
generate_viz.py 生成的交互式 HTML 图包含：
- 边标签显示 value_effects（绿色）
- 门控条件显示虚线 + 锁图标（黄色）
- 详情面板显示 gate_condition、gate_branch、auto_route 信息
- 结局类型标签：cold_ending、bittersweet_ending
- 图例新增「数值门控」图标

---
六、自动化测试
测试脚本路径：<PROJECT_ROOT>/qa/test_pipeline.py
运行方式：
python3 test_pipeline.py                          # 全部测试
python3 test_pipeline.py --only seed,graph,snippet  # 指定类别
python3 test_pipeline.py --output-dir /path/to/v5   # 指定输出目录
python3 test_pipeline.py -v                         # verbose
测试类别：seed / graph / narrative / audit / snippet / submit / pipeline / e2e
输出：qa_report.json（含 summary + 每条测试结果）

---
七、质量标准总结
P0（必须通过，否则不可交付）
- Story Graph JSON 合法且结构完整
- 入口节点存在，>= 70% 节点可达
- = 10 节点、>= 2 选择点、>= 3 正常结局（v2 要求）、>= 1 死结局
- 叙事文本覆盖 >= 50% 节点
- Rollout 平台 snippet 有 calculate 入口函数
- 数值系统定义且属性被引用（v2 要求）
P1（重要质量指标）
- 叙事覆盖 >= 70% 节点
- 死结局有死因标注且双向连通
- 结局有类型标注且有 ending_condition
- AI 写作痕迹控制在阈值内
- 审计报告无结构性错误
- 无伪选择、无漏斗收束（v2 结构质量检查全通过）
- = 50% 选择点有 value_effects（v2 要求）
P2（锦上添花）
- 段落长度变异系数 >= 0.25
- 所有可选输出文件生成
- 选择节点叙事包含选项文本
- gate_condition 用于 >= 2 个选项
- auto_route 用于 >= 1 个节点
- 结局由不同数值组合触发