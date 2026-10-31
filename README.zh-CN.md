# RP_AVG_game — 从一个故事种子生成可玩的分支 AVG

[English](README.md) | 简体中文

> 输入一段故事种子（seed），输出一部带分支、数值和多结局的网页 AVG 游戏。

本项目把互动小说的生产拆成「剧本制」多 Agent 流水线：**Director** 先规划完整的 Story Graph，**Writers** 只拿局部上下文并行写各节点正文，**Auditor** 用规则检查结构和连贯性，最后编译成单文件 HTML 游戏，或打包给通用 runtime 播放。运行时不调用模型，产物是静态网页，可离线游玩、直接部署。

```
Seed ─► Director ─► story_graph.json ─► Writers(并行) ─► narratives.json
                                                            │
             单文件 HTML / runtime 游戏包 ◄─ build_game ◄─ Auditor ─► audit_report.json
                                 ▲
                         asset_generator（背景 / 立绘 / 视频 / 音频）
```

## 快速体验

只需要 Python 3.10+，不用安装依赖，也不需要 API Key。

```bash
git clone https://github.com/shanshan1017/rp-avg-game && cd rp-avg-game
python3 -m http.server 8000
```

| Demo | 地址 | 说明 |
|---|---|---|
| 维多利亚密室推理 | http://localhost:8000/demos/game_victorian_mystery_001.html | 单文件 HTML，背景图 + 立绘 + 分支 |
| 樱花平行世界 | http://localhost:8000/demos/game_sakura_parallel_003.html | 单文件 HTML |
| 诛仙·七脉会武 | `bash avg_game_toolkit_v1/start_zhuxian_preview.sh` → http://127.0.0.1:8062/runtime/ | toolkit runtime：41 个节点、24 个选择、5 个结局，含视频与音频 |
| 故事树可视化 | http://localhost:8000/outputs/story_tree_viz.html | 三个样例种子的分支结构 |

## 核心机制

- **Story Graph**（`pipeline/story_graph_schema.py`）定义了 6 种节点：`narrative`、`choice`、`branch_point`、`merge_point`、`dead_end`、`ending`；分支分为三种：
  - `pearl_string` 珍珠串：选项走向不同的段落，之后汇回主线
  - `strong` 强分支：选项通向不同的路线
  - `value_based` 数值分支：由累积的数值决定走向
- **状态系统**：主数值、多维数值、flags、variables 共同驱动选项的门控（`all / any / not / >= …`）、结局判定和「后果回声」。
- **Auditor**（`pipeline/auditor.py`）检查图完整性、道具追踪、角色在场、命名一致、死结局因果、时间线，以及结构质量：伪选择、漏斗收束、数值系统没被用上、结局缺少条件。
- **Runtime**（`avg_game_toolkit_v1/runtime_container/fixed_avg_runtime/`）是可换皮的通用网页播放器，读取 `runtime_game_package.json`，用 localStorage 保存存档位和结局收集。

## 生成你自己的游戏

```bash
# 离线模式：用内置示例快速验证整条链路，不需要 API
python3 pipeline/pipeline.py --mode offline --output-dir /tmp/offline
python3 avg_engine/build_game.py --story-graph /tmp/offline/story_graph.json \
    --narratives /tmp/offline/narratives.json --output /tmp/offline/game.html

# LLM 模式：需要自备 OpenAI 兼容接口
cp .env.example .env   # 填入自己的 Key，.env 已被 git 忽略
pip install -r requirements.txt
python3 pipeline/pipeline.py --mode llm --seed-file data/seed_001.jsonl --output-dir outputs/my_story
```

图片、视频、音频生成和 toolkit 的多 Agent 流程见 **[MANUAL.md](MANUAL.md)** 与 [`avg_game_toolkit_v1/README.md`](avg_game_toolkit_v1/README.md)。

## 目录结构

| 路径 | 内容 |
|---|---|
| `pipeline/` | Director / Writers / Auditor 与 Story Graph schema |
| `avg_engine/` | 编译器：story graph + narratives → 单文件 HTML（`build_game.py`、`asset_generator.py`、`templates/`） |
| `avg_game_toolkit_v1/` | 三层游戏生产工具包：`tool_core/`（多 Agent 生成链）→ `runtime_container/`（通用 runtime）→ `playable_games/`（打包成品） |
| `demos/` | 可玩 demo 及本地化资产 |
| `outputs/seed00{1,2,3}/` | 样例产物：story graph、正文、world bible、审计报告、可视化 |
| `data/` | 故事种子（`gen_seeds.py` 生成了 100 个多题材 seed） |
| `qa/` | 可离线运行的 QA 测试 |
| `docs/` | 系统设计与 QA 计划 |

## 开发与规范

```bash
pip install -r requirements-dev.txt && pre-commit install
ruff check . && python3 qa/test_pipeline.py
```

目录约定、命名、密钥处理、素材上限和提交规范见 **[CONTRIBUTING.md](CONTRIBUTING.md)**。每个 PR 都会在 CI 中运行 lint、离线流水线、QA、runtime 包校验和 gitleaks 密钥扫描。

## 说明

- 仓库不含任何密钥，所有外部服务都通过环境变量配置（见 `.env.example`）。文档中的 `<PROJECT_ROOT>`、`api.example.com` 等是占位符。
- 诛仙案例是基于原著世界观的非商业同人演示，原作版权归原作者所有。
