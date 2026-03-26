"""Hook & script generator for Instagram Reels — generates viral hooks and video scripts."""

from __future__ import annotations

from dataclasses import dataclass, field

from gemma.config import Config
from gemma.persona.character import get_character


@dataclass
class VideoHook:
    text: str
    audience: str  # cold, warm, hot
    theme: str
    script: str | None = None
    scene_descriptions: list[str] = field(default_factory=list)


class HookGenerator:
    """Generate viral hooks and video scripts for Instagram Reels.

    Inspired by the OpenClaw/Eddie pipeline — generates hooks at different
    audience awareness levels, then structures full scripts around them.
    """

    AUDIENCE_DESCRIPTIONS = {
        "cold": "They've never heard of you. Grab attention with a bold, unexpected claim.",
        "warm": "They know the problem (running pain, slow times) but not the solution. Show them the path.",
        "hot": "They're ready to follow/engage. Give them the exact answer or gear recommendation.",
    }

    def __init__(self, config: Config) -> None:
        self.config = config
        self.character = get_character()
        self.provider = config.llm.default_provider

    async def generate_hooks(
        self,
        theme: str,
        audience: str = "cold",
        count: int = 10,
    ) -> list[VideoHook]:
        """Generate multiple hook angles for a given theme and audience."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_hooks_prompt(theme, audience, count)

        if self.provider == "anthropic":
            text = await self._generate_anthropic(system_prompt, user_prompt)
        elif self.provider == "openai":
            text = await self._generate_openai(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        return self._parse_hooks(text, audience, theme)

    async def generate_script(self, hook: VideoHook) -> VideoHook:
        """Generate a full video script for a given hook."""
        system_prompt = self._build_system_prompt()
        user_prompt = (
            f"Write a 30-60 second Instagram Reel script for this hook:\n\n"
            f"Hook: \"{hook.text}\"\n"
            f"Audience: {hook.audience} ({self.AUDIENCE_DESCRIPTIONS[hook.audience]})\n"
            f"Theme: {hook.theme}\n\n"
            "Format the script as:\n"
            "HOOK (0-3s): [opening line + visual]\n"
            "STORY (3-20s): [the content + visuals]\n"
            "CTA (20-30s): [call to action + visual]\n\n"
            "For each section, include:\n"
            "1. What Gemma says (voiceover text)\n"
            "2. What the viewer sees (scene description for AI video generation)\n\n"
            "Keep it punchy. No fluff. Make every second count."
        )

        if self.provider == "anthropic":
            script_text = await self._generate_anthropic(system_prompt, user_prompt)
        else:
            script_text = await self._generate_openai(system_prompt, user_prompt)

        hook.script = script_text
        hook.scene_descriptions = self._extract_scenes(script_text)
        return hook

    def _build_system_prompt(self) -> str:
        return (
            f"You are a viral content strategist writing hooks and scripts for "
            f"{self.character.name}, a {self.character.age}-year-old "
            f"{self.character.ethnicity} ultra runner based in {self.character.location}.\n\n"
            f"Her vibe: David Goggins energy but warm and approachable. "
            f"Tough love, real talk, no BS motivation earned through miles.\n\n"
            f"She runs 70-90 miles/week, has completed Western States 100, UTMB, "
            f"and trains on Pacific Northwest trails.\n\n"
            f"Write hooks that are scroll-stopping and authentic to her voice. "
            f"No clickbait that doesn't deliver. Every hook must be backed by real content."
        )

    def _build_hooks_prompt(self, theme: str, audience: str, count: int) -> str:
        audience_desc = self.AUDIENCE_DESCRIPTIONS.get(audience, "General audience")
        return (
            f"Generate {count} Instagram Reel hook lines for the theme: '{theme}'\n\n"
            f"Target audience: {audience.upper()} — {audience_desc}\n\n"
            "Rules:\n"
            "- Each hook must be 1-2 sentences max\n"
            "- Must grab attention in under 3 seconds\n"
            "- Should feel authentic to an ultra runner, not generic fitness\n"
            "- Mix formats: bold claims, questions, contrarian takes, personal confessions\n"
            "- No cliches like 'you won't believe' or 'this changed my life'\n\n"
            f"Output exactly {count} hooks, one per line, numbered 1-{count}."
        )

    async def _generate_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.config.llm.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    async def _generate_openai(self, system_prompt: str, user_prompt: str) -> str:
        import openai

        client = openai.AsyncOpenAI(api_key=self.config.llm.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _parse_hooks(self, text: str, audience: str, theme: str) -> list[VideoHook]:
        """Parse numbered hook lines from LLM response."""
        hooks = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip numbering (1. or 1) prefix)
            cleaned = line.lstrip("0123456789.)- ").strip()
            if cleaned and len(cleaned) > 10:
                cleaned = cleaned.strip('"').strip("'")
                hooks.append(
                    VideoHook(text=cleaned, audience=audience, theme=theme)
                )
        return hooks

    def _extract_scenes(self, script: str) -> list[str]:
        """Extract scene descriptions from a generated script."""
        scenes = []
        for line in script.split("\n"):
            lower = line.lower().strip()
            if any(
                kw in lower
                for kw in ["viewer sees:", "visual:", "scene:", "shot:"]
            ):
                # Extract the description after the keyword
                for kw in ["viewer sees:", "visual:", "scene:", "shot:"]:
                    if kw in lower:
                        desc = line.split(":", 1)[-1].strip()
                        if desc:
                            scenes.append(desc)
                        break
        return scenes
