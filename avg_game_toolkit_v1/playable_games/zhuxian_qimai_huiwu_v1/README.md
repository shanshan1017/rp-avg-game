# 诛仙_v1 可玩游戏包

这是当前可直接试玩的游戏案例：

- `game_id`: `zhuxian_qimai_huiwu_v1`
- `title`: `诛仙之七脉会武:四强台前`
- 玩家视角：第三人称张小凡
- 核心冲突：张小凡在七脉会武四强迎战陆雪琪，要在实力暴露、情愫、师门目光和胜负之间做选择。
- 美术风格：国漫玄幻

## 目录结构

```text
zhuxian_qimai_huiwu_v1/
  README.md
  asset_package_summary.json
  runtime/
    index.html
    app.js
    styles.css
    runtime_game_package.json
  assets/
    zhuxian_qimai_huiwu_v1/
      images/
      videos/
```

`runtime/` 是网页 AVG 容器加这版游戏的 JSON。`assets/` 是 JSON 当前实际引用到的素材文件。

## 运行方式

从本目录启动：

```bash
python -m http.server 8062 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:8062/runtime/
```

也可以从 handoff 根目录执行：

```bash
./start_zhuxian_preview.sh 8062
```

## JSON 和资产契约

游戏入口 JSON：

```text
runtime/runtime_game_package.json
```

JSON 内的资产根路径：

```text
../assets/zhuxian_qimai_huiwu_v1/
```

因此 runtime 页面位于 `runtime/` 目录时，会到相邻的 `assets/zhuxian_qimai_huiwu_v1/` 查找图片和视频。

只要一个容器能读取 `runtime/runtime_game_package.json`，并按 `engine_contract.asset_base_path` 解析资产路径，就可以直接运行这版游戏。

## 当前包摘要

摘要文件：

```text
asset_package_summary.json
```

关键数据：

- 节点数：41
- 选择节点数：8
- 结局数：5
- 角色数：5
- 章节数：4
- asset entry 数：99
- 已复制的唯一真实素材文件：52
- 缺失素材：0
- placeholder 素材：0
- 视频：2

视频文件：

```text
assets/zhuxian_qimai_huiwu_v1/videos/vid_arrival_drum_step.mp4
assets/zhuxian_qimai_huiwu_v1/videos/vid_lu_arrival_intent.mp4
```

## 当前 runtime 表现

- 首页已经改成游戏入口，不再展示无关的节点素材墙。
- 世界线是连线图，可以看到节点关系。
- 视频作为开场 cinematic：先全屏播放，结束后出现 UI，再点击继续进入对白。
- 角色图不会作为主屏 CG 常驻混在一起；主屏优先展示背景、CG、视频。
- 角色立绘会随 speaker / focus 切换；当前优先支持 `segments[].show_layers`，但这版 JSON 还没稳定产出该字段，所以 runtime 有推断兜底。

## 已知问题

- `storyline` / `scene_dramaturgy` 里还没有完整规划“每句对白对应谁出场、谁退场、谁高亮”，这会影响角色立绘的精确切换。
- 视频目前是 node 级素材，不是 segment 级 timeline；后续需要在 story graph 或 scene dramaturgy 中规划播放顺序和触发点。
- 当前素材是通用图像生成结果，不是严格透明立绘差分，因此容器里仍需要进一步规范 portrait layer。
- 这版是 HTML runtime showcase，不是 RenPy 项目；但 JSON 和资产已经独立，可以作为 RenPy exporter 的输入。

## 移植给其他容器

最小输入只有两类：

```text
runtime/runtime_game_package.json
assets/zhuxian_qimai_huiwu_v1/
```

容器需要实现：

1. 加载 JSON。
2. 根据 `nodes` 和 `choices` 推进剧情。
3. 根据 `state` 应用选择效果和 route gate。
4. 根据 `assets` 和 `engine_contract.asset_base_path` 加载素材。
5. 根据 `segments` 呈现对白、旁白、状态提示和角色焦点。

这样就能做到：读取 JSON + 拥有资产 = 直接玩游戏。
