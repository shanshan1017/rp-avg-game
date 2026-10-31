# Runtime Container

这里是从工具链里单独拎出来的游戏容器。它的职责是加载 `runtime_game_package.json` 和资产，并把它表现成一个可玩的 AVG。

当前容器：

```text
runtime_container/fixed_avg_runtime/
  index.html
  app.js
  styles.css
  README.md
```

## 如何使用

把任意游戏包复制成：

```text
fixed_avg_runtime/runtime_game_package.json
```

然后在 `fixed_avg_runtime/` 里启动静态服务：

```bash
python -m http.server 8050 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:8050/
```

也可以通过 URL 指定 package：

```text
http://127.0.0.1:8050/?package=/path-or-url/to/runtime_game_package.json
```

## 容器数据契约

容器只读取 runtime package，不读取 planner 或 agent 中间产物。最重要的字段是：

- `meta`: 游戏标题、描述、作者信息、版本信息。
- `engine_contract.asset_base_path`: 资产根路径，通常是 `../assets/<game_id>/`。
- `chapters`: 章节结构。
- `characters`: 角色信息、显示名、默认立绘或 portrait id。
- `nodes`: 剧情节点、节点类型、段落、选择、结局。
- `segments`: 节点里的对白、旁白、状态提示和未来的 `show_layers`。
- `choices`: 玩家选择、目标节点、状态变化。
- `assets`: 图片、视频、UI、音频素材 id 到文件路径的映射。
- `state`: 数值、flag、route gate、成就、结局条件。

容器不应该硬编码某个游戏的节点 id、角色名或素材文件名。所有游戏内容都应该来自 JSON。

## 当前支持的体验

- 首页、继续游戏、重新开始、导入 JSON。
- 主游玩界面：背景、CG、视频、角色立绘、对白框、状态条、选择。
- node 级视频 cinematic：先全屏播放视频，播放完再进入对白 UI。
- 动态角色焦点：优先读取 `segments[].show_layers`；没有时根据 speaker、文本和角色资产推断。
- 世界线：用连线图展示节点关系，可点击跳转做 QA。
- 记录页：查看已抵达节点、选择和结局。
- 本地存档：使用 `localStorage`。

## 后续换皮方向

后面可以保留同一个 JSON 契约，做多个容器版本：

- `avg_xuanhuan_arena`: 玄幻比武，强调舞台、气势、招式、观众压力。
- `avg_romance`: 恋爱向，强调好感度、聊天、表情差分和回忆。
- `avg_mystery`: 悬疑向，强调证据板、线索、嫌疑人关系图。
- `avg_puzzle`: 解谜向，强调道具、密码、roll 点、抽牌或小游戏。
- `renpy_exporter`: 把 runtime package 转换成 RenPy script 和 assets。

容器改造时建议守住三个边界：

1. 游戏状态仍由 JSON 和 runtime state 管。
2. UI 皮肤只改表现，不改变剧情图语义。
3. 新玩法如果需要数据字段，先扩展 schema，再让 pipeline 产出，不在容器里临时猜。

## 当前需要继续补强的地方

- 把 `segments[].show_layers` 从 runtime 推断升级为 pipeline 正式产物。
- 把视频 timeline 从 node 级素材升级为 segment 级或 beat 级规划。
- 增加容器级 skin registry，允许一个 package 选择不同 UI 皮肤。
- 增加类型化交互接口，例如 roll 点、抽牌、证据选择、地图移动。
- 增加移动端布局和触屏 QA。
