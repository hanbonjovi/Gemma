"""Wan-Animate video generator — free/open-source character swap engine.

Wan-Animate (Wan 2.2 Animate) by Tongyi Lab provides:
- Move Mode: Makes a character image come alive following a reference video
- Mix Mode: Replaces a person in video while preserving movements & expressions
- Open source, available via Replicate API or self-hosted
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from gemma.config import Config
from gemma.video.video_base import VideoGenerator


class WanAnimateGenerator(VideoGenerator):
    """Generate videos using Wan-Animate via Replicate API.

    Cost: ~$0.05/video via Replicate, or free if self-hosted.
    """

    # Replicate model identifiers
    MOVE_MODEL = "wan-ai/wan-2.2-animate"
    MIX_MODEL = "wan-ai/wan-2.2-animate"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.api_token = config.video.replicate_api_token
        self.output_dir = config.output_dir / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_token:
            raise ValueError(
                "REPLICATE_API_TOKEN is required for Wan-Animate. "
                "Get one at https://replicate.com/account/api-tokens"
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

    def _output_path(self, prefix: str = "wan") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}_{uuid4().hex[:6]}.mp4"

    async def character_swap(
        self,
        character_image: str | Path,
        broll_video: str | Path,
        output_path: str | Path | None = None,
    ) -> Path:
        """Swap Gemma's face/body onto b-roll footage using Mix Mode.

        The real person's movement becomes Gemma's movement while
        preserving the original video's motion, expressions, and lighting.
        """
        out = Path(output_path) if output_path else self._output_path("swap")

        # Prepare file URLs (Replicate needs URLs or base64)
        char_url = self._prepare_input(character_image)
        video_url = self._prepare_input(broll_video)

        input_data = {
            "image": char_url,
            "video": video_url,
            "mode": "mix",  # Mix mode for character replacement
        }

        result_url = await self._run_prediction(input_data)
        await self._download_output(result_url, out)
        return out

    async def image_to_video(
        self,
        image: str | Path,
        motion_prompt: str,
        duration: int = 5,
        output_path: str | Path | None = None,
    ) -> Path:
        """Animate Gemma's static image using Move Mode.

        Makes the character image come alive by following a motion description.
        """
        out = Path(output_path) if output_path else self._output_path("move")

        image_url = self._prepare_input(image)

        input_data = {
            "image": image_url,
            "prompt": motion_prompt,
            "mode": "move",
            "num_frames": duration * 24,  # 24 fps
        }

        result_url = await self._run_prediction(input_data)
        await self._download_output(result_url, out)
        return out

    def _prepare_input(self, file_path: str | Path) -> str:
        """Prepare a file path as a URL for the Replicate API."""
        path_str = str(file_path)
        if path_str.startswith(("http://", "https://")):
            return path_str

        # For local files, we need to upload to Replicate first
        # or use base64 data URI
        import base64

        path = Path(file_path)
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode()

        suffix = path.suffix.lower()
        if suffix in (".mp4", ".mov", ".avi"):
            mime = "video/mp4"
        elif suffix in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        else:
            mime = "image/png"

        return f"data:{mime};base64,{b64}"

    async def _run_prediction(self, input_data: dict) -> str:
        """Run a prediction on Replicate and return the output URL."""
        async with httpx.AsyncClient(timeout=300) as client:
            # Create prediction
            response = await client.post(
                f"https://api.replicate.com/v1/models/{self.MOVE_MODEL}/predictions",
                headers=self._headers(),
                json={"input": input_data},
            )
            response.raise_for_status()
            result = response.json()

            # Check for immediate output (wait preference)
            output_url = result.get("output")
            if output_url:
                return output_url[0] if isinstance(output_url, list) else output_url

            # Poll for completion
            poll_url = result.get("urls", {}).get("get")
            if not poll_url:
                raise RuntimeError(f"No poll URL from Replicate: {result}")

            return await self._poll_prediction(client, poll_url)

    async def _poll_prediction(
        self, client: httpx.AsyncClient, poll_url: str, max_wait: int = 600
    ) -> str:
        """Poll until the prediction completes (video gen can take a few minutes)."""
        for _ in range(max_wait // 5):
            await asyncio.sleep(5)
            resp = await client.get(poll_url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

            if data["status"] == "succeeded":
                output = data.get("output")
                if output:
                    return output[0] if isinstance(output, list) else output
                raise RuntimeError("Prediction succeeded but no output URL")

            if data["status"] == "failed":
                raise RuntimeError(
                    f"Wan-Animate prediction failed: {data.get('error')}"
                )

        raise TimeoutError("Wan-Animate prediction timed out")

    async def _download_output(self, url: str, output_path: Path) -> None:
        """Download the generated video to a local file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
