"""FLUX Kontext image generator — primary engine for character-consistent images."""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

from gemma.config import Config
from gemma.generators.image_base import ImageGenerator


class FluxKontextGenerator(ImageGenerator):
    """Generate images using FLUX Kontext via Replicate API.

    FLUX Kontext excels at maintaining character consistency across multiple
    scenes by using a reference image. It takes an input image and a text
    prompt, then generates a new image with the same character in a new scene.
    """

    REPLICATE_MODEL = "black-forest-labs/flux-kontext-pro"

    def __init__(self, config: Config) -> None:
        self.config = config
        self.api_token = config.image.replicate_api_token
        self.output_dir = config.output_dir / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_token:
            raise ValueError(
                "REPLICATE_API_TOKEN is required for FLUX Kontext. "
                "Get one at https://replicate.com/account/api-tokens"
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        }

    def _output_path(self, prefix: str = "flux") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}_{uuid4().hex[:6]}.png"

    async def _image_to_data_uri(self, image_path: str | Path) -> str:
        """Convert a local image file to a data URI for the API."""
        path = Path(image_path)
        if str(image_path).startswith(("http://", "https://")):
            return str(image_path)
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode()
        suffix = path.suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(
            suffix, "image/png"
        )
        return f"data:{mime};base64,{b64}"

    async def generate(
        self,
        prompt: str,
        reference_image: str | Path | None = None,
        output_path: str | Path | None = None,
        aspect_ratio: str = "1:1",
    ) -> Path:
        """Generate an image using FLUX Kontext.

        If a reference_image is provided, the character in the reference will be
        preserved in the new scene described by the prompt.
        """
        out = Path(output_path) if output_path else self._output_path()

        input_data: dict = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        if reference_image:
            input_data["image_url"] = await self._image_to_data_uri(reference_image)

        # Add LoRA if configured
        if self.config.image.lora_model_path:
            input_data["lora_url"] = self.config.image.lora_model_path
            input_data["lora_scale"] = self.config.image.lora_weight

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.replicate.com/v1/models/"
                f"{self.REPLICATE_MODEL}/predictions",
                headers=self._headers(),
                json={"input": input_data},
            )
            response.raise_for_status()
            result = response.json()

            # Poll for completion if not using wait preference
            output_url = result.get("output")
            if not output_url and result.get("urls", {}).get("get"):
                output_url = await self._poll_prediction(
                    client, result["urls"]["get"]
                )

            if not output_url:
                raise RuntimeError(f"No output from FLUX Kontext: {result}")

            # Handle output format (can be string URL or list)
            if isinstance(output_url, list):
                output_url = output_url[0]

            # Download the image
            img_response = await client.get(output_url)
            img_response.raise_for_status()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(img_response.content)

        return out

    async def _poll_prediction(
        self, client: httpx.AsyncClient, poll_url: str, max_wait: int = 300
    ) -> str | None:
        """Poll a Replicate prediction until it completes."""
        for _ in range(max_wait // 2):
            await asyncio.sleep(2)
            resp = await client.get(poll_url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            if data["status"] == "succeeded":
                output = data.get("output")
                return output[0] if isinstance(output, list) else output
            if data["status"] == "failed":
                raise RuntimeError(f"FLUX Kontext prediction failed: {data.get('error')}")
        raise TimeoutError("FLUX Kontext prediction timed out")

    async def generate_variations(
        self,
        base_image: str | Path,
        prompts: list[str],
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """Generate multiple scene variations with the same character."""
        results = []
        for i, prompt in enumerate(prompts):
            out_dir = Path(output_dir) if output_dir else self.output_dir
            out_path = out_dir / f"variation_{i:03d}.png"
            path = await self.generate(
                prompt=prompt,
                reference_image=base_image,
                output_path=out_path,
            )
            results.append(path)
        return results

    async def generate_text_overlay(
        self,
        text: str,
        background_prompt: str,
        output_path: str | Path | None = None,
    ) -> Path:
        """Generate an image with text — FLUX handles text rendering reasonably well."""
        prompt = (
            f'{background_prompt}. Bold white text overlay reading: "{text}". '
            "Clean typography, readable against background, motivational poster style."
        )
        return await self.generate(prompt=prompt, output_path=output_path)
