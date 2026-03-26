"""Google Nano Banana 2 image generator — secondary engine with free tier."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from gemma.config import Config
from gemma.generators.image_base import ImageGenerator


class NanoBananaGenerator(ImageGenerator):
    """Generate images using Google's Nano Banana 2 via the Gemini API.

    Nano Banana 2 excels at:
    - Text rendering in images (motivational quotes)
    - Character consistency for up to 5 characters
    - Photorealistic faces
    - Free tier available via Gemini API
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.api_key = config.image.google_api_key
        self.output_dir = config.output_dir / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required for Nano Banana 2. "
                "Get one at https://aistudio.google.com/apikey"
            )

    def _output_path(self, prefix: str = "nanob") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{prefix}_{timestamp}_{uuid4().hex[:6]}.png"

    async def generate(
        self,
        prompt: str,
        reference_image: str | Path | None = None,
        output_path: str | Path | None = None,
        aspect_ratio: str = "1:1",
    ) -> Path:
        """Generate an image using Nano Banana 2 via the Gemini API."""
        from google import genai
        from google.genai import types

        out = Path(output_path) if output_path else self._output_path()

        client = genai.Client(api_key=self.api_key)

        # Build the content parts
        contents: list = []

        # If reference image provided, include it for character consistency
        if reference_image:
            ref_path = Path(reference_image)
            if ref_path.exists():
                ref_bytes = ref_path.read_bytes()
                ref_part = types.Part.from_bytes(
                    data=ref_bytes,
                    mime_type="image/png",
                )
                contents.append(ref_part)
                contents.append(
                    f"Using the person in the reference image above, generate: {prompt}"
                )
            else:
                contents.append(prompt)
        else:
            contents.append(prompt)

        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        # Extract the generated image from the response
        image_saved = False
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(image_data)
                image_saved = True
                break

        if not image_saved:
            raise RuntimeError(
                "Nano Banana 2 did not return an image. "
                "Response may have been filtered or the prompt needs adjustment."
            )

        return out

    async def generate_variations(
        self,
        base_image: str | Path,
        prompts: list[str],
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """Generate multiple variations using the same reference image."""
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
        """Generate an image with text overlay — Nano Banana 2 excels at this."""
        prompt = (
            f"{background_prompt}. "
            f'The image contains bold, clean typography that reads: "{text}". '
            "The text is large, white, centered, and highly readable against the "
            "background. Professional motivational poster aesthetic."
        )
        return await self.generate(prompt=prompt, output_path=output_path)
