# AVG Game Toolkit V1 Handoff

这是一份可交给队友继续协作的 AVG / 互动视频游戏工具包。它把三件事拆开：

- `tool_core/`: 生成工具链，负责从项目输入、剧情规划、多 agent 写作、素材 prompt、runtime package 到校验报告。
- `runtime_container/`: 可换皮的游戏容器，负责把 `runtime_game_package.json` 和资产渲染成可玩的网页 AVG。
- `playable_games/`: 已打包好的可玩案例；当前包含 `zhuxian_qimai_huiwu_v1`，只要有 JSON 和资产就能直接开服试玩。

这份 handoff 不包含 API key 或 `.secrets`。素材生成要使用外部密钥时，请在本机显式传入 `--provider-env-file`。

## 这套工具要解决什么

我们的目标不是只做“文游 JSON”，也不是只做“漂亮网页壳”。目标是把一个互动故事项目拆成稳定的生产链路：

1. 用户输入题材、角色、时长、结局数、核心冲突、素材许可。
2. Planner 先定义核心问题、情绪锚点、分支压力和生产边界。
3. Story Graph / World Character / Mechanics / Scene Dramaturgy / Narrative 等 agent 分工产出剧情、人物、机制和可玩文本。
4. Art / Video / UI / Audio agent 产出素材槽位和 provider-ready prompt。
5. 工具层编译出 `runtime_game_package.json`，并校验节点、选择、结局、状态、素材引用。
6. 运行容器只读取 JSON 和资产，不写死某个游戏的剧情。
7. 后续可以替换容器：现在是 HTML AVG 容器，之后可以导出 RenPy、做恋爱/悬疑/解谜等不同皮肤。

一句话：`tool_core` 负责“把故事生产成结构化游戏包”，`runtime_container` 负责“把游戏包表现成可玩体验”。

## 目录说明

```text
avg_game_toolkit_v1/
  README.md
  start_zhuxian_preview.sh
  tool_core/
    bin/                         # pipeline 入口脚本
    schemas/                     # 数据契约
    agent_instructions/          # agent 角色说明
    runtime/fixed_avg_runtime/   # 工具内置 runtime 模板
    docs/                        # 工具链设计和历史对比文档
    media_asset_pipeline/        # 素材生产链路文档与示例
  runtime_container/
    fixed_avg_runtime/           # 单独拎出的网页 AVG 容器
  playable_games/
    zhuxian_qimai_huiwu_v1/
      runtime/                   # 可直接 serve 的 HTML runtime + runtime_game_package.json
      assets/                    # JSON 引用到的真实素材
      asset_package_summary.json # 游戏包摘要
      README.md                  # 这版游戏的运行和资产说明
```

## 先试玩当前案例

在本目录执行：

```bash
./start_zhuxian_preview.sh 8062
```

然后打开：

```text
http://127.0.0.1:8062/runtime/
```

如果端口被占用，可以换一个：

```bash
./start_zhuxian_preview.sh 8063
```

## 生成一个新游戏

建议把新项目放在 handoff 包外或 handoff 根目录下的 `games/`，不要写进 `tool_core/`。

```bash
mkdir -p games
python tool_core/bin/init_game_case.py my_game_v1 --games-root ./games
```

然后填写：

```text
games/my_game_v1/intake/project_intake.json
```

如果只想准备 agent 工作区，不真正调用 Claude Code：

```bash
python tool_core/bin/run_pipeline.py my_game_v1 \
  --games-root ./games \
  --stages agents \
  --parallelism 4 \
  --pipeline-profile fast \
  --context-mode minimal
```

如果要真实调用 agent：

```bash
python tool_core/bin/run_pipeline.py my_game_v1 \
  --games-root ./games \
  --stages all \
  --parallelism 4 \
  --pipeline-profile fast \
  --context-mode minimal \
  --run-agents \
  --agent-model-profile mixed \
  --agent-attempts 2 \
  --agent-timeout-sec 900 \
  --agent-hard-timeout-sec 7200
```

`--parallelism` 会并发执行依赖已经满足的阶段；`--pipeline-profile fast` 会放宽部分下游规划阶段的依赖，让世界观/角色、素材 prompt、音频 prompt 等更早启动。

## Prompt-only 工作流

如果现在只想产出文本、结构、prompt 和 runtime 预览，不跑付费素材生成：

```bash
python tool_core/bin/run_pipeline.py my_game_v1 \
  --games-root ./games \
  --stages init,plan,story_graph,world_character,mechanics,scene_dramaturgy,narrative,compile,runtime_enrich,validate,runtime_preview,runtime_agent,art_video_ui_prompts,audio_prompts,manifest,checker,index \
  --parallelism 4 \
  --pipeline-profile fast \
  --context-mode minimal \
  --run-agents
```

这会产出：

- `playtest/text_playtest_pack.json`
- `runtime_package/runtime_game_package.json`
- `runtime_preview/`
- `prompts/prompt_pack.json`
- `prompts/audio_prompt_pack.json`
- `manifests/generation_manifest.json`
- `reports/coherence_audit_report.md`

## 素材生成工作流

素材生成需要用户明确同意，并且 provider manifest 也允许生成。密钥文件不要提交进 handoff 包。

```bash
python tool_core/bin/run_pipeline.py my_game_v1 \
  --games-root ./games \
  --stages manifest,generate_assets,runtime_preview,index \
  --allow-paid-generation \
  --provider-env-file /absolute/path/to/provider_keys.env \
  --asset-workers 4 \
  --skip-existing-assets
```

当前支持的关键参数：

- `--provider-env-file`: dotenv 风格的 provider key 文件。
- `--asset-workers`: 并发素材 worker 数。
- `--skip-existing-assets`: 已经存在的素材不重复生成。
- `--only-asset-provider`: 只跑某一种 provider，适合补图或补视频。

## 主要阶段

```text
init
plan
story_graph
world_character
mechanics
scene_dramaturgy
narrative
compile
runtime_enrich
validate
runtime_preview
runtime_agent
art_video_ui_prompts
audio_prompts
manifest
generate_assets
checker
index
```

其中：

- `plan`: 确定项目核心问题、情绪锚点、范围、权限和跨学科约束。
- `story_graph`: 产出可玩的节点图、分支、路线矩阵和媒体钩子。
- `world_character`: 产出角色、地点、道具、关系和知识边界。
- `mechanics`: 产出数值、flag、route gate、结局和失败规则。
- `scene_dramaturgy`: 产出每一场的冲突、转折、段落预算和回调。
- `narrative`: 写成玩家可读的段落、对白、选择文案和文本试玩包。
- `compile`: 把文本试玩包编译成 runtime package。
- `runtime_enrich`: 把人物和机制信息补进 runtime package。
- `validate`: 检查图结构、选择、结局、状态和素材引用。
- `art_video_ui_prompts`: 产出图片、视频、UI 素材槽位和 prompt。
- `manifest`: 把 prompt pack 转成 provider generation manifest。
- `generate_assets`: 调 provider 生成实际素材。
- `checker`: 做跨学科一致性、可玩性和素材安全审计。

## 容器边界

容器只应该依赖：

- `runtime_game_package.json`
- package 中声明的 `engine_contract.asset_base_path`
- assets 目录里的图片、视频、音频

容器不应该依赖：

- agent workspace
- planner 中间文件
- provider key
- 某个具体游戏的硬编码节点或角色名

因此后续可以并行做多套容器：

- 玄幻比武 AVG 容器
- 恋爱/校园容器
- 悬疑调查容器
- 解谜/抽牌/roll 点容器
- RenPy exporter

只要它们都吃同一个 `runtime_game_package.json` 契约，就可以共享工具链产物。

## 当前已知缺口

- `segments[].show_layers` 现在 runtime 支持，但当前游戏包里还没有由 pipeline 稳定产出，所以角色立绘切换仍有一层 runtime 推断逻辑。
- 视频目前按 node 级 cinematic 处理；后续 story graph / scene dramaturgy 应该明确视频出现顺序、触发点、是否阻断对白。
- 当前 HTML 容器已经能玩，但作为“游戏器”还偏 AVG 文本框，需要继续做皮肤、输入、小交互和类型化玩法。
- RenPy 还没有 exporter；但现有 JSON 契约已经可以作为 RenPy 转换的输入。
- 素材 prompt 和素材引用已经分开，但角色透明立绘、表情差分、背景 CG 的资产规范还需要更严格。

## 建议分工

- Story Graph pipeline: 重点看 `tool_core/` 的 pipeline、agent prompt、数据契约和并行策略。
- 派蒙: 重点看 `runtime_container/`，继续做容器 UI、皮肤、小交互、可玩性增强。
- 大可: 维护 showcase、项目 intake、案例包和团队协作节奏。

后续讨论时，建议围绕一个问题推进：同一个 `runtime_game_package.json`，怎么让不同容器把它变成不同类型的游戏体验。
