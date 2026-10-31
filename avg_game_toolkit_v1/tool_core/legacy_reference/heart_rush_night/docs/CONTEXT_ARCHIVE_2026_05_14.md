# 项目上下文归档：2026-05-14

## 当前项目

工作目录：

- `<WORKSPACE_ROOT>`

核心项目：

- `interactive_video_game`

当前可运行原型是一个 HTML 第一视角互动视频游戏，主题为男生视角被几个女生追逐和试探。男主是第一视角镜头，不应出现在画面中。

## 已有游戏

游戏名：

- `心动失控夜`

运行时：

- `interactive_video_game/video_engine/public/index.html`
- `interactive_video_game/video_engine/public/app.js`
- `interactive_video_game/video_engine/public/styles.css`
- `interactive_video_game/video_engine/public/game_data.js`

当前剧情资产合同：

- 4 张角色参考图
- 16 张节点 poster
- 16 段节点视频
- 尾帧只作为生产参考，不在当前 UI 展示

## 角色设定

第一版核心角色：

- 林小满：邻家妹妹
- 沈以霜：高冷上司姐姐
- 祁夏：网吧偶遇少女
- 白鹿：神秘自由系角色

用户要求：

- 不做真人风格，避免版权和肖像风险。
- 使用日本二次元插画 / 二游角色设计方向。
- 角色设计要有亮点，不要太普通。
- 保持整体图像和视频风格统一。

## 关键经验

v2 问题：

- 四个角色由文生图独立生成，风格漂移明显。
- poster 没有正确使用单角色参考，导致角色一致性不足。

v3 问题：

- 将多人 cast lineup 当成 poster 参考图，模型把多人阵容误当成画面内容，导致很多 poster 出现所有人。

v4 改进：

- 用户提供了 4 张喜欢的画风参考图。
- 生成了 text-only 和 with-style-refs 两套图片。
- poster 生成不再使用 cast lineup。
- 有角色节点只使用该节点角色参考；无角色节点尽量 text-only 或强约束 no people。

核心规则：

- 不要把多角色 lineup 作为单节点 poster 的参考。
- 参考图不是纯风格，会把主体也带进输出。
- 先生成并审核角色，再生成 poster，再生成视频。
- 每个素材必须能追溯到 runtime 字段。

## 已有重要文档

- `interactive_video_game/docs/SCALABLE_PRODUCTION_PIPELINE.md`
- `interactive_video_game/docs/ASSET_SCOPE_AND_WORKFLOW.md`
- `interactive_video_game/docs/ASSET_REQUEST_AND_LOCAL_SAVE.md`
- `interactive_video_game/docs/PRODUCTION_RULES.md`
- `interactive_video_game/docs/PROMPT_PACK.md`
- `interactive_video_game/docs/STORYLINE.md`
- `interactive_video_game/data/style_bible/visual_style.md`
- `interactive_video_game/data/style_bible/characters.md`

## 已有生成脚本

- `interactive_video_game/pipeline/generate_assets.py`

现状：

- 支持图像生成和视频任务生成/下载相关逻辑。
- API key 通过环境变量读取。
- 输出 manifest 尽量使用本地路径。

后续方向：

- 先沉淀通用 skill、能力矩阵和 schema。
- 通用生产默认采用三 agent：Codex 作为 Planning Agent，两个 Claude Code 分别作为 Executive Agent 和 Checker Agent。
- Checker 通过前不得进入下一 gate；paid generation 前必须有 Planning 计划和用户确认。
- 再把 Ark submit/poll/download 抽成通用 adapter。
- 最后把资产 manifest 和 HTML/Godot runtime 打包流程接起来。
