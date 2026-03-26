"""LLM-powered caption generator — writes Instagram captions in Gemma's voice."""

from __future__ import annotations

from dataclasses import dataclass

from gemma.config import Config
from gemma.persona.character import GemmaPark, get_character
from gemma.persona.voice import VoiceGuide, get_voice_guide


@dataclass
class GeneratedCaption:
    caption: str
    hashtags: list[str]
    theme: str
    hook: str | None = None


class CaptionGenerator:
    """Generate Instagram captions using an LLM in Gemma's voice."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.character = get_character()
        self.voice = get_voice_guide()
        self.provider = config.llm.default_provider

    def _build_system_prompt(self) -> str:
        """Build the full system prompt combining character + voice guide."""
        return (
            self.character.to_system_prompt()
            + "\n"
            + self.voice.to_prompt_instructions()
        )

    async def generate(
        self,
        theme: str,
        context: str = "",
        image_description: str = "",
        max_length: int = 2200,
    ) -> GeneratedCaption:
        """Generate a caption for a given content theme.

        Args:
            theme: Content theme (motivation, trail_run, training_log, etc.)
            context: Additional context for the caption.
            image_description: Description of the image being captioned.
            max_length: Maximum caption length (Instagram limit is 2200).

        Returns:
            GeneratedCaption with text, hashtags, and metadata.
        """
        structure = self.voice.get_structure(theme)
        example = self.voice.get_example(theme)

        user_prompt = self._build_user_prompt(
            theme=theme,
            structure=structure,
            example=example,
            context=context,
            image_description=image_description,
            max_length=max_length,
        )

        if self.provider == "anthropic":
            text = await self._generate_anthropic(user_prompt)
        elif self.provider == "openai":
            text = await self._generate_openai(user_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        caption, hashtags = self._parse_response(text)

        return GeneratedCaption(
            caption=caption,
            hashtags=hashtags,
            theme=theme,
        )

    def _build_user_prompt(
        self,
        theme: str,
        structure: str,
        example: str | None,
        context: str,
        image_description: str,
        max_length: int,
    ) -> str:
        parts = [
            f"Write an Instagram caption for a '{theme.replace('_', ' ')}' post.",
            f"\nCaption structure to follow:\n{structure}",
        ]
        if example:
            parts.append(f"\nExample of a similar caption (for tone reference, don't copy):\n{example}")
        if image_description:
            parts.append(f"\nThe image shows: {image_description}")
        if context:
            parts.append(f"\nAdditional context: {context}")
        parts.append(
            f"\nKeep the caption under {max_length} characters."
            "\n\nAfter the caption, on a new line starting with 'HASHTAGS:', "
            "list 20-25 relevant hashtags separated by spaces."
        )
        return "\n".join(parts)

    async def _generate_anthropic(self, user_prompt: str) -> str:
        """Generate using Claude API."""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.config.llm.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self._build_system_prompt(),
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    async def _generate_openai(self, user_prompt: str) -> str:
        """Generate using OpenAI API."""
        import openai

        client = openai.AsyncOpenAI(api_key=self.config.llm.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _parse_response(self, text: str) -> tuple[str, list[str]]:
        """Parse LLM response into caption text and hashtags."""
        hashtags: list[str] = []
        caption = text

        # Split on HASHTAGS: line
        if "HASHTAGS:" in text:
            parts = text.split("HASHTAGS:", 1)
            caption = parts[0].strip()
            hashtag_text = parts[1].strip()
            hashtags = [
                tag if tag.startswith("#") else f"#{tag}"
                for tag in hashtag_text.split()
                if tag.strip()
            ]

        return caption, hashtags

    async def generate_batch(
        self,
        themes: list[str],
        contexts: list[str] | None = None,
    ) -> list[GeneratedCaption]:
        """Generate captions for multiple themes."""
        contexts = contexts or [""] * len(themes)
        results = []
        for theme, context in zip(themes, contexts):
            caption = await self.generate(theme=theme, context=context)
            results.append(caption)
        return results
