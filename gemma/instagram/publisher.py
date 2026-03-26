"""Instagram Graph API publisher — handles posting content to Instagram.

Phase 1: Export content to folder for manual posting.
Phase 2: Automated posting via Instagram Graph API.

Requirements for API posting:
- Facebook Page connected to Instagram Business/Creator account
- Meta App with instagram_basic, instagram_content_publish permissions
- Valid access token
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import httpx

from gemma.config import Config
from gemma.content.post import Post, PostStatus


class ManualPublisher:
    """Export posts to a folder structure for manual Instagram posting.

    Output structure:
    assets/output/posts/{post_id}/
    ├── image_001.png (or video.mp4)
    ├── caption.txt
    ├── hashtags.txt
    ├── hook.txt (for reels)
    └── metadata.json
    """

    def __init__(self, config: Config) -> None:
        self.output_dir = config.output_dir / "posts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_post(self, post: Post) -> Path:
        """Export a post to the output directory for manual posting."""
        post_dir = post.save(self.output_dir)

        # Copy media files to the post directory
        for i, media_path in enumerate(post.media_paths):
            src = Path(media_path)
            if src.exists():
                suffix = src.suffix
                dst = post_dir / f"media_{i:03d}{suffix}"
                shutil.copy2(src, dst)

        # Create a README for easy reference
        readme = post_dir / "POST_INSTRUCTIONS.txt"
        readme.write_text(self._format_instructions(post))

        return post_dir

    def export_batch(self, posts: list[Post]) -> list[Path]:
        """Export multiple posts."""
        return [self.export_post(p) for p in posts]

    def _format_instructions(self, post: Post) -> str:
        """Create human-readable posting instructions."""
        lines = [
            f"=== Gemma Park — Instagram Post ===",
            f"Theme: {post.metadata.get('display_name', post.theme)}",
            f"Format: {post.format}",
            f"Scheduled: {post.scheduled_time}",
            "",
            "=== CAPTION (copy this) ===",
            post.caption,
            "",
        ]
        if post.hashtags:
            lines.extend([
                "=== HASHTAGS (paste as first comment) ===",
                " ".join(post.hashtags),
                "",
            ])
        if post.hook_text:
            lines.extend([
                "=== HOOK TEXT (add as on-screen text for Reel) ===",
                post.hook_text,
                "",
            ])
        lines.extend([
            "=== POSTING INSTRUCTIONS ===",
            f"1. Open Instagram and create a new {'Reel' if post.is_reel else 'Post'}",
            "2. Select the media file(s) from this folder",
        ])
        if post.is_reel and post.hook_text:
            lines.append(f"3. Add hook text as on-screen text: \"{post.hook_text}\"")
        lines.extend([
            f"{'4' if post.hook_text else '3'}. Paste the caption from caption.txt",
            f"{'5' if post.hook_text else '4'}. Post hashtags as the first comment",
            f"{'6' if post.hook_text else '5'}. Post!",
        ])
        return "\n".join(lines)


class InstagramPublisher:
    """Publish posts directly to Instagram via the Graph API.

    Requires Instagram Business/Creator account connected to a Facebook Page
    and a Meta App with appropriate permissions.
    """

    GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.access_token = config.instagram.access_token
        self.ig_account_id = config.instagram.business_account_id

        if not self.access_token or not self.ig_account_id:
            raise ValueError(
                "Instagram API requires INSTAGRAM_ACCESS_TOKEN and "
                "INSTAGRAM_BUSINESS_ACCOUNT_ID. Set them in .env"
            )

    async def publish_image(self, post: Post) -> str:
        """Publish a single image post to Instagram.

        Returns the published media ID.
        """
        if not post.media_paths:
            raise ValueError("Post has no media files")

        image_url = post.media_paths[0]  # Must be a public URL for Graph API

        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Create media container
            container_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media",
                params={
                    "image_url": image_url,
                    "caption": post.caption_with_hashtags,
                    "access_token": self.access_token,
                },
            )
            container_resp.raise_for_status()
            container_id = container_resp.json()["id"]

            # Step 2: Publish the container
            publish_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]

        post.status = PostStatus.POSTED.value
        return media_id

    async def publish_carousel(self, post: Post) -> str:
        """Publish a carousel (multi-image) post to Instagram."""
        if len(post.media_paths) < 2:
            raise ValueError("Carousel requires at least 2 media items")

        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Create individual item containers
            item_ids = []
            for media_url in post.media_paths:
                resp = await client.post(
                    f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media",
                    params={
                        "image_url": media_url,
                        "is_carousel_item": "true",
                        "access_token": self.access_token,
                    },
                )
                resp.raise_for_status()
                item_ids.append(resp.json()["id"])

            # Step 2: Create carousel container
            carousel_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media",
                params={
                    "media_type": "CAROUSEL",
                    "children": ",".join(item_ids),
                    "caption": post.caption_with_hashtags,
                    "access_token": self.access_token,
                },
            )
            carousel_resp.raise_for_status()
            carousel_id = carousel_resp.json()["id"]

            # Step 3: Publish
            publish_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media_publish",
                params={
                    "creation_id": carousel_id,
                    "access_token": self.access_token,
                },
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]

        post.status = PostStatus.POSTED.value
        return media_id

    async def publish_reel(self, post: Post) -> str:
        """Publish a reel (video) to Instagram."""
        if not post.media_paths:
            raise ValueError("Reel requires a video file")

        video_url = post.media_paths[0]  # Must be a public URL

        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: Create reel container
            container_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": post.caption_with_hashtags,
                    "access_token": self.access_token,
                },
            )
            container_resp.raise_for_status()
            container_id = container_resp.json()["id"]

            # Step 2: Wait for video processing, then publish
            publish_resp = await client.post(
                f"{self.GRAPH_API_BASE}/{self.ig_account_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]

        post.status = PostStatus.POSTED.value
        return media_id

    async def publish(self, post: Post) -> str:
        """Publish a post using the appropriate method based on format."""
        if post.is_carousel:
            return await self.publish_carousel(post)
        elif post.is_reel:
            return await self.publish_reel(post)
        else:
            return await self.publish_image(post)
