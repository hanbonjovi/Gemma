"""Post model — represents a complete Instagram post with all its components."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4


class PostStatus(str, Enum):
    PLANNED = "planned"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    POSTED = "posted"


@dataclass
class Post:
    """A complete Instagram post ready for publishing."""

    id: str = field(default_factory=lambda: uuid4().hex[:12])
    theme: str = ""
    format: str = "image"  # image, carousel, reel, story
    media_paths: list[str] = field(default_factory=list)
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    hook_text: str | None = None  # For reels — on-screen text
    scheduled_time: str = ""  # ISO format
    status: str = PostStatus.PLANNED.value
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Post:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, output_dir: str | Path) -> Path:
        """Save the post to a directory with all its components."""
        post_dir = Path(output_dir) / self.id
        post_dir.mkdir(parents=True, exist_ok=True)

        # Save caption
        caption_file = post_dir / "caption.txt"
        caption_file.write_text(self.caption)

        # Save hashtags
        if self.hashtags:
            hashtags_file = post_dir / "hashtags.txt"
            hashtags_file.write_text(" ".join(self.hashtags))

        # Save hook text for reels
        if self.hook_text:
            hook_file = post_dir / "hook.txt"
            hook_file.write_text(self.hook_text)

        # Save metadata
        meta_file = post_dir / "metadata.json"
        meta_file.write_text(json.dumps(self.to_dict(), indent=2))

        return post_dir

    @classmethod
    def load(cls, post_dir: str | Path) -> Post:
        """Load a post from a directory."""
        meta_file = Path(post_dir) / "metadata.json"
        if not meta_file.exists():
            raise FileNotFoundError(f"No metadata.json in {post_dir}")
        data = json.loads(meta_file.read_text())
        return cls.from_dict(data)

    @property
    def caption_with_hashtags(self) -> str:
        """Full caption with hashtags appended."""
        if self.hashtags:
            return f"{self.caption}\n\n{'  '.join(self.hashtags)}"
        return self.caption

    @property
    def is_reel(self) -> bool:
        return self.format == "reel"

    @property
    def is_carousel(self) -> bool:
        return self.format == "carousel"
