# Production Rules

## Story Planning Order

先做整体 storyline，再填充每个节点的具体内容。

1. 先确定完整体验的开场、升级、收束、失败点和多结局。
2. 再确定每个节点的功能：引入角色、制造误会、给选择、惩罚错误、推进结局。
3. 最后才写每段 8-15 秒视频剧本和生成提示词。

这样可以避免先写局部桥段导致整体路径超时、分支断裂或角色动机不统一。

## Multi-Agent Production Workflow

默认采用三 agent 生产结构：

- Planning Agent：当前 Codex。负责需求澄清、整体 storyline、runtime asset contract、schema 化台本、资产计划、能力选择和交接包。
- Executive Agent：Claude Code 1。负责读取 Planning 交接包，按批准范围扩写 prompt、提交生成任务、保存本地文件、写 manifest 和执行报告。
- Checker Agent：Claude Code 2。负责只读审查执行结果，输出 QA report、blocking issues、rerun list 和是否可进入下一 gate 的结论。

硬性顺序：

1. Planning 产出计划和验收标准。
2. 用户确认计划或要求修改。
3. Executive 只执行批准范围。
4. Checker 独立验收。
5. Checker 通过前不得进入下一 gate 或 runtime package。

禁止事项：

- Planning 不直接启动批量付费生成，不跳过 runtime asset contract。
- Executive 不擅自改 story graph，不扩大素材范围，不把短期 URL 或 API key 写入仓库。
- Checker 不提交生成任务，不直接修复正式产物，不把 Executive 自述通过当作验收证据。

旧的 Director / Detail / Prompt / Asset Runner 职能仍然存在，但都必须挂到上述三角色里：Planning 负责 Director 和验收标准，Executive 负责 Detail / Prompt / Asset Runner，Checker 负责独立审计。

## Perspective Rules

- 全程第一视角，镜头就是男主视角。
- 男主不出镜，不出现男主正脸、背影、镜中倒影、证件照、社交头像。
- 尽量不出现男主手部特写；如果互动必须出现，用道具或镜头运动替代。
- 女生可以直视镜头、靠近镜头、递物品、挡住去路、发消息。
- UI 选项代表男主的行动或回答，不需要视频里出现男主说话画面。

## Character Rules

女生角色可以包括：

- 邻家妹妹：熟悉、直球、带一点小吃醋。
- 高冷上司姐姐：成熟、克制、压迫感强，但行为不越界。
- 网吧偶遇少女：灵动、游戏感、神秘又会挑衅。
- 可选反差角色：表面温柔、实际掌控信息的摄影/社团少女。

所有角色必须是成年设定。互动保持恋爱喜剧、轻悬疑、暧昧张力，不写露骨成人内容。

## Asset Rules

- 先生成角色参考图，再生成视频。
- 不使用真人照片、真实名人、影视角色、网红脸、可识别公众人物。
- 统一使用原创风格化视觉：anime cinematic illustration / 2.5D animated film look。
- 角色参考图要固定发型、发色、服装主色、配饰、表情特征。
- 每个视频节点优先引用角色图和上一段尾帧，保证连续性。
- 火山方舟返回的视频 URL 有时效，必须下载或转存后再写入游戏 manifest。

## Frontend Rules

- 前端只读取 `game_config.json`，不硬编码剧情。
- 选择按钮、条件、数值变化、失败、结局都由配置驱动。
- 选项层不要遮挡角色脸和关键动作，默认放在底部安全区。
- 每段视频结束后或 `choice_timing_sec` 到达时弹出选项。
- 失败节点必须有“回到上一个选择点”和“重新开始”。
