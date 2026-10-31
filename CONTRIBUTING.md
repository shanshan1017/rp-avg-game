# 贡献与仓库规范

本文件是本仓库的**工作规范**：目录放什么、怎么命名、提交前检查什么、密钥和素材怎么处理。提 PR 前请通读一遍。

## 1. 目录约定

| 目录 | 放什么 | 不放什么 |
|---|---|---|
| `pipeline/` | Story Graph 生成核心（Director / Writers / Auditor / schema） | 一次性实验脚本 |
| `avg_engine/` | story graph → 单文件 HTML 游戏的编译器与模板 | 生成好的游戏 |
| `avg_game_toolkit_v1/` | 多 Agent 媒体生产工具链、通用 runtime、打包成品 | 历史备份素材、未入选的候选素材 |
| `demos/` | 对外展示的可玩游戏 HTML 及其本地化资产 | 调试版本 |
| `outputs/seedNNN/` | 精选的样例产物（只保留 `seed001`–`seed003`） | 本地跑出来的其它结果（已被 `.gitignore` 忽略） |
| `data/` | 故事种子 | 带真实路径/凭证的任务配置 |
| `docs/` | 设计文档、QA 计划 | 会议记录、个人笔记 |
| `qa/` | 可离线运行的测试 | 依赖内部集群的用例 |

新增一类东西时，先想清楚它属于哪个目录；**不要在仓库根目录堆文件**，也不要复制整个目录做“备份”——用分支和 tag。

## 2. 命名

- Python：`snake_case.py`，函数/变量 `snake_case`，类 `PascalCase`。
- 种子与产物：`seed_NNN.jsonl` ↔ `outputs/seedNNN/`；demo：`demos/game_<theme>_<NNN>.html`。
- 游戏包：`avg_game_toolkit_v1/playable_games/<game_id>_v<N>/`，`game_id` 全小写下划线。
- 文档：大写下划线（如 `PIPELINE_USAGE_GUIDE.md`）或全小写下划线，同目录保持一致。

## 3. 密钥、路径与隐私（硬性要求）

- **任何密钥只走环境变量。** 复制 `.env.example` 为 `.env`（已被忽略）；代码里只允许 `os.environ[...]`，默认值只能是 `https://api.example.com/...` 这类占位符。
- 不提交内网域名/IP、个人或集群路径（用 `<PROJECT_ROOT>`、`<STORAGE_VOLUME>` 占位）、同事姓名、内部任务日志。
- 提交前会由 `gitleaks` 在 pre-commit 和 CI 中扫描；误报请在 PR 里说明，不要关掉检查。
- 一旦误提交密钥：**立即作废该 Key**，再清理文件。仅删除文件不够，历史中仍可找回。

## 4. 素材与大文件

- 单文件上限 20 MB（`check-added-large-files`）。视频先压缩；超过上限的素材放外部存储，在 manifest 里引用。
- 只提交最终入选素材；生成过程中的候选、`*_backup`、`.bak` 不入库。
- 新增第三方 IP / 人物 / 字体时，在 PR 描述中写明来源与授权情况。

## 5. 本地开发

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install            # 每次 commit 自动跑 ruff / gitleaks / JSON 校验 / 大文件检查
```

提交前至少跑一遍（与 CI 相同）：

```bash
ruff check .
python pipeline/pipeline.py --mode offline --output-dir /tmp/offline
python qa/test_pipeline.py --output-dir /tmp/offline
python avg_game_toolkit_v1/tool_core/bin/validate_runtime_package.py \
  avg_game_toolkit_v1/playable_games/zhuxian_qimai_huiwu_v1/runtime/runtime_game_package.json --assets-complete
```

改了 Story Graph schema、Auditor 规则或 runtime 时，额外用浏览器把 `demos/` 和诛仙 runtime 各玩通一条路线。

## 6. 分支、提交与 PR

- 不直接推 `main`；分支命名 `feat/…`、`fix/…`、`docs/…`、`chore/…`。
- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat(pipeline): add value-gated merge point`、`fix(runtime): …`、`docs: …`。一个提交只做一件事。
- PR 描述写清：改了什么、为什么、怎么验证的；涉及玩法/画面的附截图或录屏。
- CI 全绿后再合并。
