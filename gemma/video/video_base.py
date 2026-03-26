"""Abstract base class for video generation engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VideoGenerator(ABC):
    """Base interface for video generation (character swap and image-to-video)."""

    @abstractmethod
    async def character_swap(
        self,
        character_image: str | Path,
        broll_video: str | Path,
        output_path: str | Path | None = None,
    ) -> Path:
        """Swap a character onto existing b-roll footage.

        Args:
            character_image: Reference image of the AI character.
            broll_video: Path to the b-roll video with real person movement.
            output_path: Where to save the output video.

        Returns:
            Path to the generated video with swapped character.
        """

    @abstractmethod
    async def image_to_video(
        self,
        image: str | Path,
        motion_prompt: str,
        duration: int = 5,
        output_path: str | Path | None = None,
    ) -> Path:
        """Animate a static image into a short video clip.

        Args:
            image: Path to the character image to animate.
            motion_prompt: Description of the desired motion.
            duration: Video duration in seconds.
            output_path: Where to save the output video.

        Returns:
            Path to the generated video.
        """
