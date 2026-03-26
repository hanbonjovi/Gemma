"""Abstract base class for image generation engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ImageGenerator(ABC):
    """Base interface for all image generation engines."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        reference_image: str | Path | None = None,
        output_path: str | Path | None = None,
        aspect_ratio: str = "1:1",
    ) -> Path:
        """Generate a single image from a prompt.

        Args:
            prompt: Text prompt describing the desired image.
            reference_image: Path or URL to a reference image for character consistency.
            output_path: Where to save the generated image. Auto-generated if None.
            aspect_ratio: Aspect ratio (1:1, 4:5, 9:16 for stories).

        Returns:
            Path to the generated image file.
        """

    @abstractmethod
    async def generate_variations(
        self,
        base_image: str | Path,
        prompts: list[str],
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """Generate multiple variations of a character in different scenes.

        Args:
            base_image: Reference image for character consistency.
            prompts: List of scene prompts to place the character in.
            output_dir: Directory to save generated images.

        Returns:
            List of paths to generated images.
        """

    @abstractmethod
    async def generate_text_overlay(
        self,
        text: str,
        background_prompt: str,
        output_path: str | Path | None = None,
    ) -> Path:
        """Generate an image with text overlay (for motivational quotes).

        Args:
            text: The quote or text to render in the image.
            background_prompt: Prompt for the background scene.
            output_path: Where to save the generated image.

        Returns:
            Path to the generated image file.
        """
