"""HeyGen video generator — alternative engine for talking-head content.

HeyGen excels at:
- Avatar-based video with lip sync
- Talking-head content (running tips, gear reviews)
- 1,100+ avatars, 175 languages
- API starts at $5, full plan $29/mo
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from gemma.config import Config
from gemma.video.video_base import VideoGenerator


class HeyGenGenerator(VideoGenerator):
    """Generate talking-head videos using HeyGen API.

    Best for when Gemma needs to "speak to camera" — running tips,
    gear reviews, motivational speeches, Q&A responses.
    """

    API_BASE = "https://api.heygen.com/v2"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.api_key = config.video.heygen_api_key
        self.output_dir = config.output_dir / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            raise ValueError(
                "HEYGEN_API_KEY is required. "
                "Get one at https://app.heygen.com/settings/api"
            )

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _output_path(self, prefix: str = "heygen") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}_{uuid4().hex[:6]}.mp4"

    async def character_swap(
        self,
        character_image: str | Path,
        broll_video: str | Path,
        output_path: str | Path | None = None,
    ) -> Path:
        """Character swap via HeyGen's face swap feature."""
        raise NotImplementedError(
            "HeyGen is best for talking-head content. "
            "Use Wan-Animate for character swap on b-roll footage."
        )

    async def image_to_video(
        self,
        image: str | Path,
        motion_prompt: str,
        duration: int = 5,
        output_path: str | Path | None = None,
    ) -> Path:
        """Create a talking-head video from an image and script."""
        raise NotImplementedError(
            "Use create_talking_head() for HeyGen video generation."
        )

    async def create_talking_head(
        self,
        avatar_image: str | Path,
        script: str,
        voice_id: str = "en-US-female-mature",
        output_path: str | Path | None = None,
    ) -> Path:
        """Create a talking-head video where Gemma speaks to camera.

        Args:
            avatar_image: Reference photo of Gemma.
            script: What Gemma says in the video.
            voice_id: Voice to use for text-to-speech.
            output_path: Where to save the output video.

        Returns:
            Path to the generated video.
        """
        out = Path(output_path) if output_path else self._output_path()

        # Upload the avatar image first
        photo_url = await self._upload_photo(avatar_image)

        # Create the video
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "photo_avatar",
                        "photo_url": photo_url,
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id,
                    },
                }
            ],
            "dimension": {"width": 1080, "height": 1920},  # 9:16 for Reels
        }

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self.API_BASE}/video/generate",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            video_id = result["data"]["video_id"]

            # Poll for completion
            video_url = await self._poll_video(client, video_id)

            # Download the video
            video_resp = await client.get(video_url)
            video_resp.raise_for_status()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(video_resp.content)

        return out

    async def _upload_photo(self, image_path: str | Path) -> str:
        """Upload a photo to HeyGen and return the URL."""
        path = Path(image_path)
        if str(image_path).startswith(("http://", "https://")):
            return str(image_path)

        async with httpx.AsyncClient(timeout=60) as client:
            with open(path, "rb") as f:
                response = await client.post(
                    f"{self.API_BASE}/photo_avatar/upload",
                    headers={"X-Api-Key": self.api_key},
                    files={"file": (path.name, f, "image/png")},
                )
            response.raise_for_status()
            return response.json()["data"]["url"]

    async def _poll_video(
        self, client: httpx.AsyncClient, video_id: str, max_wait: int = 600
    ) -> str:
        """Poll until video generation completes."""
        for _ in range(max_wait // 5):
            await asyncio.sleep(5)
            resp = await client.get(
                f"{self.API_BASE}/video_status.get",
                headers=self._headers(),
                params={"video_id": video_id},
            )
            resp.raise_for_status()
            data = resp.json()["data"]

            if data["status"] == "completed":
                return data["video_url"]
            if data["status"] == "failed":
                raise RuntimeError(f"HeyGen video generation failed: {data.get('error')}")

        raise TimeoutError("HeyGen video generation timed out")
