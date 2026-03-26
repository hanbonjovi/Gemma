"""Hashtag strategy — manages rotating hashtag sets to maximize reach."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class HashtagSet:
    name: str
    tags: list[str]


# Pre-defined hashtag pools organized by category
HIGH_VOLUME = [
    "#running", "#runnersofinstagram", "#trailrunning", "#ultrarunning",
    "#runningmotivation", "#marathon", "#runner", "#fitness",
    "#trailrun", "#instarunners", "#runhappy", "#fitnessmotivation",
]

MEDIUM_VOLUME = [
    "#ultrarunner", "#traillife", "#runnerlife", "#mountainrunning",
    "#trailrunner", "#runningcommunity", "#longrun", "#ultramarathon",
    "#trailrunninglife", "#runwild", "#dirtrunner", "#runfree",
]

NICHE = [
    "#femaleultrarunner", "#womenwhoultra", "#trailrunningwomen",
    "#womenrunners", "#sherunstrails", "#ultrawoman", "#trailsisters",
    "#womentrailrunners", "#runlikeagirl", "#strongwomen",
]

LOCATION = [
    "#pnwrunning", "#portlandrunner", "#oregontrails", "#pnwtrails",
    "#mounthood", "#forestpark", "#columbiarivergorge", "#cascadetrails",
    "#pacificnorthwest", "#oregonrunning",
]

BRANDED = [
    "#gemmapark", "#gemmaruns", "#parkitup", "#milesdonttlie",
    "#notrailnolife",
]

MOTIVATIONAL = [
    "#nevergiveup", "#mentaltoughness", "#goggins", "#noexcuses",
    "#embracethesuck", "#hardwork", "#discipline", "#grit",
]

GEAR_SPECIFIC = [
    "#salomon", "#hoka", "#niketrail", "#trailshoes", "#runninggear",
    "#hydrationvest", "#gearreview", "#runningshoes",
]


class HashtagManager:
    """Manages hashtag selection and rotation to avoid shadowbanning.

    Strategy:
    - Use 20-25 hashtags per post (Instagram sweet spot)
    - Mix high-volume, medium, niche, location, and branded tags
    - Rotate sets to avoid using identical combinations
    - Theme-specific tag selection
    """

    # Mapping content themes to relevant extra hashtag pools
    THEME_POOLS: dict[str, list[str]] = {
        "motivation": MOTIVATIONAL,
        "trail_run": LOCATION + NICHE,
        "training_log": MEDIUM_VOLUME,
        "race_recap": MEDIUM_VOLUME + NICHE,
        "gear_review": GEAR_SPECIFIC,
        "vulnerability": MOTIVATIONAL + NICHE,
    }

    def __init__(self, max_hashtags: int = 25) -> None:
        self.max_hashtags = max_hashtags
        self._used_sets: list[set[str]] = []

    def generate(self, theme: str = "motivation") -> list[str]:
        """Generate a hashtag set for a given content theme.

        Returns 20-25 hashtags mixing different volume levels.
        """
        tags: list[str] = []

        # Always include branded (3-5)
        tags.extend(random.sample(BRANDED, min(3, len(BRANDED))))

        # Add theme-specific tags (4-6)
        theme_pool = self.THEME_POOLS.get(theme, MOTIVATIONAL)
        tags.extend(random.sample(theme_pool, min(5, len(theme_pool))))

        # Add niche tags (3-4)
        remaining_niche = [t for t in NICHE if t not in tags]
        tags.extend(random.sample(remaining_niche, min(3, len(remaining_niche))))

        # Add medium volume (4-5)
        remaining_med = [t for t in MEDIUM_VOLUME if t not in tags]
        tags.extend(random.sample(remaining_med, min(4, len(remaining_med))))

        # Fill to max with high volume
        remaining_high = [t for t in HIGH_VOLUME if t not in tags]
        fill_count = min(self.max_hashtags - len(tags), len(remaining_high))
        if fill_count > 0:
            tags.extend(random.sample(remaining_high, fill_count))

        # Deduplicate and limit
        seen: set[str] = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        result = unique_tags[: self.max_hashtags]

        # Track used sets to avoid repetition
        self._used_sets.append(set(result))
        if len(self._used_sets) > 10:
            self._used_sets.pop(0)

        return result

    def generate_as_string(self, theme: str = "motivation") -> str:
        """Generate hashtags as a single string for easy copy-paste."""
        return " ".join(self.generate(theme))
