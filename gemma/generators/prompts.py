"""Prompt template system — loads and renders image & caption prompts from YAML."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from gemma.persona.character import GemmaPark, get_character


PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@dataclass
class SceneTemplate:
    name: str
    prompt: str
    lighting: str = "natural"
    outfit_type: str = "trail_running"
    aspect_ratio: str = "1:1"


@dataclass
class PromptLibrary:
    """Manages prompt templates for image and caption generation."""

    scenes: list[SceneTemplate] = field(default_factory=list)
    caption_prompts: dict[str, str] = field(default_factory=dict)
    hook_prompts: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, prompts_dir: Path | None = None) -> PromptLibrary:
        """Load prompt templates from YAML files."""
        directory = prompts_dir or PROMPTS_DIR
        library = cls()

        # Load image templates
        image_file = directory / "image_templates.yaml"
        if image_file.exists():
            data = yaml.safe_load(image_file.read_text())
            for scene in data.get("scenes", []):
                library.scenes.append(SceneTemplate(**scene))

        # Load caption templates
        caption_file = directory / "caption_templates.yaml"
        if caption_file.exists():
            data = yaml.safe_load(caption_file.read_text())
            library.caption_prompts = data.get("caption_prompts", {})
            library.hook_prompts = data.get("hook_prompts", {})

        return library

    def get_scene(self, theme: str) -> SceneTemplate | None:
        """Get a scene template by theme name."""
        matches = [s for s in self.scenes if s.name == theme]
        return matches[0] if matches else None

    def get_random_scene(self, theme: str | None = None) -> SceneTemplate | None:
        """Get a random scene, optionally filtered by theme prefix."""
        if theme:
            matches = [s for s in self.scenes if s.name.startswith(theme)]
        else:
            matches = self.scenes
        return random.choice(matches) if matches else None

    def render_image_prompt(
        self,
        scene: SceneTemplate,
        character: GemmaPark | None = None,
    ) -> str:
        """Render a full image generation prompt combining character and scene."""
        char = character or get_character()
        char_prompt = char.to_image_prompt(
            scene=scene.prompt,
            outfit_type=scene.outfit_type,
        )
        lighting = f"Lighting: {scene.lighting}."
        return f"{char_prompt} {lighting}"

    def get_caption_system_prompt(self, theme: str) -> str | None:
        """Get the caption generation system prompt for a theme."""
        return self.caption_prompts.get(theme)

    def get_hooks(self, audience: str = "cold") -> list[str]:
        """Get hook templates for a given audience type."""
        return self.hook_prompts.get(audience, [])
