# AVG Tool Comparison V1

Date: 2026-05-19

This note compares three local references for the interactive-video / AVG toolchain:

- Story-to-game: `<STORY_TO_GAME_ROOT>`
- Story Graph pipeline: `<STORY_GRAPH_ROOT>`
- Current tool: `<PROJECT_ROOT>/tool_versions/cross_disciplinary_coherence_v1`

The goal is not to pick one winner. The goal is to decide what our tool should absorb so it can create more playable, dramatically satisfying, cross-disciplinary coherent games.

## One-line Diagnosis

Story-to-game is the best playable pure-text launcher and writing-rule package. Story Graph pipeline is the strongest story-graph-to-prose generation pipeline. Our current tool is strongest at cross-disciplinary production alignment, but still weak at scene dramaturgy and player-facing writing.

## Comparison Table

| Dimension | Story-to-game | Story Graph pipeline | Current Tool |
| --- | --- | --- | --- |
| Primary purpose | Convert story/novel/script into playable branching text JSON and run it in a single HTML launcher. | Generate complete interactive novel story graph and prose from a seed. | Produce a reusable media game production package with story, mechanics, art/video/UI/runtime/QA alignment. |
| Top-level authority | Original story + adaptation skill. | Director-generated StoryGraph. | Planner-controlled cross-disciplinary coherence plan. |
| Runtime | Strongest among the three for text AVG: HTML launcher, import/cache, save/load, achievements, chapters, ambience, dev tools. | Mostly output/visualization, not a polished player runtime. | Review runtime exists and has worldline inspection, but presentation rendering is still flatter than schema. |
| Story structure | Beat sequence, branch topology, branch literary outline, state/end matrix. | Four-act StoryGraph with nodes, branches, choices, value system, facts, witnesses. | Story graph gate exists, but v5 case did not yet enforce a strong scene-writing pass. |
| Scene writing | Very strong rulebook: opening establishment, choice callbacks, first appearance, scene transitions, branch self-sufficiency. | Strong writer prompt with World Bible + Graph Summary + branch detail, 400-800 chars per narrative node. | Current campus v5 scene text too short and functional, often 180-315 chars per cell. |
| Choice quality | Excellent explicit rule: every choice must have immediate textual callback; variables alone do not count. | Strong anti-pseudo-choice and value/gate rules. | Mechanics-state alignment exists, but player-visible callback is not yet a hard schema/checker gate. |
| Branch completeness | Strong: even rash endings need setup -> consequence -> closure; branches must be treated as real story paths. | Good: normal endings, dead endings, branch arcs, auditor checks funnel/pseudo choice. | Structural route validation exists; dramatic branch completeness still weak. |
| Character consistency | Mostly text-level character cards and first appearance rules. | World Bible + character speech style + witnesses. | Strongest future potential: character bible can connect to visual anchors, prompt packs, portraits, video references. |
| Art/video/UI | Not first-class beyond ambience/effects. | Not first-class. | First-class: asset slots, prompt pack, generation manifest, UI/video surfaces, media traceability. |
| QA/checking | JSON validator + literary self-check rules. | RuleAuditor + PostWriteValidator, strong structure checks. | Coherence matrix concept is strongest, but needs dramatic-quality and runtime-display checks. |
| Scalability | Good for pure text; 361-node sample loads easily. | Good for medium interactive novel generation, but not media production. | Best architecture for multi-agent production, but agent tasks need smaller contracts and better retry/progress handling. |

## Concrete Local Stats

These are corpus-level numbers, not exact single-route playtime.

- Story-to-game sample `成人日`: 361 nodes, 132 choice nodes, 7 endings, 9 achievements, about 23,241 CJK chars in node/ending text.
- Story Graph pipeline `seed003`: 32 story graph nodes, 6 choice nodes, 7 terminal nodes, 12 branches, about 29,142 chars of generated narrative text.
- Our campus v5: 36 cells, 8 choice cells, about 7,468 chars in cell bodies.

Interpretation:

- Story-to-game uses many tiny nodes and frequent interaction. Its average content node is short, but the route feels active because choices and callback nodes are dense.
- Story Graph pipeline uses fewer but much richer prose nodes. It feels more literary and complete, but less immediately game-runtime-ready.
- Our v5 has middle-sized cells but too few dramatic beats inside each cell. It reads like a clean outline expanded into paragraphs, not like scenes being acted.

## What Story-to-game Teaches Us

The most valuable part is not only the launcher. It is the writing discipline:

1. Opening establishment is mandatory: the first 2-3 nodes must answer who I am, where I am, when it is, and what situation is already pressuring me.
2. Every choice needs a visible callback. `val`, `flag`, and `achievement` do not count unless the next screen reacts in text.
3. First appearance matters: when a major character, location, or prop appears, the player must visually understand it immediately.
4. Scene transitions need glue: choices should not teleport the player to the next fact.
5. Branches must be complete: even short wrong paths need cause -> consequence -> closure.
6. Information isolation must be enforced: a later node cannot assume the player learned something on a different branch.

These are exactly the missing checks behind the campus v5 stiffness.

## What the Story Graph Pipeline Teaches Us

The Story Graph pipeline's strongest design is separation of responsibilities:

- Director produces structured graph instructions, not final prose.
- Writers receive World Bible, Graph Summary, local branch details, and style config.
- Auditor checks structure after writing.

Useful Story Graph pipeline fields to keep or adapt:

- `scene_description`
- `key_events`
- `emotional_tone`
- `facts_introduced`
- `witnesses`
- character `speech_style`
- value system and ending conditions

The Story Graph pipeline also gives a better prose budget: 400-800 Chinese chars for narrative nodes and 200-400 for choice nodes. Our campus v5 often stayed below the amount needed for scene rhythm.

## What Our Current Tool Already Has That The Others Lack

Our tool is closest to the final target because it treats game production as more than text:

- project intake and permission gates;
- story graph planning gate;
- hybrid script schema with `text_image`, `video`, `choice`, `ending`, `failure` modes;
- runtime UI surfaces such as phone, right-top hints, memory log, profile panel;
- character layers and asset slots;
- image/video prompt packs and generation manifests;
- coherence matrix tying story facts to assets, mechanics, UI, runtime, and QA;
- isolated agent runner concept.

This is the right foundation for interactive video/AVG production, but it needs stronger story craft gates before media planning.

## Main Gap In Our Tool

The current missing middle layer is **Scene Dramaturgy**.

We currently jump from story graph to media story plan / hybrid script too quickly. That means a unit can be structurally correct but dramatically thin.

Add a required gate between story graph and hybrid script:

```text
story_graph_plan.json
-> scene_dramaturgy_plan.json
-> media_story_plan.json
-> hybrid_script.json
```

Each scene/unit should require:

- player establishment: who/where/when/current pressure;
- active characters and each character's immediate want;
- conflict or obstacle;
- turn: what changes by the end;
- required visible evidence;
- required dialogue beats;
- choice callback requirement;
- branch information boundary;
- setup/payoff links;
- art/UI/video hooks;
- minimum content budget.

## Recommended Direction

Do not replace our tool with Story-to-game or the Story Graph pipeline.

Use this blend:

1. Keep our tool as the top-level cross-disciplinary planner.
2. Borrow the Story Graph pipeline's Director/Writer/Auditor separation and World Bible / Graph Summary handoff.
3. Borrow Story-to-game's writing laws as hard gates for playability.
4. Upgrade our runtime to consume rich `sequence_steps`, not flat `body` paragraphs.
5. Add a text-only playable launcher mode early, before image/video generation, so we can validate story fun cheaply.

## Next Implementation Priorities

1. Add `scene_dramaturgy_plan.schema.json`.
2. Add `scene_writer_contract.md` based on Story Graph pipeline + Story-to-game rules.
3. Add checker rules for:
   - opening establishment;
   - choice visible callback;
   - first appearance;
   - branch information isolation;
   - branch closure;
   - scene turn;
   - minimum prose/beat budget.
4. Upgrade review runtime to support sequence playback: background, portrait/expression, narration, dialogue, phone message, hint, memory unlock, choice.
5. Re-run campus triangle as v6 in text-only mode first.
6. Only after v6 reads well, connect prompt/asset/video generation.

## Product Positioning

Story-to-game says: turn a story into a playable text game.

The Story Graph pipeline says: generate a complex interactive novel from a seed.

Our tool should say: plan and validate a playable AVG / interactive video production where story, choices, UI, character art, video, and runtime all agree before spending money on assets.
