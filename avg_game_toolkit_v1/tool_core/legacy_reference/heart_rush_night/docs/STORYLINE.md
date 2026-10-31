# Storyline Draft

## 工作标题

《心动失控夜》

## 一句话

周五夜晚，你刚准备下班，却发现邻家妹妹、高冷上司姐姐、网吧偶遇少女同时在找你。你必须在不断升级的误会和追逐里做选择，决定这一晚会变成甜蜜约会、事业绑定、游戏搭档，还是彻底修罗场。

## 体验目标

- 类型：第一视角恋爱喜剧 + 轻悬疑追逐。
- 单局时长：60-90 秒。
- 单节点视频：8-15 秒。
- 典型路径：开场 + 2-3 个中间节点 + 1 个抉择节点 + 1 个结局视频。
- 情绪曲线：轻松开场 -> 被包围的压力 -> 误会升级 -> 诚实或逃避的选择 -> 多结局。

## 核心设定

你是一个刚下班的普通男生，今天同时欠下三件事：

- 答应邻家妹妹帮她试吃新做的夜宵。
- 答应上司姐姐今晚交一份紧急方案。
- 答应网吧偶遇少女上线打一场双排。

你原本以为这些事能错开，结果她们都提前出现，并且都掌握了一部分“你可能放鸽子”的证据。整局游戏的真正问题不是选谁，而是你要不要继续躲。

## 角色阵容

| 角色 | 类型 | 功能 |
| --- | --- | --- |
| 林小满 | 邻家妹妹 | 情感压力，提醒玩家曾经许下的日常约定 |
| 沈以霜 | 高冷上司姐姐 | 事业压力，推动玩家面对责任 |
| 祁夏 | 网吧偶遇少女 | 逃离路线，提供轻快但危险的分支 |
| 白鹿 | 反差摄影少女 | 信息操盘者，可作为 true ending 的关键见证人 |

## 状态变量

- `honesty`：诚实度。直接影响 true ending 和失败概率。
- `warmth`：亲近感。偏向林小满路线。
- `focus`：责任感。偏向沈以霜路线。
- `sync`：默契感。偏向祁夏路线。

## 整体节点图

```text
node_01_office_exit
  ├─ node_02_boss_elevator
  │    ├─ node_03_crosswalk
  │    └─ fail_lie_receipt
  ├─ node_02_neighbor_gate
  │    ├─ node_03_crosswalk
  │    └─ fail_phone_screen
  └─ node_02_cafe_alley
       ├─ node_03_crosswalk
       └─ fail_wrong_escape

node_03_crosswalk
  ├─ node_04_truth_groupchat
  ├─ node_04_keep_juggling
  └─ fail_panic_freeze

node_04_truth_groupchat
  ├─ end_neighbor_warmth
  ├─ end_boss_midnight_plan
  ├─ end_cafe_duo
  └─ end_true_open_calendar

node_04_keep_juggling
  ├─ end_neighbor_warmth       条件：warmth >= 2 且 honesty >= 1
  ├─ end_boss_midnight_plan    条件：focus >= 2 且 honesty >= 1
  ├─ end_cafe_duo              条件：sync >= 2 且 honesty >= 1
  └─ fail_rooftop_showdown     默认失败
```

## 节点职能草案

| 节点 ID | 时长 | 职能 | 视频画面 |
| --- | ---: | --- | --- |
| `node_01_office_exit` | 12s | 开场，三条消息同时压来 | 第一视角走向电梯，手机震动，电梯门反光但不见男主 |
| `node_02_boss_elevator` | 13s | 上司路线引入 | 沈以霜按住电梯门，冷静地问“方案在哪” |
| `node_02_neighbor_gate` | 13s | 邻家路线引入 | 林小满拎着夜宵盒在小区门口等你 |
| `node_02_cafe_alley` | 13s | 网吧路线引入 | 祁夏靠在霓虹招牌下晃着你的会员卡 |
| `node_03_crosswalk` | 14s | 合流升级，所有人都快到了 | 斑马线红灯，三条语音同时弹出 |
| `node_04_truth_groupchat` | 14s | 诚实路线，进入多结局选择 | 你发出群聊解释，三个女生先后看向镜头 |
| `node_04_keep_juggling` | 14s | 继续周旋路线，风险路线 | 镜头在楼梯、街角、便利店之间快速移动 |
| `fail_lie_receipt` | 8s | 说谎被上司用打卡/收据拆穿 | 沈以霜把收据推到镜头前 |
| `fail_phone_screen` | 8s | 藏手机被小满看到弹窗 | 林小满笑容停住，镜头被夜宵袋挡住 |
| `fail_wrong_escape` | 8s | 误进错误包间被围观 | 网吧包间门打开，一群人回头看镜头 |
| `fail_panic_freeze` | 8s | 什么都不回，三人同时出现 | 三个身影从不同方向逼近，画面切黑 |
| `fail_rooftop_showdown` | 10s | 周旋失败，屋顶摊牌 | 白鹿举起相机，揭示你所有时间线冲突 |
| `end_neighbor_warmth` | 12s | 小满结局 | 小区长椅，她把夜宵递到镜头前 |
| `end_boss_midnight_plan` | 12s | 上司结局 | 办公室夜景，沈以霜把方案改名为两人版本 |
| `end_cafe_duo` | 12s | 网吧结局 | 祁夏戴上耳机，屏幕显示双排胜利 |
| `end_true_open_calendar` | 12s | 真结局 | 四人一起看共享日历，白鹿拍下“诚实后的第一张合照” |

## 当前不展开的内容

下一步再写每个节点的完整短剧本、对白、镜头运动和生视频 prompt。现在只锁住整体路线、节点功能和角色关系。
