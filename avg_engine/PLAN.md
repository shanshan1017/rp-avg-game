# AVG 互动小说网站规划文档

## 《密室与玫瑰：克劳福德侦探案》 — AVG Engine 重构方案

---

## 一、项目概述

基于 `seed001` 的完整故事数据（`story_graph.json` + `story_readable.txt`），搭建一个 AVG（Adventure Visual Game）风格的 RPG 互动网站。玩家以侦探艾德蒙·克劳福德的视角，通过文字阅读 + 背景切换 + 角色立绘 + 分支选择，完整体验维多利亚时代密室推理故事。

## 二、数据依赖

| 数据源 | 路径 | 用途 |
|--------|------|------|
| 故事图谱 | `outputs/seed001/story_graph.json` | 25个节点、13个分支、3个数值属性、选择门控逻辑 |
| 完整叙事文本 | `outputs/seed001/story_readable.txt` | 每个节点的完整文学叙事 |
| 资源清单 | `avg_engine/assets/manifest.json` | 30张背景图 URL、6个角色立绘 URL、1个视频 URL |
| 可视化参考 | `outputs/seed001/story_graph_viz.html` | 节点图关系结构参考 |

## 三、故事结构

4幕结构，25个节点，7种结局：

```
第1幕 (调查开端)
  node_01 → node_02 → [选择分叉]
                        ├─ node_03a (物证路线, clues+2)
                        └─ node_03b (书面证据路线, clues+1)
                              ↘ 合流 → node_04 [选择分叉]

第2幕 (深入调查)
  node_04 → ├─ node_05_trust (信任路线, trust+2)
            └─ node_05_suspect (怀疑路线, trust-1)
                  ↘ 合流 → node_06 [三选一]
                            ├─ node_07a (协助, clues+2, 需trust≥1)
                            ├─ node_07b (证据威胁, clues+1)
                            └─ node_07c (跟踪, clues+1 courage+1)
                                  ↘ 合流 → node_08 [三选一]

第3幕 (地下室危机)
  node_08 → ├─ node_09_solo → [生死分叉] → node_10_survive / node_dead_basement
            ├─ node_09_william → [生死分叉] → node_10_survive / node_dead_william
            └─ node_09_guided (需trust≥1) → node_10_survive
                  ↘ 合流 → node_11 [三选一]

第4幕 (结局)
  node_11 → ├─ node_12_public (需clues≥4)  → node_end_true / node_end_bittersweet
            ├─ node_12_legal               → node_end_neutral / node_end_cold
            └─ node_12_negotiate (需trust≥2) → node_end_grey
```

## 四、背景图映射

| story_graph node_id | manifest bg key | 说明 |
|---------------------|----------------|------|
| node_01 | node_01 | 庄园外景 |
| node_02 | node_02 | 密室书房 |
| node_03a | node_03a | 壁炉灰烬特写 |
| node_03b | node_03b | 信件特写 |
| node_04 | node_04 | 蓝色客厅 |
| node_05_trust | node_10_trust | 画廊（信任路线） |
| node_05_suspect | node_05_emily | 走廊/女仆场景 |
| node_06 | node_06 | 马厩后院/审讯 |
| node_07a | node_07a | 文件揭秘 |
| node_07b | node_07b | 半真供词 |
| node_07c | node_05_lazaro | 画廊跟踪 |
| node_08 | node_08a | 地下室入口 |
| node_09_solo | node_09_solo | 地下室独行 |
| node_09_william | node_09 | 地下室+威廉 |
| node_09_guided | node_09 | 地下室+引路 |
| node_10_survive | node_11 | 客房整理证据 |
| node_11 | node_11 | 证据抉择 |
| node_12_public | node_12 | 泰晤士报 |
| node_12_legal | node_13a | 律师事务所 |
| node_12_negotiate | node_13b | 书房谈判 |
| node_dead_basement | node_dead_01 | 地下室死亡 |
| node_dead_william | node_dead_02 | 威廉杀死 |
| node_end_true | node_end_01 | 真相结局 |
| node_end_bittersweet | node_end_02 | 苦甜结局 |
| node_end_neutral | node_end_03 | 中性结局 |
| node_end_cold | node_end_04 | 冰冷结局 |
| node_end_grey | node_14 | 灰色交易 |

## 五、角色立绘

6个角色，根据 witnesses 字段决定场景内出现的角色：
- char_edmund, char_isabella, char_lazaro, char_william, char_emily, char_count_ghost

## 六、核心功能

1. **开场标题画面**：游戏标题 + 维多利亚风装饰 + "开始调查" 按钮
2. **幕间过渡**：全屏黑底 + 幕号标题动画过渡
3. **场景展示**：背景图淡入 + 场景标题闪现 + 角色立绘滑入
4. **文字显示**：打字机效果逐字显示叙事文本，点击加速/跳过
5. **选项交互**：门控条件的灰显 + locked_hint 提示
6. **数值系统**：clues / courage / trust_isabella 实时显示
7. **死亡结局**：红色调特效 + "重新开始" / "回到选择点"
8. **通关结局**：根据 ending_type 展示不同风格的结局画面
9. **存档系统**：localStorage 自动存档 + 3个手动存档槽位

## 七、UI 设计

- 主题色：暗金色（#c4a35a）+ 深黑底（#0a0a0f）
- 字体：Noto Serif SC + Noto Sans SC
- 特效：雾气动画、暗角、蜡烛光摇曳、选项悬停金光
- 响应式：16:9 视口自适应

## 八、实施步骤

1. 解析 story_readable.txt → narratives_seed001.json
2. 建立背景图映射配置
3. 重构 game_template.html（完整 AVG 引擎）
4. 运行 build_game.py 构建最终 HTML
5. 测试 & 微调
