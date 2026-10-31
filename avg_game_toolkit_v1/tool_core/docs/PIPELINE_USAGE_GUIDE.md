# Pipeline Usage Guide

这份文档说明如何使用 `cross_disciplinary_coherence_v1` 工具链，从项目初始化、agent 准备、文本包编译、runtime 校验，到浏览器预览。

当前状态：

- 工具层 pipeline 已能跑通。
- isolated Claude Code agent workspace 已能批量准备。
- 单个真实 checker agent 已验证能被 orchestrator 拉起并产出报告。
- 付费素材生成仍未接入执行层，当前只支持 dry-run manifest。

## 0. 入口脚本

主入口：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py <project_id>
```

常用阶段集合：

```text
--stages tool    # init, compile, validate, manifest, runtime_preview, index
--stages agents  # plan, story_graph, world_character, mechanics, scene_dramaturgy, narrative, art_video_ui_prompts, audio_prompts, runtime_agent, checker
--stages all     # tool + agents
```

也可以只跑局部阶段：

```bash
--stages init,compile,validate,index
```

## 1. 初始化一个项目

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages init,index
```

生成目录：

```text
interactive_video_game/games/my_game/
  intake/
  planner/
  agents/
  authoring/
  playtest/
  prompts/
  manifests/
  assets/
  runtime_package/
  runtime_preview/
  reports/
```

关键文件：

- `reports/pipeline_status.json`: 每个阶段状态。
- `reports/artifact_index.json`: 文件索引，说明每个产物是什么、谁生成、给谁用。
- `intake/case_metadata.json`: 默认 `paid_generation_allowed=false`。

## 2. 只准备多 agent 工作区

默认不会真的调用 Claude Code。下面命令只生成每个 agent 的隔离 workspace、handoff、TASK：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages agents
```

每个 agent 会有自己的目录：

```text
games/my_game/agents/<agent_id>/workspace/
  inbox/
  outbox/
  scratch/
  logs/
  ROLE_CONTRACT.md
  TASK.md
```

这一步适合检查：

- planner 有没有给每个 agent 清楚的任务；
- 每个 agent 能看到哪些上下文；
- expected outputs 是否合理；
- 是否有越权风险。

## 3. 真实拉起 Claude Code agent

只有加 `--run-agents` 才会真实调用 Claude Code：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages checker \
  --run-agents
```

重要说明：

- 本机实测 `claude --model sonnet-4-6` 不可用，Claude Code 返回 “selected model may not exist or no access”。
- 本机实测 `claude --model claude-sonnet-4-6` 可用。
- 本机实测 `claude --model claude-opus-4-7` 可用。
- pipeline 默认使用 `--agent-model-profile mixed`：
  - 复杂阶段用 `claude-opus-4-7`：`plan`、`story_graph`、`scene_dramaturgy`、`narrative`、`checker`。
  - 执行/素材/机制阶段用 `claude-sonnet-4-6`：`world_character`、`mechanics`、`art_video_ui_prompts`、`audio_prompts`、`runtime_agent`。
- `sonnet` / `opus` 作为通用 alias 也可用，但推荐完整模型名。

强制全部使用 Sonnet：

```bash
--agent-model-profile sonnet
```

强制全部使用 Opus：

```bash
--agent-model-profile opus
```

覆盖为某个指定模型：

```bash
--claude-model claude-sonnet-4-6
```

推荐参数：

```bash
--agent-attempts 2 \
--agent-timeout-sec 900 \
--agent-hard-timeout-sec 7200
```

`--agent-timeout-sec` 是 idle timeout：只要 stdout/stderr 或 `outbox/`、`scratch/` 有变化，就不会因为静默时间被误杀。`--agent-hard-timeout-sec` 是总墙钟保护。

## 4. 用已有 text pack 编译 runtime package

如果已经有 `text_playtest_pack.json`：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --text-pack /absolute/path/to/text_playtest_pack.json \
  --stages init,compile,validate,runtime_preview,index
```

生成：

```text
games/my_game/runtime_package/runtime_game_package.json
games/my_game/runtime_package/compile_report.json
games/my_game/runtime_package/validation_report.json
games/my_game/runtime_package/validation_report.md
games/my_game/runtime_preview/
```

## 5. 预览 runtime

进入 preview 目录：

```bash
cd interactive_video_game/games/my_game/runtime_preview
python -m http.server 8050
```

浏览器打开：

```text
http://127.0.0.1:8050/
```

runtime 会加载：

```text
runtime_game_package.json
```

可以检查：

- 首页；
- 游玩流程；
- 选择；
- state；
- 世界线；
- 点击世界线节点跳转。

## 6. 生成 dry-run 素材 manifest

如果已经有 `prompts/prompt_pack.json`：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages manifest,index
```

输出：

```text
games/my_game/manifests/generation_manifest.json
```

注意：

- 这一步不调用图像、视频、音频 API。
- manifest 只记录脱敏后的 provider request payload。
- `paid_generation_allowed=false`。
- API key 不会写入任何 manifest、报告或 runtime package。

## 7. 推荐工作流

### A. 纯工具层验证

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --text-pack /absolute/path/to/text_playtest_pack.json \
  --stages tool
```

用途：

- 快速把已有文本包变成 runtime package；
- 检查跳转、状态、素材引用、安全问题；
- 生成可浏览器预览的 runtime。

### B. 多 agent 工作区准备

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages agents
```

用途：

- 不花模型调用；
- 检查 handoff 和上下文；
- 确保 Planner 给每个部门的任务是隔离、明确、可追踪的。

### C. 局部真实 agent 测试

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages checker \
  --run-agents
```

用途：

- 验证 Claude Code 能被拉起；
- 验证 outbox 输出；
- 验证 checker 能按合同产出报告。

### D. 完整真实多 agent 生产

暂不建议直接跑，除非已经有明确项目 intake 和 Planner brief。

未来命令形态会是：

```bash
python interactive_video_game/tool_versions/cross_disciplinary_coherence_v1/bin/run_pipeline.py my_game \
  --stages agents \
  --run-agents
```

跑完后 Planner 需要审阅各 agent 的 `outbox/`，再把合格产物提升到 `authoring/`、`prompts/`、`runtime_package/`。

## 8. 如何判断一次运行成功

看：

```text
games/<project_id>/reports/pipeline_status.json
```

每个 stage 应该是：

```json
{
  "status": "completed"
}
```

或合理的：

```json
{
  "status": "skipped",
  "message": "No prompt_pack.json found."
}
```

再看：

```text
games/<project_id>/reports/artifact_index.json
```

它应该能回答：

- 哪个文件是 canonical；
- 哪个文件是中间产物；
- 这个文件由谁生成；
- 下游谁消费这个文件；
- 文件是否存在。

## 9. 当前已验证结果

已完成 smoke test：

1. `--stages agents`：成功为 10 个 agent 生成隔离 workspace。
2. `--stages checker --run-agents --claude-model sonnet`：真实拉起 Claude Code checker，耗时约 169 秒，成功产出：
   - `agents/checker/workspace/outbox/agent_report.json`
   - `agents/checker/workspace/outbox/coherence_audit_report.md`
3. 追加模型名验证：`sonnet-4-6` 不可用，`claude-sonnet-4-6` 可用并返回 `OK`。
4. 追加复杂模型验证：`claude-opus-4-7` 可用并返回 `OK`；pipeline 默认 mixed 模式已启用复杂阶段走 Opus。
3. checker 正确指出：上游 agent 是 prepare 模式，没有创作产物，所以不能进入 text playtest / generation / runtime release。

这说明：多 agent 隔离调用链路已经打通，但完整内容生产仍需要一个新的、明确的项目 intake。
