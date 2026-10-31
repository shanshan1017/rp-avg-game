# Project Intake Gate

This gate makes new-game starts repeatable. Before planning or execution, the user request is normalized into `project_intake.json`.

## Purpose

The Planner should not invent hidden requirements every time. Intake records what the user actually asked for, what can be safely assumed, and what requires permission before execution.

## Required Files

- `templates/project_intake_questionnaire.md`
- `templates/project_intake.template.json`
- `schemas/project_intake.schema.json`

## Gate Position

```text
G0 Project Intake
  -> G1 Coherence Plan
  -> G2 Story Graph Plan
  -> G3 World / Character / Mechanics Baseline
```

`project_intake.json` is the user-facing input contract. `media_project_brief.json` is the normalized production brief derived from it.

## Minimum Answers

The Planner must collect or explicitly assume:

- game type and genre;
- core premise;
- target player experience;
- player POV, identity, and visibility rule;
- main characters;
- target playtime;
- ending policy;
- interaction density;
- presentation format and runtime target;
- art direction and references;
- hard constraints;
- permission to plan, execute agents, and/or generate paid assets.

## Ask Policy

If a missing field would change story structure, runtime format, safety, budget, or paid generation, it is `must_ask`.

If a missing field can be filled with a conservative default, Planner may assume it only when `approved_to_make_assumptions=true`, and must record it in `unknowns` or `planner_notes`.

Never start paid generation unless `paid_generation_allowed=true`.

Never launch execution agents unless `approved_to_start_execution=true` or the user has explicitly asked for a planning-only dry run that requires checker/planning agents.

## Output Policy

After intake, Planner may produce:

- `project_intake.json`
- `media_project_brief.json`
- `coherence_plan.json`

Planner should not produce `story_graph_plan.json` until the user has either approved the intake or approved assumptions.

## Suggested User Prompt

```text
我先需要固定入口信息，填短句就可以：

1. 游戏类型/题材：
2. 一句话核心设定：
3. 玩家是谁、视角、主角是否可见：
4. 主要角色：
5. 目标游玩时长：
6. 结局数量：
7. 选择密度/玩法：
8. 表现形式和目标 runtime：
9. 美术风格/参考：
10. 硬限制：
11. 是否允许我先做合理假设并开始规划：
12. 是否允许启动 agent 或生成付费素材：
```
