# 可规模化互动视频生产流水线

本文档用于把 `心动失控夜` 的制作方式沉淀成可复用链路。以后输入新的剧本、主题或主角设定时，先走这条流水线，再交给两个 Claude Code agent 分别执行和检查。

核心原则：先锁故事图和 runtime 资产合同，再生成素材。任何不会被当前游戏读取、展示或播放的素材，都不进入批量生成任务。

## 输入合同

每个新项目先准备一个 project brief。推荐从 `templates/project_brief.template.json` 复制，并填入以下信息：

- `game_id`：项目唯一 ID，用于输出目录和 manifest。
- `title`：游戏标题。
- `runtime_target`：当前默认 `html_video_engine`，后续可扩 `godot_video_engine`。
- `session_length_sec`：单局目标时长，当前标准为 60-90 秒。
- `node_duration_sec`：单节点视频时长，当前标准为 8-15 秒。
- `pov_rule`：是否第一视角、主角是否出镜。
- `style_profile`：引用 `data/style_bible/visual_style.md` 或新的风格文件。
- `characters`：只列会出现在镜头或 UI 中的角色。
- `story_seed`：粗故事、节点草案或完整剧本。
- `runtime_asset_contract`：前端实际会读取的资产类型。
- `multi_agent_production`：Planning / Executive / Checker 三角色和 gate 权限。

`runtime_asset_contract` 是最重要的字段。它必须回答：这些素材会不会被游戏展示？展示在哪？路径由谁引用？如果答不上来，就先不生成。

## 不变量

### 1. 故事图先于局部剧本

顺序固定：

1. Director 产出完整 story graph。
2. Auditor 检查节点连通、路径时长、失败/结局条件。
3. Detail Agent 扩写每个节点的 8-15 秒短剧本。
4. Prompt Agent 扩写首帧图和视频 prompt。
5. Asset Runner 才能调用生成接口。

不要先写漂亮桥段，再倒推结构。互动视频最容易坏在分支断裂和路径超时。

### 2. Runtime 资产合同先于生成

每次生成前必须先输出一张资产表：

| 资产类型 | 是否被 runtime 读取 | 前端字段/文件 | 数量 | 生成动作 |
| --- | --- | --- | ---: | --- |
| 角色参考图 | 是/否 | `characterRefs` 等 | N | 生成/复用/跳过 |
| 节点 poster | 是/否 | `video.poster` | N | 生成/复用/跳过 |
| 节点视频 | 是/否 | `video.src` | N | 生成/复用/跳过 |
| UI 图片 | 是/否 | 具体字段 | N | 生成/跳过 |
| 独立音频 | 是/否 | 具体字段 | N | 生成/跳过 |

当前 `心动失控夜` HTML runtime 只读取 4 张角色参考图、16 张节点 poster、16 段节点视频。尾帧只作为后续重跑衔接素材，不在当前 UI 中展示。

### 3. 风格锁必须可复制

所有 prompt 必须拼接统一风格前缀、角色一致性锚点和负面约束。当前风格文件是：

- `data/style_bible/visual_style.md`
- `data/style_bible/characters.md`

新项目如果换画风，先新建一个 style profile，不要在单个节点 prompt 里临时改风格。

### 4. 角色一致性先生成角色，再生成视频

角色生成顺序固定：

1. 角色视觉 Bible。
2. 角色主参考图。
3. 角色 contact sheet 审核。
4. 节点 poster。
5. 节点视频。

第一视角男主不需要角色参考图。除非项目改成第三视角，否则主角只需要 `protagonist_visibility_rule`，不生成主角图。

### 5. 本地文件优先，短期 URL 不进游戏

图像和视频接口返回的 URL 都必须下载到本地。`game_data.js` 和 manifest 只写本地相对路径，不写平台签名 URL，不写 API key。

## Multi-Agent 分工

最少三个角色：

- Planning Agent：当前 Codex，负责计划、拆解、交接和最终 gate 判断。
- Executive Agent：Claude Code 1，负责按批准计划执行 prompt / generation / manifest 工作。
- Checker Agent：Claude Code 2，负责独立只读验收，输出阻断问题和重跑建议。

### Planning Agent

负责：

- 需求澄清和 project brief。
- 规划完整 storyline。
- 输出 story graph / story bible / script table / asset plan。
- 控制路径长度、失败点和多结局。
- 定义状态变量和分支条件。
- 定义 runtime asset contract。
- 写 Executive / Checker handoff prompt。

不能做：

- 未经用户批准启动批量付费生成。
- 跳过 Checker 直接进入下一 gate。
- 临时添加没有前端字段承接的新资产。

### Executive Agent

负责：

- 读取 Planning 交接包。
- 把 story graph 扩写为节点短剧本，或按已批准短剧本继续执行。
- 写角色图 prompt。
- 写节点 poster prompt。
- 写视频 prompt。
- 组合风格前缀、角色锚点、负面约束。
- 调用图片和视频生成脚本。
- 保存请求 payload、任务 ID、轮询结果和本地文件。
- 更新 manifest。
- 写 `execution_report.md`。

不能做：

- 改节点连接关系。
- 新增结局或失败节点，除非 Planning 重新审核。
- 使用真人、明星、现有 IP 作为参考。
- 把 UI、字幕、按钮、logo 写进画面。
- 把 API key 写入仓库。
- 把平台短期 URL 写入前端配置。
- 批量生成 runtime 未使用的素材。

### Checker Agent

负责：

- 只读检查 Planning 交接包和 Executive 输出。
- 检查资源引用是否存在。
- 检查风格、角色一致性、第一视角和安全规则。
- 检查 schema、runtime 字段、manifest redaction 和本地路径。
- 输出 `qa_report.md` / `acceptance_report.json`。
- 只标记需要重跑的 asset id / node id。

不能做：

- 因为“也许以后有用”要求生成额外素材。
- 直接修复正式资源。
- 提交生成任务。
- 和 Executive 共用未记录假设。

## 多 Agent 交接物

Planning 必须交给 Executive 和 Checker：

- project brief。
- story bible。
- script table。
- asset plan。
- runtime asset contract。
- style profile。
- 当前 gate id。
- allowed write scope。
- forbidden changes。
- acceptance criteria。

Executive 必须产出：

- prompt pack。
- provider payload drafts 或 task records。
- 本地素材文件。
- generation manifest。
- `execution_report.md`，列出 changed files、commands、failures、deviations。

Checker 必须产出：

- `qa_report.md`。
- 可选 `acceptance_report.json`。
- `pass | pass_with_notes | fail`。
- blocker / major / minor / note 分级问题。
- rerun asset ids 和具体原因。

## 标准工作流

### Gate 0：Brief 校验

输入：

- `templates/project_brief.template.json` 复制出的项目 brief。
- 可选：用户提供的新剧本或主角设定。

输出：

- 明确 `game_id`。
- 明确 `style_profile`。
- 明确 `runtime_asset_contract`。
- 明确主角可见性规则。

失败条件：

- 没有 story seed。
- 角色年龄或安全边界不清。
- 需要生成的资产没有 runtime 展示路径。

### Gate 1：Story Graph

输出：

- `data/seeds/<game_id>_story_graph_v0.json`
- 节点连通审计。
- 常规路径 60-90 秒。
- 所有 choice target 存在。
- 失败节点可回退或重开。

### Gate 1.5：Storyline Checker

Owner：Checker Agent。

阻断条件：

- entry node 缺失。
- choice target 不存在。
- 没有可达结局。
- failure / ending 覆盖不符合 brief。
- 典型路径明显超出目标时长。
- 状态变量没有被定义却被分支引用。

Checker 通过后，Planning 才能让 Executive 扩写细节台本。

### Gate 2：Prompt Pack

输出：

- `outputs/<game_id>/scripts.json`
- `outputs/<game_id>/character_prompts.json`
- `outputs/<game_id>/video_prompts.json`

审核：

- 所有节点都有 `node_id`。
- 视频 prompt 都包含 style prefix。
- 多角色节点包含所有出镜角色的一致性锚点。
- 负面约束覆盖真人、男主出镜、字幕、UI、水印。

### Gate 2.5：Script / Asset Contract Checker

Owner：Checker Agent。

阻断条件：

- script table 的 `required_assets` 无法映射到 asset plan。
- asset plan 里有 runtime 不会使用、却被标记为必须生成的素材。
- 节点角色、地点、选择、时长或 runtime 字段缺失。
- 第一视角规则和角色出场表不一致。

### Gate 3：角色资产

输出：

- `video_engine/public/assets/characters/<character_id>.png`
- `outputs/<game_id>/character_assets.json`
- `outputs/<game_id>/character_contact_sheet.jpg`

审核：

- 角色成年。
- 发型、服装、配饰、轮廓可区分。
- 和 style profile 一致。
- 没有真人脸或现有 IP 感。

### Gate 3.5：Prompt Safety & Reference Checker

Owner：Checker Agent。

提交生成前检查：

- prompt 没有真人、名人、现有 IP。
- poster / video references 与 `on_screen_character_ids` 一致。
- 没有把全员 cast lineup 传给单角色或无角色节点。
- 第一视角男主不出镜规则被写入相关 prompt。
- 多角色节点被标为高风险并有更严格验收标准。

### Gate 4：节点 Poster

输出：

- `video_engine/public/assets/posters/<node_id>.png`
- `outputs/<game_id>/first_frame_assets.json`
- `outputs/<game_id>/poster_contact_sheet.jpg`

审核：

- 画幅 16:9。
- 第一视角成立。
- 角色脸部位于安全区。
- 不含 UI、字幕、logo、水印。

### Gate 4.5：Generated Asset Visual Checker

Owner：Checker Agent。

生成后、入正式 manifest 前检查：

- contact sheet / still sheet 或视频抽帧证据存在。
- 角色一致性通过。
- 只出现节点声明角色。
- 无男主出镜。
- 无嵌字、水印、logo、平台痕迹。
- 画幅、清晰度、UI 安全区合格。

每个资产结论为：`approved`、`approved_with_notes`、`rerun_required` 或 `rejected`。

### Gate 5：节点视频

输出：

- `video_engine/public/assets/videos/<node_id>.mp4`
- `outputs/<game_id>/video_task_payloads.json`
- `outputs/<game_id>/video_tasks.json`
- `outputs/<game_id>/video_results.json`
- `outputs/<game_id>/video_manifest.json`

审核：

- 每段 8-15 秒。
- 第一视角不破。
- 女生角色与参考图一致。
- 节点目标清楚，结尾能自然弹出选择。
- 无嵌字、无 UI、无水印。

### Gate 5.5：Runtime Manifest Checker

Owner：Checker Agent。

build runtime 前最终阻断：

- game config 引用的所有本地路径存在。
- 无远程签名 URL。
- 无 API key。
- manifest 中没有未批准素材进入 runtime。
- runtime 必需素材都通过 Checker 或有明确 waiver。

### Gate 6：Runtime 接入

输出：

- `video_engine/public/game_data.js`
- 资源引用检查结果。
- 桌面和移动端浏览器 QA 截图。

审核：

- `game_data.js` 引用的所有本地文件存在。
- 开场、选择、失败、结局都可到达。
- UI 不遮挡关键脸部。
- 本地路径播放正常。

### Gate 6.5：Independent Final Acceptance

Owner：Checker Agent。

输出：

- `ACCEPTANCE_REPORT.md`
- `acceptance_report.json`

只有 blocker 为 0，且 major issue 有明确 waiver 时，Planning 才能允许最终打包或进入下一轮制作。

## 可扩展目录约定

```text
interactive_video_game/
  data/
    briefs/<game_id>.json
    seeds/<game_id>_story_graph_v0.json
    style_bible/<style_profile>.md
  outputs/
    <game_id>/
      scripts.json
      character_prompts.json
      video_prompts.json
      character_assets.json
      first_frame_assets.json
      video_task_payloads.json
      video_tasks.json
      video_results.json
      video_manifest.json
      ART_QA_REPORT.md
  video_engine/public/assets/
    characters/
    posters/
    videos/
```

同一个 `game_id` 的正式文件路径稳定。重跑候选放到：

```text
outputs/<game_id>/rerolls/<node_id>/<attempt_id>/
```

通过 QA 后再替换正式路径。

## Claude Code 交接标准

交给 Claude Code 前，必须附带：

- project brief。
- 当前 runtime 资产合同。
- style profile。
- character Bible。
- story graph 或 story seed。
- 明确本轮只做哪一个 Gate。

默认第一轮任务不是“生成全部素材”，而是：

1. 检查 story graph。
2. 检查 runtime 资产合同。
3. 扩写 prompt。
4. 列出将要生成的资产清单。
5. 等人工确认后再提交批量任务。

当前项目如果只做美术审计，使用 `templates/claude_code_art_pipeline_prompt.md` 中的提示词即可。

通用项目优先使用：

- `templates/claude_code_media_asset_executor_prompt.md`
- `templates/claude_code_media_asset_checker_prompt.md`

## 失败回滚规则

- 生成失败：保留 payload 和错误信息，不覆盖正式文件。
- 风格跑偏：只重跑对应节点，不批量重跑全片。
- 角色不一致：先修角色参考或 prompt，再重跑受影响节点。
- runtime 没读到资产：先修 manifest / `game_data.js`，再考虑重生素材。
- 发现新 UI 需求：先改前端字段和数据 schema，再生成 UI 图。

## 当前项目应用结论

`心动失控夜` 当前已经满足基础链路：

- 4 张角色参考图已接入。
- 16 张节点 poster 已接入。
- 16 段节点视频已接入。
- `game_data.js` 本地引用完整。
- 未接入的 logo、头像、徽章、UI 纹理、独立音频、favicon 均不生成。

下一步应由 Claude Code 做 `ART_QA_REPORT.md` 和 video contact sheet，确认哪些已展示素材值得重跑。
