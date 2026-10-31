# Codex Agent Supervision Protocol

This protocol is for Codex internal subagents launched from the main Planner thread. It replaces ad hoc worker prompts and prevents long-running agent work from disappearing into chat-only state.

## Planner Responsibilities

For every subagent task, the Planner must create or update a project-local supervision board:

- `reports/codex_agent_supervision.json`

Validate the board with:

```bash
python bin/validate_codex_agent_supervision.py /absolute/path/to/reports/codex_agent_supervision.json
```

Each record must include:

- `agent_id`: internal Codex agent id returned by the launcher
- `nickname`: optional internal nickname
- `role`: bounded role, such as `generation_executive`, `art`, `runtime`, or `checker`
- `task`: one-sentence task
- `owned_paths`: paths the agent may write
- `forbidden_paths`: paths the agent must not write
- `status`: `launched`, `running`, `completed`, `blocked`, `failed`, or `closed`
- `started_at`
- `last_checked_at`
- `completed_at`
- `result_summary`
- `result_files`
- `next_action`

The Planner must not rely only on chat notifications. After each `wait_agent` result or subagent notification, update the supervision board before launching follow-up work.

## Worker Responsibilities

Every Codex worker prompt must include:

- the role and exact owned write scope
- the exact input artifacts to inspect
- the expected output files
- a requirement to write progress or final status into project files when the task touches local project state
- a reminder that other agents may be editing nearby files and that the worker must not revert unrelated changes
- a reminder not to print or write secrets

For long-running local work, workers should write one of:

- `reports/<role>_worker_run_status.md`
- `reports/agent_runs/<run_id>/progress.jsonl`
- `reports/agent_runs/<run_id>/agent_report.json`

## Monitoring Cadence

Planner monitoring loop:

1. Register each new agent before doing other work.
2. Use `wait_agent` only when the next step needs that result; otherwise continue non-overlapping local work.
3. If an agent returns `completed`, read its result files and classify the outcome:
   - complete: integrate outputs or launch the next dependent task
   - blocked: record blocker and stop dependent paid/provider work
   - failed: record failure and decide retry/replan
4. If an agent is still running, update `last_checked_at` and keep working elsewhere.
5. Close agents that are no longer needed.

## Next-Task Gate

Do not launch the next dependent task unless the previous worker produced one of:

- a valid `agent_report.json` with `status=complete`, or
- a role-specific status report that explicitly says the next task is safe.

Blocked provider work must not be followed by generation or runtime asset integration. It should route to Planner decision: fix credentials/network/base URL, or switch provider.

## Current Tool Gap

`run_pipeline.py` still contains the older Claude Code workspace launcher. Until it is replaced with Codex-native orchestration, Codex subagent supervision is maintained by the Planner through `reports/codex_agent_supervision.json`, `bin/validate_codex_agent_supervision.py`, and role-specific status reports.
