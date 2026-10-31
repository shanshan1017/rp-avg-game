# 使用手册 — Interactive Novel / AVG 游戏生成系统

本手册覆盖从「玩 Demo」到「从零生成一个新游戏」的完整流程。项目总览见 [README.md](README.md)。

---

## 目录

1. [系统架构](#1-系统架构)
2. [环境要求](#2-环境要求)
3. [快速开始:玩 Demo](#3-快速开始玩-demo)
4. [端到端生成流程](#4-端到端生成流程)
5. [游戏模板开发](#5-游戏模板开发)
6. [avg_game_toolkit_v1 工具包](#6-avg_game_toolkit_v1-工具包)
7. [outputs 产物说明](#7-outputs-产物说明)
8. [运行 QA 测试](#8-运行-qa-测试)
9. [环境变量汇总](#9-环境变量汇总)
10. [FAQ](#10-faq)

---

## 1. 系统架构

「剧本制」多 Agent 分工,每个角色只做一件事:

```
Seed(故事种子)
   │
   ▼
Director Agent ──► story_graph.json     全局规划:分支结构、数值系统、后果回声
   │
   ▼
Writers(并行)──► narratives.json       只看局部上下文写各节点叙事
   │                                     (BranchWriter / DeadEndWriter / PearlStringWriter)
   ▼
Auditor        ──► audit_report.json    规则化审计:图完整性、假选项、数值一致性
   │
   ▼
asset_generator ─► 背景图 / 立绘         调用图片生成 API + manifest
   │
   ▼
build_game     ──► game_xxx.html        单文件可玩 AVG 游戏(模板注入)
```

对应代码:`pipeline/`(Director/Writers/Auditor)→ `avg_engine/`(资产生成 + 游戏编译)。

## 2. 环境要求

- Python 3.10+
- 第三方依赖仅一个:`pip install requests`(只在 LLM 模式和图片生成时用到;离线模式、玩 Demo、跑测试均为纯标准库)
- 浏览器(玩游戏用,Chrome/Safari/Firefox 均可)

## 3. 快速开始:玩 Demo

在仓库根目录起一个静态服务器:

```bash
cd <仓库根目录>
python3 -m http.server 8788 --bind 0.0.0.0
```

浏览器打开(远程开发机场景把 `localhost` 换成机器 IP,或先建 SSH 隧道 `ssh -L 8788:localhost:8788 <开发机>`):

| URL | 内容 |
|---|---|
| `http://localhost:8788/demos/game_victorian_mystery_001.html` | 维多利亚密室推理(seed001) |
| `http://localhost:8788/demos/game_sakura_parallel_003.html` | 樱花平行世界(seed003,樱花皮肤模板) |
| `http://localhost:8788/outputs/story_tree_viz.html` | 三个种子的故事树可视化 |
| `http://localhost:8788/outputs/seed001/story_graph_viz.html` | 单个故事图可视化 |

两个游戏完全自包含(图片资产已本地化在 `demos/assets/`),唯一外部请求是 Google Fonts 字体,断网也能玩(字体回退)。

不想开浏览器也可以直接读 `outputs/seed001/story_readable.txt` —— 全部分支的可读全文。

## 4. 端到端生成流程

### Step 0 — 准备 Seed

Seed 是一段 JSON,描述故事题材、基调、核心冲突。现成的在 `data/`:

- `data/seed_001.jsonl` / `seed_003.jsonl` — 单个种子
- `data/seeds_100.jsonl` — 100 个多题材种子
- 重新生成种子库:`python3 data/gen_seeds.py`(输出到 `data/seeds_100.jsonl`)

### Step 1 — 生成故事(Story Graph + 叙事 + 审计)

**离线模式**(不调 LLM,用内置示例跑通全流程,验证环境用):

```bash
python3 pipeline/pipeline.py --mode offline
```

**LLM 模式**(真实生成,需要 OpenAI/Anthropic 兼容 API):

```bash
python3 pipeline/pipeline.py --mode llm \
    --seed-file data/seed_001.jsonl \
    --output-dir outputs/my_story \
    --model claude-sonnet-4-6 \
    --api-base https://<your-llm-api>/v1 \
    --api-key <your-key>
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `--mode` | `offline` / `llm` | `offline` |
| `--seed-file` | seed 文件路径(llm 模式必填) | — |
| `--output-dir` | 产物输出目录 | `outputs/` |
| `--model` | 模型名 | 环境变量 `LLM_MODEL`,否则 `claude-sonnet-4-6` |
| `--api-base` / `--api-key` | LLM API 地址与密钥 | 环境变量 `LLM_API_BASE` / `LLM_API_KEY` |
| `--extra-requirements` | 附加给 Director 的创作要求 | 空 |
| `--extra-header` | 额外 HTTP 头,可重复,格式 `'Key: Value'` | — |

产出:`story_graph.json`、`narratives.json`、`world_bible.txt`、`audit_report.json`(各文件含义见[第 7 节](#7-outputs-产物说明))。

### Step 2 — 可视化检查(可选但推荐)

```bash
python3 pipeline/generate_viz.py outputs/my_story/story_graph.json -o outputs/my_story/story_graph_viz.html
```

浏览器打开生成的 HTML,人工检查分支结构、死路、汇合点是否合理。审计未通过的问题看 `audit_report.json`。

### Step 3 — 生成图片资产

需要一个 OpenAI Images 兼容的图片生成 API:

```bash
export IMAGE_API_URL="https://<your-image-api>/v1/images/generations"
export IMAGE_API_KEY="<your-key>"

python3 avg_engine/asset_generator.py \
    --story-graph outputs/my_story/story_graph.json \
    --output-dir avg_engine/assets/my_story \
    --stage all \
    --workers 3
```

- `--stage`:`all` / `images`(背景图)/ `characters`(立绘),可分阶段跑
- `--workers`:并发请求数
- 产出:图片文件 + `manifest.json`(资产清单,供下一步注入)

### Step 4 — 编译可玩游戏

```bash
python3 avg_engine/build_game.py \
    --story-graph outputs/my_story/story_graph.json \
    --narratives outputs/my_story/narratives.json \
    --manifest avg_engine/assets/my_story/manifest.json \
    --template avg_engine/templates/game_template.html \
    --output my_game.html
```

- `--template`:`game_template.html`(默认深色 UI)或 `game_template_sakura.html`(樱花粉皮肤)
- 产出是**单文件 HTML**,通过静态服务器打开即可玩(见第 3 节)

辅助工具:`avg_engine/parse_narratives.py` 可把 `story_readable.txt` 反向解析回结构化 narratives JSON(处理只有可读全文的历史产物时用)。

## 5. 游戏模板开发

模板在 `avg_engine/templates/`,是完整的 HTML + CSS + JS,通过注释占位符接收数据(`build_game.py` 的 `inject_into_template()` 负责替换):

| 占位符 | 注入内容 |
|---|---|
| `<!-- GAME_DATA_PLACEHOLDER -->` | `<script>` 标签,定义 `GAME_DATA`(story + narratives + assets) |
| `<!-- TITLE_PLACEHOLDER -->` / `<!-- MAIN_TITLE_PLACEHOLDER -->` | 游戏标题 |
| `<!-- SUBTITLE_PLACEHOLDER -->` | 副标题 |

**注意:直接在浏览器打开模板文件会白屏**,因为 `GAME_DATA` 未定义(控制台报 `GAME_DATA is not defined`)。调试模板 UI 的两种方式:

1. **推荐**:改完模板后用 Step 4 的命令以现成产物(如 `outputs/seed003/`)重新编译,看编译结果;
2. 临时在模板 `<!-- GAME_DATA_PLACEHOLDER -->` 处手工粘贴一段 `<script>const GAME_DATA = {...}</script>` 假数据。

模板 JS 入口逻辑在文件尾部:读取 `GAME_DATA.story / .narratives / .assets`,渲染节点文本、立绘、选项按钮,维护数值系统与存档(localStorage)。

## 6. avg_game_toolkit_v1 工具包

`avg_game_toolkit_v1/` 是更完整的三层游戏生产架构(与第 4 节的单机流程独立,面向多 Agent 协作生产):

```
tool_core/           生产工具层:pipeline 编排、agent 指令、schema、providers
runtime_container/   通用 AVG 网页运行时(index.html + app.js + styles.css,可换皮)
playable_games/      打包成品(runtime_game_package.json + 网页壳)
```

`tool_core/bin/` 主要入口:

| 脚本 | 用途 |
|---|---|
| `run_pipeline.py` | 编排整条生产链(agent 阶段默认 prepare-only,加 `--run-agents` 才真正调用;付费生成需另行显式执行) |
| `init_game_case.py` | 初始化一个新游戏案例目录 |
| `check_story_graph_plan.py` | 校验故事图规划(planning gate) |
| `build_generation_manifest.py` / `execute_generation_manifest.py` | 生成/执行媒体资产清单(图片、音频、视频 provider) |
| `compile_runtime_package.py` / `enrich_runtime_package.py` / `validate_runtime_package.py` | 编译、增强、校验 runtime 游戏包 |
| `play_text_game.py <pack>` | 终端里纯文本试玩一个游戏包(`--path 1,2,1` 可脚本化走分支,`--show-assets` 显示资产引用) |
| `run_claude_agent.py` | 以隔离 worker 方式调用 Claude Code 执行 agent 阶段 |

诛仙案例预览:`./start_zhuxian_preview.sh [端口]`(默认 8062)。**注意**:本仓库只含该案例的 runtime 包(JSON + 网页壳),约 400MB 的原始媒体资产未随仓库分发,预览会缺图缺音;文本试玩不受影响:

```bash
python3 avg_game_toolkit_v1/tool_core/bin/play_text_game.py \
    avg_game_toolkit_v1/playable_games/zhuxian_qimai_huiwu_v1/runtime/runtime_game_package.json
```

详细设计见 `avg_game_toolkit_v1/README.md` 与 `tool_core/docs/`。

## 7. outputs 产物说明

每个种子目录(`outputs/seed001` 等)包含:

| 文件 | 内容 |
|---|---|
| `story_graph.json` | Director 输出的故事图:节点、边、分支类型、数值系统、后果回声 |
| `narratives.json` | Writers 输出的各节点叙事文本(结构化,含选项文案) |
| `world_bible.txt` | 世界观设定集(人物、地点、规则),Writers 的共享上下文 |
| `story_readable.txt` | 全部分支线性展开的可读全文,人工审阅用 |
| `audit_report.json` | Auditor 的审计结果:错误/警告清单及位置 |
| `story_graph_viz.html` | 交互式故事图可视化(独立打开即可) |

`outputs/story_tree_viz.html` 是三个种子的汇总故事树。

## 8. 运行 QA 测试

```bash
python3 qa/test_pipeline.py                              # 默认校验 outputs/seed001
python3 qa/test_pipeline.py --output-dir /tmp/offline    # 校验你自己跑出的产物
```

覆盖 6 类:seed 格式、story graph 完整性、narrative 质量、审计报告、pipeline 代码、端到端。报告写到 `<output-dir>/qa_report.json`(已被 git 忽略),有错误时以非零退出码结束。CI 中的完整检查见 [CONTRIBUTING.md](CONTRIBUTING.md#5-本地开发)。

## 9. 环境变量汇总

| 变量 | 用途 | 使用处 |
|---|---|---|
| `LLM_MODEL` / `LLM_API_BASE` / `LLM_API_KEY` | 故事生成 LLM | `pipeline/pipeline.py`(可被命令行参数覆盖) |
| `IMAGE_API_URL` / `IMAGE_API_KEY` | 图片生成 API(OpenAI Images 兼容) | `avg_engine/asset_generator.py` |
| `GPT_IMAGE_BASE_URL` / `GPT_IMAGE_API_KEY` | 图片 provider | `tool_core/providers/gpt_image.py` |
| `MINIMAX_API_KEY` / `MINIMAX_BASE_URL` | 音频 provider(TTS/配乐/音效) | `tool_core/providers/minimax_audio.py` |
| `ARK_API_KEY` | 视频 provider | `tool_core/providers/volcengine_video.py` |

仓库不含任何密钥,全部需自备。

## 10. FAQ

**Q: 打开游戏 HTML 白屏?**
直接双击文件打开(`file://`)可能因浏览器安全策略加载不了本地资产,请用 `python3 -m http.server` 起服务后经 `http://` 访问。如果打开的是 `avg_engine/templates/` 下的文件,那是未注入数据的模板,见第 5 节。

**Q: 文档里的 `<PROJECT_ROOT>`、`<STORAGE_VOLUME>`、`api.example.com` 是什么?**
发布前脱敏的占位符,代表原内部环境的路径/服务地址,替换成你自己的环境即可。

**Q: 诛仙案例没有图和声音?**
原始媒体资产(约 400MB)未随仓库分发,只保留了 runtime 包结构。用 `play_text_game.py` 可完整体验文本玩法。

**Q: 图片生成用什么服务?**
任何 OpenAI Images API(`/v1/images/generations`)兼容的服务都可以;音频/视频 provider 分别对接 MiniMax 与火山引擎 ARK,均可在 `tool_core/providers/` 里替换。

**Q: 想加一个新的游戏皮肤?**
复制 `avg_engine/templates/game_template.html` 改样式,保留三个占位符注释,编译时 `--template` 指向新文件即可。
