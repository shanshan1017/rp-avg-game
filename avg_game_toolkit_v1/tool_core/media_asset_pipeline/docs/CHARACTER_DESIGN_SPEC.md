# Character Design Spec

角色设计是通用互动媒体素材流水线的一级产物，位置在 `Story Bible` 之后、`Script Table` 和 `Asset Plan` 之前。

## 为什么需要

`Story Bible` 里的角色信息只负责剧情规划，通常只有定位、年龄、性格和视觉锚点。它不足以稳定支持：

- 角色参考图生成。
- poster 图生图。
- 视频角色一致性。
- 多角色同屏时防止融合、换发型、换服装。
- UI 角色档案。
- 台词风格和分支选择含义。

所以每个项目都应该产出：

- 人类可读：`character_design.md`
- 机器可读：`character_design.json`
- Schema：`../../schemas/media_character_design.schema.json`

## 推荐内容

每个角色至少写清：

- 基础信息：姓名、年龄、身份、出场范围、runtime 字段。
- 叙事功能：她想要什么、外部目标、内在矛盾、角色弧光、失败压力。
- 关系设计：和男主的关系、和其他女主的关系、玩家选择她意味着什么。
- 视觉设计：轮廓、脸和发型、眼睛、服装、色板、标志道具、表情和姿态。
- 场景规则：哪些场景可以出现、多人同屏时如何避免身份混淆。
- 声音和台词：说话节奏、用词习惯、样例台词。
- 生成规则：prompt anchor、must preserve、must avoid、reference policy。

## Gate 影响

新增 `Character Design Gate`：

1. Story Bible 完成。
2. Character Design 完成并通过 Checker。
3. 才能生成角色参考图。
4. 角色参考图通过后，才能进入 poster 和 video 生成。

## 关键规则

- 校园题材必须明确角色为成年人。
- 第一视角男主不需要角色视觉设定，除非 runtime 改成第三视角。
- 不要用真实人物、明星、公共人物或现有 IP 作为角色参考。
- 多角色节点不能使用 cast lineup 作为 scene reference。
- 角色设定里的视觉锚点必须能被 prompt 复用，不能只写抽象性格词。
