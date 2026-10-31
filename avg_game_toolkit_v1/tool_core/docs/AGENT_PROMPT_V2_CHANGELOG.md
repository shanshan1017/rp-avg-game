# Agent Prompt V2 Changelog

This changelog records how the agent instruction pack was deepened after absorbing:

- `SCRIPT_WRITING_TUTORIAL_GUIDE.md`
- `VISUAL_NOVEL_TUTORIAL_GUIDE.md`

## Global Changes

- Upgraded `agent_instructions/README.md` from V1 to V2.
- Added shared Story Intention Gate language.
- Added the visual novel production formula:

```text
Visual Novel = (Narrative + Visual / Audio Presentation) x Interactivity
```

- Required every agent report to mention alignment with:
  - core intention;
  - player comprehension;
  - visible choice feedback;
  - asset-story traceability;
  - runtime package feasibility.

## Per-Agent Changes

### Planner

- Added ownership of `story_intention_statement`.
- Added mandatory G1.5 Story Intention Gate before story graph planning.
- Added requirement to define core question, emotional anchor, central conflict, intended choice pressure, ending philosophy, gameplay-expression of intention, and each main character's role in the intention.
- Added judgement rules for rejecting scenes, choices, assets, and mechanics that do not serve the intention or player comprehension.

### Story Graph Director

- Added requirement that every branch tests or expresses the approved story intention.
- Added route/intention matrix expectation.
- Added ending policy distinction: true-ending structure vs multiple equal answers.
- Added route function rule: routes must differ by value pressure, not only by character.
- Added node type `callback` to protect visible choice feedback.

### Scene Dramaturgy Agent

- Added `intention function` to every scene plan.
- Added Visual Novel Triad Check for every playable scene:
  - Narrative;
  - Presentation;
  - Interactivity.
- Strengthened scene requirements around present-tense pressure, character want, obstacle, conflict, and turn.
- Added explicit presentation mode requirement.

### Narrative Writer

- Added rule that core intention must be felt through action/dialogue/consequence, not stated as a slogan.
- Strengthened segment rhythm requirements.
- Added callback segment guidance after choices.
- Added current desire and speech-pattern requirements for major characters.
- Added prohibition against lore-only or task-only scene writing.

### Character / World Agent

- Added story-intention alignment for each major character.
- Added desire, fear, contradiction, behavior-under-pressure, and emotional defense requirements.
- Added symbolic function for recurring props.
- Added requirement that every major character and recurring prop has a reason to exist in the core intention.

### Mechanics Agent

- Added requirement that values/flags express the core question or route pressure.
- Added true-ending vs multiple-answer ending logic guidance.
- Added visible interpretation requirement for relationship values.
- Added achievement and checkpoint notes when they reinforce story memory.
- Strengthened failure fairness and visible echo requirements.

### Art / Video / UI Agent

- Added requirement that every asset support the narrative intention, emotional anchor, and player comprehension.
- Added global visual bible as a required asset type.
- Added CG/video restraint: use them only for emotional, dramatic, route, or reward peaks.
- Added rule that every CG/video must explain why normal portrait dialogue is insufficient.
- Strengthened style consistency and asset-story traceability requirements.

### Audio Agent

- Added a dedicated audio department prompt.
- Added BGM, ambience, SFX, silence, optional voice, and runtime audio mapping responsibilities.
- Added rule that audio must support the core intention and emotional anchor, not just generic atmosphere.
- Added audio fallback and licensing/safety rules.

### Runtime Agent

- Added `story_intention_statement` metadata as an input.
- Added requirement to preserve segmented reading rhythm and choice callbacks.
- Added package assembly rules for intention summary, chapters, endings, achievements, and asset manifest metadata.
- Added QA/player mode distinction for missing required vs optional assets.

### Checker Agent

- Added audit against story intention, not only schema validity.
- Added checks for scene dramaturgy, visual novel triad, segment rhythm, and route value pressure.
- Added severity guidance for blocker/major/minor issues.
- Added requirement to classify findings by story intention, player comprehension, choice fairness, asset-story traceability, or runtime loadability.
