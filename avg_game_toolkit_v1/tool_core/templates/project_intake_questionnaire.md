# Project Intake Questionnaire

Use this before starting a new interactive media/game project. The Planner should ask for missing `must_ask` fields before writing `coherence_plan.json` or launching worker agents.

## Minimum Required Answers

1. Game type and genre:
   - Example: campus romance mystery AVG, first-person thriller, interactive video comedy.

2. Core premise:
   - Who is the player?
   - Where/when does it happen?
   - What is the central conflict?

3. Target player experience:
   - What should the player feel? Sweet, tense, tragic, clever, scary, funny, etc.

4. Player role and visibility:
   - POV: first-person / third-person / mixed.
   - Player identity.
   - Can the protagonist appear on screen?

5. Main characters:
   - Name or role.
   - Relationship to player.
   - Any must-keep personality or visual traits.

6. Playtime:
   - Minimum / target / maximum route duration.

7. Endings:
   - Normal endings.
   - True endings.
   - Failure/bad endings.

8. Interaction density:
   - Few meaningful choices, many choices, value/stat strategy, route locks, etc.

9. Presentation format:
   - HTML, Godot, HTML first then Godot, or asset package only.
   - Text+image, video, choices, UI overlays, audio.
   - Which moments deserve video?

10. Art direction:
    - Style description.
    - Reference files if any.
    - Forbidden styles or references.

11. Hard constraints:
    - Safety, IP, protagonist visibility, budget, asset generation, model/provider, deadline.

12. Permission:
    - May Planner make assumptions?
    - May Planner start planning?
    - May agents execute?
    - Is paid image/video generation allowed now?

## Short User-Facing Prompt

```text
先填一下固定入口信息：

1. 游戏类型/题材：
2. 一句话核心设定：
3. 玩家是谁、第一/第三视角、主角是否可见：
4. 主要角色：
5. 目标游玩时长：
6. 结局数量：
7. 选择密度/玩法：
8. 表现形式：文字+图 / 视频 / HTML / Godot：
9. 美术风格和参考：
10. 硬限制：
11. 我是否可以先做合理假设并开始规划：
12. 这轮是否允许启动 agent 或生成付费素材：
```

## Planner Rule

If the user gives only a loose premise, Planner may fill safe assumptions only when `approved_to_make_assumptions=true`. Otherwise ask a short follow-up before writing `coherence_plan.json`.

Never start paid generation until `paid_generation_allowed=true`.

Never launch execution agents until `approved_to_start_execution=true`, unless the user explicitly asked for a planning-only dry run.
