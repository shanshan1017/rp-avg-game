# 美术素材清单与生产工作流

本文档用于锁定 `心动失控夜` 当前 runtime 真正会展示的素材范围和生产顺序。确认后，可以把本文档作为 Claude Code / 美术执行 agent 的工作说明，让它只处理会进入游戏链路的素材，避免生成不会被前端读取的闲置资源。

如果后续换新剧本、主角或整集主题，先阅读 `SCALABLE_PRODUCTION_PIPELINE.md`，再用本文档这种格式为新项目重新生成“runtime 资产合同”。不要直接沿用旧资产数量。

## 目标版本

- 类型：第一视角互动视频游戏。
- 运行时：当前为 HTML runtime，后续保留 Godot 迁移。
- 视觉：原创二次元 / 2.5D cinematic illustration，不使用真人、明星脸、现有 IP。
- 画幅：主视频 16:9，当前目标 720p，可升级 1080p。
- 单局时长：常规结局路径约 60-90 秒。
- 节点长度：8-15 秒。
- 主角规则：第一视角男主不出镜，不出现脸、身体、背影、倒影、影子、手部特写或社交头像。

## 当前节点规模

当前故事图共 16 个节点：

- 普通视频节点：7 个。
- 中途失败 / 失败结局：5 个。
- 正常结局 / 真结局：4 个。

角色：

- 林小满：邻家妹妹。
- 沈以霜：高冷上司姐姐。
- 祁夏：网吧偶遇少女。
- 白鹿：反差摄影少女 / 观察者。

核心地点：

- 写字楼电梯厅。
- 写字楼电梯。
- 小区门口。
- 网吧后巷。
- 夜晚十字路口。
- 便利店外。
- 楼梯间与街角快切。
- 失败/结局专用场景：电梯、手机弹窗、小包间、屋顶、小区长椅、会议室、网吧双人机位、街边桌。

## 当前 Runtime 使用核查

已核对 `index.html`、`app.js`、`styles.css`、`build_game_data.py` 和 `game_data.js`。当前游戏实际展示/读取的素材只有以下三类：

| 素材类型 | 当前是否展示 | 使用位置 | 生成要求 |
| --- | --- | --- | --- |
| 角色主参考图 | 是 | 标题页路线卡、MEMORY 面板 | 必须有 4 张 |
| 节点 poster | 是 | `<video poster>`、标题页初始背景、视频加载前占位 | 必须有 16 张 |
| 节点视频 | 是 | 主播放层 `<video src>` | 必须有 16 段 |
| 节点尾帧 | 否 | 当前前端未读取；只用于后续连续镜头和重跑衔接 | 本轮不主动生成，视频接口返回则本地保存 |
| logo / 标题字图片 | 否 | 当前标题是 HTML 文本 | 不生成 |
| 路线卡专用图 | 否 | 当前复用角色主参考图 | 不生成 |
| 角色头像裁切 | 否 | 当前 MEMORY 也复用角色主参考图 | 不生成 |
| 结局/失败徽章 | 否 | 当前结局/失败层是 CSS + 文字 | 不生成 |
| HUD/按钮纹理 | 否 | 当前全部 CSS 绘制 | 不生成 |
| 独立 UI 音效 / BGM | 否 | 当前只播放视频自带音频 | 不生成 |
| favicon / app icon | 否 | 当前游戏逻辑不用 | 不生成 |

结论：本轮 Claude Code 只需要围绕 `characters/`、`posters/`、`videos/` 三条链路做审计和必要重跑。任何未接入 runtime 的 UI 素材都先不生成，除非我们先改前端接入它。

当前资源引用检查结果：

- `game_data.js` 引用素材总数：36。
- 角色图：4 / 4 存在。
- 节点 poster：16 / 16 存在。
- 节点视频：16 / 16 存在。
- 缺失素材：0。

## 风格统一规范

所有被游戏展示的图片和视频必须保持同一套视觉语言：

- 原创二次元 / 2.5D cinematic illustration。
- 都市夜景恋爱轻喜剧，整体为夜色、霓虹、暖光、冷白办公灯混合。
- 16:9 横屏构图，主视频与 poster 均保持同一画幅。
- 第一视角镜头，男主不出镜，不出现男主脸、身体、背影、倒影、影子、手部特写或社交头像。
- 人物脸部不能被 HUD 或选择框遮挡；角色关键表情尽量位于画面中上部安全区。
- 不生成写实真人，不生成明星脸，不借用现有动漫/游戏 IP。
- 不把 UI、字幕、按钮、logo、水印生成进画面。

重跑图片或视频时，prompt 必须带统一风格前缀：

```text
Original anime cinematic 2.5D illustration, first-person player POV, urban Friday night romantic comedy thriller, polished animated film lighting, consistent character design, 16:9 composition, no male protagonist visible, no UI, no subtitles, no watermark.
```

多角色节点必须额外带角色一致性约束：

```text
Use the approved character references for Lin Xiaoman, Shen Yishuang, Qi Xia, and Bai Lu. Keep hairstyle, outfit color family, facial features, age impression, and silhouette consistent with the reference sheets.
```

## 素材总表

### A. 角色素材

| 素材 | 数量 | 必需 | 当前状态 | 输出路径 |
| --- | ---: | --- | --- | --- |
| 角色主参考图 | 4 | 是 | 已有，游戏中展示 | `video_engine/public/assets/characters/<character_id>.png` |
| 角色半身立绘裁切 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 角色表情表 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 角色服装/场景变体 | 0 | 否 | 当前 runtime 未接入，不生成；重跑视频时再按节点补 | - |
| 角色小头像 / MEMORY 缩略图 | 0 | 否 | 当前复用主参考图，不生成 | - |

如果后续某个视频节点因角色一致性必须重跑，再按节点补局部参考图。不要在没有重跑需求时批量生成角色变体。

潜在角色变体，仅在重跑时使用：

- 林小满：小区门口夜宵、便利店街边桌、长椅结局。
- 沈以霜：电梯、会议室、便利店街边桌。
- 祁夏：网吧后巷、网吧双人机位、便利店街边桌。
- 白鹿：楼梯间观察者、屋顶剪辑者、真结局合照观察者。

### B. 场景与关键帧素材

| 素材 | 数量 | 必需 | 当前状态 | 输出路径 |
| --- | ---: | --- | --- | --- |
| 节点首帧 / poster | 16 | 是 | 已有，游戏中展示 | `video_engine/public/assets/posters/<node_id>.png` |
| 节点尾帧 | 0 | 否 | 当前游戏不展示；视频接口返回则保存，不主动生成 | `video_engine/public/assets/posters/<node_id>_last_frame.png` |
| 地点概念图 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 开场标题背景图 | 0 | 否 | 当前复用 `node_01_office_exit.png`，不生成专用图 | - |
| 结局卡背景图 | 0 | 否 | 当前复用结局视频停帧和 poster，不生成 | - |
| 失败卡背景图 | 0 | 否 | 当前复用失败视频停帧和 poster，不生成 | - |

说明：

- 当前版本直接用 16 张节点 poster。
- 不单独生成标题 key art、结局卡和失败卡，避免产生不被前端读取的闲置素材。
- 地点概念图只在视频重跑质量不稳时补，用于统一风格和镜头。

### C. 视频素材

| 素材 | 数量 | 必需 | 当前状态 | 输出路径 |
| --- | ---: | --- | --- | --- |
| 节点视频 | 16 | 是 | 已有，游戏中展示 | `video_engine/public/assets/videos/<node_id>.mp4` |
| 备用重跑视频 | 只针对 QA 判定问题节点 | 是，按需 | 待定 | `outputs/heart_rush_night_v0/video_rerolls/<node_id>/` |
| 压缩版视频 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| Godot 版视频拷贝 | 0 | 否 | Godot 项目建立后再复制 | - |

视频节点清单：

| 节点 ID | 类型 | 标题 | 地点 | 角色 | Runtime 必须素材 |
| --- | --- | --- | --- | --- | --- |
| `node_01_office_exit` | video | 周五下班口 | 写字楼电梯厅 | 无 | poster、video |
| `node_02_boss_elevator` | video | 电梯门被按住 | 写字楼电梯 | 沈以霜 | 角色参考、poster、video |
| `node_02_neighbor_gate` | video | 小区门口的夜宵 | 小区门口 | 林小满 | 角色参考、poster、video |
| `node_02_cafe_alley` | video | 霓虹巷口的会员卡 | 网吧后巷 | 祁夏 | 角色参考、poster、video |
| `node_03_crosswalk` | video | 红灯倒计时 | 夜晚十字路口 | 无 | poster、video |
| `node_04_truth_groupchat` | video | 群聊发送成功 | 便利店外 | 小满、以霜、祁夏 | 多角色一致性、poster、video |
| `node_04_keep_juggling` | video | 继续周旋 | 楼梯间与街角快切 | 白鹿 | 白鹿参考、poster、video |
| `fail_lie_receipt` | failure | 收据上的时间 | 电梯 | 沈以霜 | poster、video |
| `fail_phone_screen` | failure | 亮起的弹窗 | 小区门口 | 林小满 | poster、video |
| `fail_wrong_escape` | failure | 错误包间 | 网吧包间 | 祁夏 | poster、video |
| `fail_panic_freeze` | failure | 三方同时抵达 | 十字路口 | 三人 | poster、video |
| `fail_rooftop_showdown` | failure | 屋顶时间线 | 屋顶 | 四人 | 多角色一致性、poster、video |
| `end_neighbor_warmth` | ending | 热汤和长椅 | 小区长椅 | 林小满 | poster、video |
| `end_boss_midnight_plan` | ending | 午夜方案 | 会议室 | 沈以霜 | poster、video |
| `end_cafe_duo` | ending | 最后一局 | 网吧双人机位 | 祁夏 | poster、video |
| `end_true_open_calendar` | ending | 共享日历 | 便利店外街边桌 | 四人 | 多角色一致性、poster、video |

### D. UI 与前端美术素材

| 素材 | 数量 | 必需 | 当前状态 | 输出路径 |
| --- | ---: | --- | --- | --- |
| 游戏标题字 / logo | 0 | 否 | 当前 HTML 文本展示，不生成 | - |
| 标题背景 key art | 0 | 否 | 当前复用开场 poster，不生成 | - |
| 路线选择卡图 | 0 | 否 | 当前复用角色主参考图，不生成 | - |
| 角色头像 | 0 | 否 | 当前复用角色主参考图，不生成 | - |
| HUD 装饰纹理 | 0 | 否 | 当前 CSS 绘制，不生成 | - |
| 选择按钮纹理 | 0 | 否 | 当前 CSS 绘制，不生成 | - |
| 结局徽章 | 0 | 否 | 当前 CSS + 文字，不生成 | - |
| 失败徽章 | 0 | 否 | 当前 CSS + 文字，不生成 | - |
| 加载图 / loading poster | 0 | 否 | 当前视频 poster 承担加载占位，不生成 | - |
| favicon / app icon | 0 | 否 | 当前不影响游戏链路，不生成 | - |

UI 风格方向保持在 CSS 层：

- 黑金、象牙白、玻璃感、细线装饰。
- 全屏视频为核心，UI 不能挡住人物脸部。
- 选择按钮用斜角白金框，数量支持 2-4 个。
- HUD 是氛围和状态提示，不做过重系统面板。

### E. 音频素材

当前视频生成时包含同步音频，HTML runtime 未接入独立音频系统。本轮不生成独立音频。

| 素材 | 数量 | 必需 | 当前状态 | 输出路径 |
| --- | ---: | --- | --- | --- |
| UI 点击音 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 选择确认音 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 解锁提示音 | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 失败 stinger | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 结局 stinger | 0 | 否 | 当前 runtime 未接入，不生成 | - |
| 标题页 BGM loop | 0 | 否 | 当前 runtime 未接入，不生成 | - |

注意：如果后续接入前端音频系统，再单独开音频资产任务。现在不要让美术执行 agent 生成音频。

### F. 数据与质检产物

| 产物 | 作用 | 当前状态 |
| --- | --- | --- |
| `character_prompts.json` | 角色图生成输入 | 已有 |
| `video_prompts.json` | 首帧和视频生成输入 | 已有 |
| `character_assets.json` | 角色图生成记录 | 已有 |
| `first_frame_assets.json` | 首帧图生成记录 | 已有 |
| `video_task_payloads.json` | 视频请求体记录 | 已有 |
| `video_tasks.json` | 视频任务 ID 和提交状态 | 已有 |
| `video_results.json` | 视频轮询与下载结果 | 已有 |
| `video_manifest.json` | 前端本地视频资源索引 | 已有 |
| `game_data.js` | 前端运行数据 | 已有 |
| 角色 contact sheet | 角色总览质检 | 已有 |
| poster contact sheet | 首帧总览质检 | 已有 |
| video contact sheet / still sheet | 视频质检 | 待补 |
| QA report | 记录重跑建议 | 待补 |

## 命名规范

### 角色 ID

```text
lin_xiaoman
shen_yishuang
qi_xia
bai_lu
```

### 节点素材

```text
assets/posters/<node_id>.png
assets/posters/<node_id>_last_frame.png
assets/videos/<node_id>.mp4
```

### UI 素材

```text
当前 runtime 不读取 UI 图片素材，本轮禁止新建 assets/ui/*。
如后续接入 UI 图片，再补命名规范。
```

### 重跑素材

```text
outputs/heart_rush_night_v0/rerolls/<node_id>/<attempt_id>/
  first_frame.png
  video.mp4
  last_frame.png
  prompt.json
  notes.md
```

## 推荐生产工作流

### Phase 1：资产审计

目标：先看已有素材，不立刻重跑。

产出：

- `outputs/heart_rush_night_v0/ART_QA_REPORT.md`
- 16 个视频节点的评级：保留 / 可用但待修 / 必须重跑。
- 问题分类：角色不一致、第一视角破坏、镜头跳变、UI 字幕误生成、人物遮挡、音频不合适、场景错位。

操作：

1. 抽取每段视频 3-5 张 still。
2. 生成 video contact sheet。
3. 对照角色参考图检查一致性。
4. 对照主角规则检查是否出现男主身体、手、倒影、影子。
5. 标记需要重跑的节点。

### Phase 2：补齐 UI 美术

目标：当前先不补 UI 美术，因为 runtime 没有读取专用 UI 图片。若要补，必须先改前端接入路径。

优先级：

1. 本轮跳过。
2. 如后续要做标题 key art、路线卡、徽章或 favicon，先在 `app.js` / `game_data.js` 接入，再生成素材。
3. 未接入前，不生成这些资产。

原则：

- UI 图不要内嵌大段文字，文字仍由前端渲染。
- 避免把按钮、字幕、logo 直接生进背景图。
- 所有 UI 图都要有透明背景版本或安全裁切版本。

### Phase 3：角色一致性增强

目标：只在 QA 判定某个视频要重跑时，为该节点补角色参考。不要提前批量生成不会被使用的变体。

产出：

- 问题节点所需角色的局部参考图。
- 问题节点对应的重跑首帧。
- 必要时补 1 张场景灯光参考。

执行顺序：

1. 先看 QA report 是否判定该节点必须重跑。
2. 从现有角色图和 poster 中挑选参考。
3. 只为该节点补生成所需参考，不扩大到全量角色包。

### Phase 4：问题视频重跑

目标：只重跑 QA 标记为“必须重跑”的节点。

输入：

- 原 `video_prompts.json`。
- 对应角色主参考。
- 对应节点首帧或重新生成的首帧。
- QA report 中的问题说明。

重跑规则：

- 每个问题节点先跑 1 条低数量尝试。
- 通过后替换 `assets/videos/<node_id>.mp4`。
- 不通过则进入 `rerolls/<node_id>/<attempt_id>/` 保留候选，不覆盖正式文件。

验收标准：

- 第一视角成立。
- 女生角色不跑偏。
- 节点目标清楚。
- 结尾能自然接出分支。
- 无水印、无嵌字、无无关 UI。
- 视频时长符合 8-15 秒。

### Phase 5：压缩与运行时接入

目标：当前只保证原始本地 mp4 链路可播放。压缩版和 Godot 拷贝暂不生成。

产出：

- 更新 `video_manifest.json`。
- 更新 `game_data.js`。
- 运行桌面和移动端 QA。

建议：

- MVP 保留原始 mp4。
- 只有当加载性能成为问题，才生成 optimized mp4。
- Godot 项目建立后，再复制或转码视频。

## Claude Code 执行边界

确认本文档后，Claude Code / 美术执行 agent 可以负责：

- 生成素材审计 contact sheet。
- 写 `ART_QA_REPORT.md`。
- 检查当前 4 张角色参考、16 张 poster、16 段视频是否都在 runtime 中引用。
- 只按 QA report 重跑指定图片或视频任务。
- 更新 `video_manifest.json` 和 `game_data.js`。
- 做浏览器截图 QA。

暂不让执行 agent 自行改动：

- 主线剧情结构。
- 角色设定和年龄。
- 分支条件与结局逻辑。
- 安全规则。
- API 密钥或私有配置。
- 大规模重跑全部视频。
- 当前 runtime 未接入的 UI 图、徽章、音频、logo、favicon。

## 第一轮建议任务包

建议 Claude Code 第一轮只做“美术审计 + 链路核查”，不生成未接入 UI 的素材，不重跑视频：

1. 读取现有角色图、poster、视频。
2. 为 16 个视频各抽 4 帧，生成 video contact sheet。
3. 写 `ART_QA_REPORT.md`，标出每个节点是否需要重跑。
4. 跑一次资源引用检查：`game_data.js` 中引用的角色图、poster、video 都必须存在。
5. 检查风格一致性：角色、灯光、画幅、第一视角、无嵌字、无男主出镜。
6. 只输出问题清单和重跑建议，不生成 logo、头像、徽章、音效、favicon。
7. 如发现某个已展示素材缺失或损坏，只修该素材和 manifest，不改剧情逻辑。

第一轮完成后，我们再决定哪些视频值得花钱重跑。
