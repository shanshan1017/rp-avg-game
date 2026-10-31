# AVG 互动小说 RP 框架 — QA 质量保证文档

最后更新：2026-04-20 v1
负责人：—

---

## 一、系统概述

### 1.1 目标

将已有的 Story Graph（结构化故事树）+ Narratives（叙事文本）转化为一个可玩的 AVG（Adventure Visual Game）视觉小说界面：

- 每个故事节点 → 一个可视化场景界面（背景图 + 角色立绘 + 叙事文本）
- 每个选择点 → 交互式按钮，玩家点击后推进剧情
- 每个场景 → AI 生成对应的背景图和角色图
- 关键剧情 → 生成过场视频/动画
- 数值系统 → 隐藏属性实时追踪，影响选项解锁和结局分流

### 1.2 架构

```
┌──────────────────────────────────────────────────────┐
│                    数据层                              │
│  story_graph.json  +  narratives.json  +  assets/    │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│                  AVG 引擎层                            │
│  GameEngine  →  SceneManager  →  ValueTracker         │
│  SaveManager →  AssetLoader   →  TransitionController │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│                 资产生成层                              │
│  ImageGenerator (背景/立绘)  →  VideoGenerator (过场) │
│  AudioGenerator (BGM/SE)                              │
└──────────────┬───────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────┐
│                  表现层 (Web UI)                       │
│  HTML5 Canvas / DOM                                   │
│  ├── 背景图层 (全屏背景)                                │
│  ├── 角色图层 (立绘，最多 3 人同屏)                      │
│  ├── 文本图层 (对话框 + 叙述框)                          │
│  ├── 选择图层 (选项按钮 + 锁定提示)                      │
│  ├── UI 图层 (数值面板/菜单/存档)                        │
│  └── 过场图层 (视频/动画播放)                            │
└──────────────────────────────────────────────────────┘
```

### 1.3 技术栈

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| 游戏引擎 | 纯 HTML5 + CSS + Vanilla JS | 零依赖，单文件部署，参考 Claude-Code-Game-Studios 模式 |
| 布局 | CSS Grid + Flexbox | 响应式适配 |
| 动画 | CSS Transitions + requestAnimationFrame | 文字逐字显示、场景切换 |
| 图片生成 | LLM API (DALL-E / MiniMax 图片模型) | 根据 scene_description 生成 |
| 视频生成 | MiniMax 视频模型 / Runway | 关键剧情过场 |
| 音频 | Web Audio API | BGM 循环 + SE 触发 |
| 存档 | localStorage + JSON export | 客户端持久化 |

### 1.4 代码位置

| 模块 | 路径 |
|------|------|
| AVG 引擎核心 | `avg_engine/` |
| 场景生成器 | `avg_engine/scene_builder.py` |
| 资产生成 Pipeline | `avg_engine/asset_generator.py` |
| HTML 游戏模板 | `avg_engine/templates/game.html` |
| 资产输出 | `avg_engine/assets/` |
| 构建脚本 | `avg_engine/build.py` |
| QA 测试 | `avg_engine/tests/` |

### 1.5 输入数据

| 文件 | 来源 | 用途 |
|------|------|------|
| `story_graph.json` | Director Agent 输出 | 故事结构、节点、选项、数值系统 |
| `narratives.json` | Branch Writer 输出 | 各节点叙事文本、死结局文本 |
| `world_bible.txt` | Director Agent 输出 | 世界观摘要，用于图片 prompt |

---

## 二、QA 检查项

### 2.1 数据完整性检查

#### 2.1.1 Story Graph 与 Narratives 对齐

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 节点覆盖率 | ERROR (< 70%) / WARNING (< 90%) | narratives.json 必须覆盖 story_graph 中所有可达节点 |
| 叙事字段存在 | ERROR | 每个 narrative 条目必须有 `narrative_text` 或 `variant_text` 或 `death_text` |
| 叙事非空 | ERROR | 叙事文本长度 >= 50 字符（死结局 >= 20） |
| 选项文本匹配 | WARNING | story_graph 中 choice 的 `text` 字段与 narratives 中 `choices_text` 一致 |
| 节点 ID 一致 | ERROR | narratives 中每个 `node_id` 必须在 story_graph.nodes 中存在 |
| 角色名一致 | WARNING | 叙事文本中出现的角色名必须与 characters 列表中的 `name` 匹配 |

#### 2.1.2 资产清单完整性

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 背景图覆盖 | ERROR (< 50%) / WARNING (< 80%) | 每个场景节点有对应背景图文件 |
| 角色立绘覆盖 | WARNING | 每个 character 至少 1 张立绘（含表情变体） |
| 过场视频 | WARNING | ending 节点和 dead_end 节点有对应视频/动画 |
| 资产文件格式 | ERROR | 图片: PNG/WebP, 视频: MP4/WebM, 音频: MP3/OGG |
| 资产文件大小 | WARNING | 单张图片 <= 2MB, 单个视频 <= 20MB |
| 资产命名规范 | WARNING | `bg_{node_id}.png`, `char_{char_id}_{expression}.png`, `video_{node_id}.mp4` |

### 2.2 场景渲染检查

#### 2.2.1 文本显示

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 文本框不溢出 | ERROR | 叙事文本在对话框内完整显示，支持滚动 |
| 对话/叙述区分 | WARNING | 引号内对话文本与叙述文本使用不同样式 |
| 角色名显示 | WARNING | 对话时显示说话角色名 |
| 逐字显示 | WARNING | 文字以打字机效果逐字出现，可点击跳过 |
| 多段落分页 | WARNING | 长文本自动分页，点击翻页 |
| 字体渲染 | WARNING | 中英文字体正确显示，无乱码 |
| 文本标记解析 | WARNING | `*动作描述*` 以斜体/不同颜色显示 |

#### 2.2.2 场景画面

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 背景图全屏 | ERROR | 背景图铺满游戏区域，无拉伸变形 |
| 角色立绘位置 | WARNING | 立绘居中或按对话位置左右排列 |
| 角色切换动画 | WARNING | 角色进场/退场有淡入淡出 |
| 场景切换过渡 | WARNING | 节点间切换有过渡效果（淡入淡出/溶解/黑屏） |
| 死结局特效 | WARNING | 死结局有红屏闪烁或特殊视觉效果 |
| 结局画面 | WARNING | 正常结局有专属 CG 或文字画面 |

#### 2.2.3 选择交互

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 选项按钮可点击 | ERROR | 每个解锁选项可以点击并正确跳转 |
| 选项数量正确 | ERROR | 显示的选项数 == story_graph 中该节点的 choices 数 |
| 锁定选项显示 | ERROR | gate_condition 不满足的选项显示为灰色 + 锁定提示 |
| 锁定提示文本 | WARNING | 显示 `locked_hint` 文本说明解锁条件 |
| 选项 hover 效果 | WARNING | 鼠标悬停有视觉反馈 |
| 死结局警告 | WARNING | `is_dead_end: true` 的选项有视觉区分（红色边框/骷髅图标） |
| 选项点击后禁用 | ERROR | 选择后所有选项不可再次点击 |
| value_effects 生效 | ERROR | 选择后数值正确更新 |

### 2.3 游戏逻辑检查

#### 2.3.1 数值系统

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 初始值正确 | ERROR | 游戏开始时所有属性 == value_system.attributes[x].initial |
| 数值累加正确 | ERROR | 每次选择后 attribute += delta，不超出 min/max 范围 |
| 数值上下限 | ERROR | clamp(min, value, max) 始终成立 |
| gate_condition 判定 | ERROR | `{"clues": ">=5"}` 等条件正确解析和判定 |
| auto_route 路由 | ERROR | 有 auto_route 的节点根据数值/分支条件正确路由 |
| 数值面板显示 | WARNING | （可选）显示当前数值状态的调试面板 |

#### 2.3.2 流程控制

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 入口节点正确 | ERROR | 游戏从 `entry_node_id` 指定的节点开始 |
| 叙事节点自动推进 | ERROR | 非 choice 类型节点：文本读完后自动/点击进入 next_nodes[0] |
| choice 节点等待 | ERROR | choice 类型节点必须等待玩家选择 |
| 死结局终止 | ERROR | dead_end 节点显示死亡文本后提供「重新开始」或「读档」 |
| 正常结局终止 | ERROR | ending 节点显示结局文本后提供「回到标题」或「继续探索」 |
| 分支合流 | ERROR | merge_point 节点正确从多个 prev_nodes 接收 |
| 不可达节点 | WARNING | BFS 遍历从 entry 出发 >= 90% 节点可达 |
| 无限循环 | ERROR | 不存在节点循环（A→B→C→A） |

#### 2.3.3 存档系统

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 自动存档 | WARNING | 每个 choice 节点前自动存档 |
| 手动存档 | WARNING | 玩家可在任意时刻存档（最多 10 个槽位） |
| 存档内容完整 | ERROR | 存档包含：current_node_id + values + visited_nodes + branch_history |
| 读档恢复 | ERROR | 读档后游戏状态完全还原 |
| 存档格式 | WARNING | JSON 格式，含 timestamp + story_id |
| 跨浏览器 | WARNING | localStorage 存档在同浏览器可用 |

### 2.4 资产生成检查

#### 2.4.1 背景图生成

| 检查项 | 级别 | 标准 |
|--------|------|------|
| Prompt 来源 | ERROR | 使用 node.scene_description + world_setting 组合生成 prompt |
| 风格一致性 | WARNING | 同一故事内所有背景图风格统一（维多利亚/现代/奇幻等） |
| 分辨率 | ERROR | 输出 >= 1920x1080 |
| 宽高比 | ERROR | 16:9 横屏 |
| 时间一致性 | WARNING | 同一 act 内时间段一致（白天/夜晚/黄昏） |
| 场景连续性 | WARNING | 同一地点的背景图在不同节点间视觉一致 |
| 无文字 | WARNING | 生成图片中不包含文字或文字痕迹 |
| 无 watermark | ERROR | 生成图片无水印 |

生成 Prompt 模板：
```
场景：{node.scene_description}
时代：{story_graph.time_period}
地点：{story_graph.location}
氛围：{node.emotional_tone}
风格：维多利亚时代油画风格，暖色调，{sp_obfuscation.environment_depth} 环境细节
宽高比：16:9
```

#### 2.4.2 角色立绘生成

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 角色外貌匹配 | ERROR | 立绘与 character.description 一致 |
| 表情变体 | WARNING | 每角色至少 3 种表情：neutral / happy / angry |
| 透明背景 | ERROR | 立绘为 PNG 透明背景 |
| 尺寸统一 | WARNING | 所有立绘等高（约 canvas 高度的 80%） |
| 风格统一 | WARNING | 与背景图同一美术风格 |
| 角色可识别 | ERROR | 不同角色在视觉上可明确区分 |

表情映射规则：
```
emotional_tone 包含「紧张/恐惧/惊慌」 → scared 表情
emotional_tone 包含「愤怒/对抗」 → angry 表情
emotional_tone 包含「温暖/感动/信任」 → warm 表情
emotional_tone 包含「悲伤/遗憾」 → sad 表情
默认 → neutral 表情
```

#### 2.4.3 过场视频生成

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 触发节点 | WARNING | 仅为 ending / dead_end / 关键 branch_point 生成视频 |
| 时长 | WARNING | 5-15 秒 |
| 分辨率 | WARNING | >= 1280x720 |
| 内容匹配 | WARNING | 视频内容与该节点叙事文本主题一致 |
| 加载策略 | ERROR | 预加载或流式加载，不阻塞游戏 |

视频生成优先级：
```
P0: ending 节点（4 个结局各一段）
P1: dead_end 节点（3 个死结局各一段）
P2: 入口节点 node_01（开场动画）
P3: 关键 branch_point（如 node_06 信任/怀疑大分支）
```

#### 2.4.4 音频资产

| 检查项 | 级别 | 标准 |
|--------|------|------|
| BGM 覆盖 | WARNING | 每个 act 至少 1 首 BGM |
| BGM 循环 | WARNING | BGM 无缝循环 |
| SE 触发 | WARNING | 选择点击音效、死结局音效、结局音效 |
| 音量控制 | WARNING | 玩家可调节 BGM/SE 音量 |

### 2.5 UI/UX 检查

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 标题画面 | WARNING | 游戏启动显示标题、「开始游戏」「继续游戏」「设置」 |
| 菜单系统 | WARNING | ESC 或右键打开菜单（存档/读档/设置/返回标题） |
| 回看功能 | WARNING | 可回看已读文本历史 |
| 快进功能 | WARNING | 已读文本可快进跳过 |
| 自动播放 | WARNING | auto 模式自动翻页 |
| 响应式布局 | WARNING | 支持 16:9 和 4:3 窗口 |
| 章节标题 | WARNING | act 切换时显示章节标题卡 |
| 数值变化提示 | WARNING | 选择后短暂显示 `+2 线索` 等数值变化 |
| 进度指示 | WARNING | 显示当前 act / 总进度 |
| 结局收集 | WARNING | 记录已达成结局，标题画面显示 |

---

## 三、构建 Pipeline QA

### 3.1 构建流程

```
Step 1: 解析 story_graph.json + narratives.json
Step 2: 生成资产清单（哪些节点需要背景/立绘/视频）
Step 3: 批量调用图片生成 API（背景 + 立绘）
Step 4: 批量调用视频生成 API（过场视频）
Step 5: 组装 HTML 游戏文件（嵌入所有资产 + 引擎代码）
Step 6: 运行 QA 自动化检查
Step 7: 输出最终 .html 文件 + 资产目录
```

### 3.2 构建检查

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 输入文件存在 | ERROR | story_graph.json 和 narratives.json 都存在 |
| 输入 JSON 合法 | ERROR | 两个文件都是合法 JSON |
| Story Graph 通过 QA | ERROR | story_graph 通过已有 pipeline QA（见 docs/interaction_novel.md） |
| 资产生成成功率 | ERROR (< 70%) / WARNING (< 90%) | 图片/视频生成 API 调用成功率 |
| HTML 输出合法 | ERROR | 输出 HTML 在浏览器中可正常打开 |
| 游戏可启动 | ERROR | 打开 HTML 后显示标题画面 |
| 全路径可达 | ERROR | 从入口到每个结局至少有一条可走通的路径 |

### 3.3 资产生成 Pipeline

```
graph_json ──┐
             ├──→ AssetPlanner ──→ 资产清单 JSON
narr_json ───┘         │
                       ▼
              ┌────────────────┐
              │ 背景图生成      │ → bg_{node_id}.png (每个场景节点)
              │ (并行, 批量)    │   约 20-25 张
              └────────────────┘
              ┌────────────────┐
              │ 角色立绘生成    │ → char_{id}_{expr}.png (每角色 x 表情)
              │ (并行, 批量)    │   约 5 角色 x 4 表情 = 20 张
              └────────────────┘
              ┌────────────────┐
              │ 过场视频生成    │ → video_{node_id}.mp4 (结局 + 死结局)
              │ (串行, 高成本)  │   约 8-10 段
              └────────────────┘
              ┌────────────────┐
              │ BGM 选取/生成   │ → bgm_act_{N}.mp3
              │                │   约 4 首
              └────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ HTML 组装器     │ → game_{story_id}.html
              │ (嵌入引擎+资产) │   单文件可玩版本
              └────────────────┘
```

### 3.4 Prompt 工程 QA

| 检查项 | 级别 | 标准 |
|--------|------|------|
| 背景 Prompt 含场景 | ERROR | prompt 包含 scene_description |
| 背景 Prompt 含时代 | WARNING | prompt 包含 time_period |
| 背景 Prompt 含氛围 | WARNING | prompt 包含 emotional_tone |
| 立绘 Prompt 含外貌 | ERROR | prompt 包含 character.description |
| 立绘 Prompt 含表情 | WARNING | prompt 包含目标表情描述 |
| 视频 Prompt 含叙事 | WARNING | prompt 包含 narrative_text 摘要 |
| 负面 Prompt | WARNING | 包含「no text, no watermark, no UI elements」 |

---

## 四、端到端测试场景

### 4.1 Golden Path 测试

每条路径必须完整走通，验证：文本显示 → 选择交互 → 数值变化 → 路由正确 → 结局显示

| 测试路径 | 关键选择 | 预期结局 | 最终数值 |
|----------|---------|---------|---------|
| 真相路线 | 壁炉→信任→同行→接受交换→陷阱→公开真相 | node_end_02 (真结局) | clues≥5, trust≥2 |
| 中立路线 | 壁炉→信任→同行→接受交换→公开化→接受不完整 | node_end_01 (中立结局) | trust≥2 |
| 冷酷路线 | 壁炉→怀疑→独行→施压→陷阱→完整公开 | node_end_03 (冷酷结局) | clues≥5, trust<0 |
| 遗憾路线 | 画框→信任→同行→坚持警方→公开化→提交证据 | node_end_04 (遗憾结局) | clues≤3 |
| 死结局 1 | 任意→独行(courage<2) | node_dead_01 (黑暗终结) | courage<2 |
| 死结局 2 | 任意→退让 | node_dead_02 (退让代价) | - |
| 死结局 3 | 任意→陷阱(clues≤1) | node_dead_03 (过于自信) | clues≤1 |

### 4.2 边界条件测试

| 测试场景 | 预期行为 |
|----------|---------|
| 所有选项都被锁定 | 显示 fallback 选项或提示 |
| 数值达到上限后继续加 | 数值保持上限不溢出 |
| 数值达到下限后继续减 | 数值保持下限不溢出 |
| 快速连续点击选项 | 只响应第一次点击 |
| 存档后修改 story_graph | 读档时检测版本，提示不兼容 |
| 浏览器刷新 | 自动存档恢复 or 提示重新开始 |
| 背景图加载失败 | 显示纯色背景 + 继续游戏 |
| 视频加载失败 | 跳过视频 + 继续游戏 |

### 4.3 性能测试

| 指标 | 标准 |
|------|------|
| 首屏加载 | <= 3 秒（含背景图） |
| 场景切换 | <= 500ms（含过渡动画） |
| 文本渲染 | 逐字显示无卡顿 |
| 存档/读档 | <= 200ms |
| 总资产大小 | <= 100MB（单故事） |
| 内存占用 | <= 200MB |

---

## 五、输出文件清单

每个故事构建后应产出：

| 文件/目录 | 必需 | 说明 |
|----------|------|------|
| `game_{story_id}.html` | 是 | 可玩的 AVG 游戏主文件 |
| `assets/backgrounds/` | 是 | 背景图 (bg_{node_id}.png) |
| `assets/characters/` | 是 | 角色立绘 (char_{id}_{expr}.png) |
| `assets/videos/` | 推荐 | 过场视频 (video_{node_id}.mp4) |
| `assets/audio/` | 推荐 | BGM + SE |
| `assets/manifest.json` | 是 | 资产清单（节点→资产映射） |
| `qa_report.json` | 推荐 | 自动化 QA 检查报告 |
| `build_log.txt` | 推荐 | 构建日志 |

---

## 六、与现有 Pipeline 的集成点

| 现有模块 | 集成方式 |
|----------|---------|
| Director Agent → story_graph.json | 直接作为 AVG 引擎输入 |
| Branch Writer → narratives.json | 直接作为叙事文本来源 |
| PostWriteValidator | 在叙事文本进入 AVG 前执行 AI 痕迹检测 |
| Auditor | 在构建前验证 story_graph 结构完整性 |
| generate_viz.py | 保留作为调试/开发者视图，AVG 引擎另建 |
| story_graph_schema.py | 复用数据结构定义 |
| Rollout 平台提交框架 | 可扩展为批量生成 AVG 的分布式任务 |

---

## 七、与 Claude-Code-Game-Studios 框架集成

参考 [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) 的以下模式：

| CCGS 模式 | 应用方式 |
|-----------|---------|
| 设计先行 | 本文档即 GDD（Game Design Document），先定义再编码 |
| 单文件 HTML 游戏 | AVG 引擎输出自包含 HTML 文件 |
| 路径范围编码规则 | `avg_engine/` 目录使用专属编码规范 |
| 用户驱动流程 | 每个构建步骤需要确认后执行 |
| QA 门控 | 构建前必须通过自动化 QA 检查 |

不复用 CCGS 的部分：
- 49 Agent 组织结构（过重，本项目单人）
- Godot/Unity 引擎集成（使用纯 Web）
- 72 种 Slash Commands（只保留与 AVG 相关的）

---

## 八、实施计划

| Phase | 内容 | 估时 | 产出 |
|-------|------|------|------|
| Phase 0 | AVG 引擎核心：场景渲染 + 选择交互 + 数值追踪 | 2-3 天 | 可玩的纯文本 AVG |
| Phase 1 | 资产生成 Pipeline：背景图 + 角色立绘批量生成 | 2-3 天 | 有画面的 AVG |
| Phase 2 | 过场视频生成 + 音频集成 | 1-2 天 | 完整多媒体体验 |
| Phase 3 | UI 打磨：存档/设置/回看/快进/结局收集 | 1-2 天 | 完整 AVG 功能 |
| Phase 4 | QA 自动化 + 端到端测试 | 1 天 | 测试报告 |
| Phase 5 | Rollout 平台集成 + 批量生成 | 1-2 天 | 分布式生产线 |

总估时：8-13 天

---

## 九、开放问题

1. **图片生成模型选型** — 使用 MiniMax 图片模型还是 DALL-E？风格一致性如何保证？
2. **视频生成成本** — 每个结局生成视频的 API 成本和时间？是否改用 CSS 动画替代？
3. **资产嵌入 vs 外链** — 单文件 HTML（base64 嵌入）还是资产目录（外链加载）？
4. **多语言支持** — 当前故事为中文，是否需要支持英文 UI？
5. **移动端适配** — 是否需要支持手机触屏交互？
6. **分支回溯** — 是否允许玩家在选择后回退到上一个选择点？
7. **角色立绘风格** — 写实油画风格 vs 动漫风格 vs 半写实？
8. **BGM 来源** — AI 生成 vs 免版权音乐库？

---

## 十、质量标准总结

### P0（必须通过）

- story_graph.json + narratives.json 数据完整且对齐
- 所有 7 条路径（4 结局 + 3 死结局）可完整走通
- 选择按钮正确跳转，数值正确累加
- gate_condition 正确锁定/解锁选项
- 背景图覆盖 >= 50% 节点
- 游戏可正常启动和结束
- 存档/读档功能正常

### P1（重要质量指标）

- 背景图覆盖 >= 80% 节点
- 角色立绘覆盖所有主要角色
- 场景切换有过渡动画
- 文本逐字显示 + 点击跳过
- 数值变化有视觉提示
- 结局画面有差异化表现
- QA 自动化检查全部通过

### P2（锦上添花）

- 过场视频覆盖所有结局
- BGM 覆盖所有 act
- 结局收集系统
- 回看/快进/自动播放
- 移动端适配
- 章节标题卡动画
- 角色表情根据叙事自动切换
