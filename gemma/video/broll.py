"""B-roll footage management — catalog and organize motion template clips."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class BRollClip:
    """A b-roll video clip used as a motion template for character swap."""

    filename: str
    category: str  # trail_running, road_running, gym, stretching, race, recovery
    description: str
    duration_seconds: float = 0
    framing: str = "medium"  # close-up, medium, wide, aerial
    motion_type: str = "running"  # running, walking, stretching, standing, sitting
    terrain: str = ""  # trail, road, treadmill, gym
    lighting: str = "natural"  # natural, golden_hour, overcast, gym_lighting
    tags: list[str] = field(default_factory=list)
    used_count: int = 0


class BRollLibrary:
    """Manage a catalog of b-roll footage for character swap videos.

    Users download real running clips from TikTok/Instagram/YouTube as
    motion templates. This library tracks metadata for each clip so the
    pipeline can select appropriate footage for each content theme.
    """

    def __init__(self, broll_dir: str | Path = "./assets/broll") -> None:
        self.broll_dir = Path(broll_dir)
        self.broll_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.broll_dir / "catalog.json"
        self.clips: list[BRollClip] = []
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Load the b-roll catalog from disk."""
        if self.catalog_path.exists():
            data = json.loads(self.catalog_path.read_text())
            self.clips = [BRollClip(**clip) for clip in data]

    def save_catalog(self) -> None:
        """Save the b-roll catalog to disk."""
        data = [asdict(clip) for clip in self.clips]
        self.catalog_path.write_text(json.dumps(data, indent=2))

    def add_clip(self, clip: BRollClip) -> None:
        """Add a new b-roll clip to the catalog."""
        # Verify the file exists
        clip_path = self.broll_dir / clip.filename
        if not clip_path.exists():
            raise FileNotFoundError(
                f"B-roll file not found: {clip_path}. "
                f"Place the video file in {self.broll_dir}/"
            )
        self.clips.append(clip)
        self.save_catalog()

    def get_by_category(self, category: str) -> list[BRollClip]:
        """Get clips matching a category."""
        return [c for c in self.clips if c.category == category]

    def get_by_motion(self, motion_type: str) -> list[BRollClip]:
        """Get clips matching a motion type."""
        return [c for c in self.clips if c.motion_type == motion_type]

    def get_best_match(
        self,
        category: str | None = None,
        motion_type: str | None = None,
        framing: str | None = None,
        least_used: bool = True,
    ) -> BRollClip | None:
        """Find the best matching b-roll clip, preferring least-used ones."""
        candidates = list(self.clips)

        if category:
            candidates = [c for c in candidates if c.category == category]
        if motion_type:
            candidates = [c for c in candidates if c.motion_type == motion_type]
        if framing:
            candidates = [c for c in candidates if c.framing == framing]

        if not candidates:
            return None

        if least_used:
            candidates.sort(key=lambda c: c.used_count)

        return candidates[0]

    def mark_used(self, clip: BRollClip) -> None:
        """Increment the usage count for a clip."""
        clip.used_count += 1
        self.save_catalog()

    def list_clips(self) -> list[dict]:
        """List all clips with their metadata."""
        return [
            {
                "filename": c.filename,
                "category": c.category,
                "description": c.description,
                "framing": c.framing,
                "motion": c.motion_type,
                "used": c.used_count,
            }
            for c in self.clips
        ]

    def get_categories(self) -> list[str]:
        """Get all unique categories in the library."""
        return sorted(set(c.category for c in self.clips))

    @property
    def clip_count(self) -> int:
        return len(self.clips)
