"""Schema helpers for first-person interactive video stories.

This module is intentionally small for the planning phase. It defines the
shape Director and Writer agents should agree on before we generate assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class NodeType(str, Enum):
    VIDEO = "video"
    CHOICE = "choice"
    FAILURE = "failure"
    ENDING = "ending"


class VisualStyle(str, Enum):
    ANIME_25D = "anime_25d"
    CINEMATIC_ILLUSTRATION = "cinematic_illustration"


@dataclass
class StateEffect:
    key: str
    delta: int


@dataclass
class Choice:
    id: str
    label: str
    target: str
    effects: list[StateEffect] = field(default_factory=list)
    condition: dict[str, str] = field(default_factory=dict)
    locked_hint: str = ""
    is_failure: bool = False


@dataclass
class VideoAssetRef:
    src: str = ""
    poster: str = ""
    character_refs: list[str] = field(default_factory=list)
    first_frame_ref: str = ""
    last_frame_ref: str = ""


@dataclass
class VideoNode:
    node_id: str
    title: str
    node_type: NodeType = NodeType.VIDEO
    duration_sec: int = 12
    act: int = 1
    checkpoint: bool = False
    scene_goal: str = ""
    first_person_camera: bool = True
    protagonist_visible: bool = False
    visual_style: VisualStyle = VisualStyle.ANIME_25D
    characters_on_screen: list[str] = field(default_factory=list)
    location: str = ""
    mood: str = ""
    video_prompt: str = ""
    negative_prompt: str = ""
    asset: VideoAssetRef = field(default_factory=VideoAssetRef)
    choice_timing_sec: int | None = None
    choices: list[Choice] = field(default_factory=list)
    ending_label: str = ""
    ending_condition: str = ""

    def validate(self) -> list[str]:
        issues: list[str] = []
        if self.duration_sec < 8 or self.duration_sec > 15:
            issues.append(f"{self.node_id}: duration_sec should be 8-15")
        if not self.first_person_camera:
            issues.append(f"{self.node_id}: must stay first-person")
        if self.protagonist_visible:
            issues.append(f"{self.node_id}: protagonist must not be visible")
        if self.choice_timing_sec is not None and self.choice_timing_sec >= self.duration_sec:
            issues.append(f"{self.node_id}: choice_timing_sec must be before video end")
        return issues


@dataclass
class Character:
    id: str
    name: str
    age: int
    archetype: str
    personality: str
    visual_anchors: list[str]
    image_prompt: str
    negative_prompt: str


@dataclass
class VideoStory:
    game_id: str
    title: str
    entry_node_id: str
    target_total_seconds: tuple[int, int] = (60, 90)
    initial_state: dict[str, int] = field(default_factory=dict)
    characters: dict[str, Character] = field(default_factory=dict)
    nodes: dict[str, VideoNode] = field(default_factory=dict)

    def validate(self) -> list[str]:
        issues: list[str] = []
        if self.entry_node_id not in self.nodes:
            issues.append("entry_node_id is missing from nodes")
        for node in self.nodes.values():
            issues.extend(node.validate())
            for choice in node.choices:
                if choice.target not in self.nodes:
                    issues.append(f"{node.node_id}: choice {choice.id} targets missing node {choice.target}")
        return issues

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
