"""Full content pipeline orchestrator — chains all generation steps together."""

from __future__ import annotations

import random
from datetime import date, datetime
from pathlib import Path

from gemma.config import Config
from gemma.content.calendar import ContentCalendar
from gemma.content.post import Post, PostStatus
from gemma.content.themes import ContentFormat, ContentTheme, get_theme_by_name, get_theme_for_day
from gemma.generators.caption import CaptionGenerator
from gemma.generators.hooks import HookGenerator
from gemma.generators.prompts import PromptLibrary
from gemma.instagram.hashtags import HashtagManager
from gemma.instagram.publisher import ManualPublisher
from gemma.persona.character import get_character


class ContentPipeline:
    """Orchestrates the full content generation pipeline.

    Flow:
    1. Check content calendar for today's theme
    2. Generate image prompts or video hooks/scripts
    3. Call image generator (FLUX/Nano Banana) or video generator (Wan-Animate)
    4. Generate caption + hashtags via LLM
    5. Package into a Post object
    6. Export to output folder for manual posting (or auto-post via API)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.character = get_character()
        self.caption_gen = CaptionGenerator(config)
        self.hook_gen = HookGenerator(config)
        self.hashtag_mgr = HashtagManager()
        self.prompt_lib = PromptLibrary.load()
        self.calendar = ContentCalendar()
        self.publisher = ManualPublisher(config)
        self._image_gen = None
        self._video_gen = None

    def _get_image_generator(self):
        """Lazy-load the configured image generator."""
        if self._image_gen is None:
            engine = self.config.image.default_engine
            if engine == "flux_kontext":
                from gemma.generators.flux_kontext import FluxKontextGenerator
                self._image_gen = FluxKontextGenerator(self.config)
            elif engine == "nano_banana":
                from gemma.generators.nano_banana import NanoBananaGenerator
                self._image_gen = NanoBananaGenerator(self.config)
            else:
                raise ValueError(f"Unknown image engine: {engine}")
        return self._image_gen

    def _get_video_generator(self):
        """Lazy-load the video generator."""
        if self._video_gen is None:
            from gemma.video.wan_animate import WanAnimateGenerator
            self._video_gen = WanAnimateGenerator(self.config)
        return self._video_gen

    async def generate_image_post(
        self,
        theme: ContentTheme,
        reference_image: str | Path | None = None,
    ) -> Post:
        """Generate a complete image post (image + caption + hashtags)."""
        image_gen = self._get_image_generator()

        # Build the image prompt
        scene = self.prompt_lib.get_random_scene(theme.name.split("_")[0])
        if scene:
            prompt = self.prompt_lib.render_image_prompt(scene)
        else:
            keyword = random.choice(theme.scene_keywords) if theme.scene_keywords else "trail running"
            prompt = self.character.to_image_prompt(
                scene=f"Photorealistic scene: {keyword}. Pacific Northwest setting.",
                outfit_type=theme.outfit_type,
            )

        # Generate the image
        image_path = await image_gen.generate(
            prompt=prompt,
            reference_image=reference_image,
            aspect_ratio="4:5",  # Instagram portrait
        )

        # Generate caption
        caption_result = await self.caption_gen.generate(
            theme=theme.caption_theme,
            image_description=prompt,
        )

        # Generate hashtags
        hashtags = self.hashtag_mgr.generate(theme=theme.caption_theme)

        # Create post
        post = Post(
            theme=theme.name,
            format=ContentFormat.IMAGE.value,
            media_paths=[str(image_path)],
            caption=caption_result.caption,
            hashtags=hashtags,
            status=PostStatus.GENERATED.value,
            scheduled_time=datetime.now().isoformat(),
            metadata={
                "display_name": theme.display_name,
                "image_prompt": prompt,
                "engine": self.config.image.default_engine,
            },
        )

        return post

    async def generate_reel_post(
        self,
        theme: ContentTheme,
        reference_image: str | Path | None = None,
        broll_video: str | Path | None = None,
    ) -> Post:
        """Generate a complete reel post (hook + video + caption)."""
        # Generate hooks
        hooks = await self.hook_gen.generate_hooks(
            theme=theme.caption_theme,
            audience="cold",
            count=3,
        )

        if not hooks:
            raise RuntimeError("Failed to generate hooks")

        # Pick the best hook (first one) and generate a script
        hook = hooks[0]
        hook = await self.hook_gen.generate_script(hook)

        # Generate video if b-roll is provided
        video_path = None
        if broll_video and reference_image:
            video_gen = self._get_video_generator()
            video_path = await video_gen.character_swap(
                character_image=reference_image,
                broll_video=broll_video,
            )
        elif reference_image:
            video_gen = self._get_video_generator()
            motion = random.choice(theme.scene_keywords) if theme.scene_keywords else "running on trail"
            video_path = await video_gen.image_to_video(
                image=reference_image,
                motion_prompt=f"Woman {motion}, dynamic movement, cinematic",
            )

        # Generate caption
        caption_result = await self.caption_gen.generate(
            theme=theme.caption_theme,
            context=f"Reel hook: {hook.text}",
        )

        # Generate hashtags
        hashtags = self.hashtag_mgr.generate(theme=theme.caption_theme)

        post = Post(
            theme=theme.name,
            format=ContentFormat.REEL.value,
            media_paths=[str(video_path)] if video_path else [],
            caption=caption_result.caption,
            hashtags=hashtags,
            hook_text=hook.text,
            status=PostStatus.GENERATED.value,
            scheduled_time=datetime.now().isoformat(),
            metadata={
                "display_name": theme.display_name,
                "hook": hook.text,
                "script": hook.script,
                "scene_descriptions": hook.scene_descriptions,
            },
        )

        return post

    async def generate_daily_content(
        self,
        target_date: date | None = None,
        reference_image: str | Path | None = None,
    ) -> list[Post]:
        """Generate all content for a single day based on the calendar."""
        target = target_date or date.today()
        theme = get_theme_for_day(target.weekday())
        posts: list[Post] = []

        # Generate primary post
        primary_format = theme.formats[0]
        if primary_format == ContentFormat.REEL:
            post = await self.generate_reel_post(theme, reference_image)
        else:
            post = await self.generate_image_post(theme, reference_image)
        posts.append(post)

        # Export for manual posting
        for post in posts:
            self.publisher.export_post(post)

        return posts

    async def generate_weekly_content(
        self,
        start_date: date | None = None,
        reference_image: str | Path | None = None,
    ) -> list[Post]:
        """Generate a full week of content."""
        from datetime import timedelta

        start = start_date or date.today()
        start = start - timedelta(days=start.weekday())  # Adjust to Monday

        all_posts: list[Post] = []
        for day_offset in range(7):
            current = start + timedelta(days=day_offset)
            posts = await self.generate_daily_content(current, reference_image)
            all_posts.extend(posts)

        return all_posts

    async def dry_run(
        self,
        theme_name: str | None = None,
        target_date: date | None = None,
    ) -> dict:
        """Preview what would be generated without making API calls."""
        target = target_date or date.today()
        theme = get_theme_by_name(theme_name) if theme_name else get_theme_for_day(target.weekday())

        if not theme:
            raise ValueError(f"Unknown theme: {theme_name}")

        # Build the image prompt
        scene = self.prompt_lib.get_random_scene(theme.name.split("_")[0])
        if scene:
            prompt = self.prompt_lib.render_image_prompt(scene)
        else:
            keyword = random.choice(theme.scene_keywords) if theme.scene_keywords else "trail running"
            prompt = self.character.to_image_prompt(
                scene=f"Photorealistic scene: {keyword}. Pacific Northwest setting.",
                outfit_type=theme.outfit_type,
            )

        return {
            "date": target.isoformat(),
            "theme": theme.display_name,
            "format": theme.formats[0].value,
            "image_prompt": prompt,
            "caption_theme": theme.caption_theme,
            "hashtag_preview": self.hashtag_mgr.generate(theme.caption_theme),
            "engine": self.config.image.default_engine,
        }
