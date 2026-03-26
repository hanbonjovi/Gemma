"""Content themes — weekly schedule and content type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ContentFormat(str, Enum):
    IMAGE = "image"
    CAROUSEL = "carousel"
    REEL = "reel"
    STORY = "story"


class DayOfWeek(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass(frozen=True)
class ContentTheme:
    name: str
    display_name: str
    day: DayOfWeek
    formats: list[ContentFormat]
    description: str
    caption_theme: str  # Maps to voice.py caption structure
    scene_keywords: list[str] = field(default_factory=list)
    outfit_type: str = "trail_running"
    posting_times: list[str] = field(default_factory=lambda: ["07:00", "12:00"])


# Weekly content calendar
WEEKLY_THEMES: list[ContentTheme] = [
    ContentTheme(
        name="motivation_monday",
        display_name="Motivation Monday",
        day=DayOfWeek.MONDAY,
        formats=[ContentFormat.IMAGE, ContentFormat.REEL],
        description="Motivational quote or story paired with a powerful trail image or short reel",
        caption_theme="motivation",
        scene_keywords=["sunrise", "summit", "mountain", "epic trail vista"],
        outfit_type="trail_running",
        posting_times=["06:30", "18:00"],
    ),
    ContentTheme(
        name="trail_tuesday",
        display_name="Trail Tuesday",
        day=DayOfWeek.TUESDAY,
        formats=[ContentFormat.CAROUSEL, ContentFormat.IMAGE],
        description="Trail running photo carousel with trail review and running details",
        caption_theme="trail_run",
        scene_keywords=["forest trail", "muddy path", "creek crossing", "switchbacks"],
        outfit_type="trail_running",
        posting_times=["07:00", "12:00"],
    ),
    ContentTheme(
        name="workout_wednesday",
        display_name="Workout Wednesday",
        day=DayOfWeek.WEDNESDAY,
        formats=[ContentFormat.REEL, ContentFormat.IMAGE],
        description="Training tip, workout breakdown, or running drill as a video reel",
        caption_theme="training_log",
        scene_keywords=["tempo run", "hill repeats", "track workout", "strength training"],
        outfit_type="road_running",
        posting_times=["07:00", "17:00"],
    ),
    ContentTheme(
        name="throwback_thursday",
        display_name="Throwback Thursday",
        day=DayOfWeek.THURSDAY,
        formats=[ContentFormat.IMAGE, ContentFormat.CAROUSEL],
        description="Personal story, race memory, or journey reflection",
        caption_theme="vulnerability",
        scene_keywords=["race finish line", "old trails", "training memories", "journey"],
        outfit_type="race_day",
        posting_times=["08:00", "19:00"],
    ),
    ContentTheme(
        name="gear_friday",
        display_name="Gear Friday",
        day=DayOfWeek.FRIDAY,
        formats=[ContentFormat.CAROUSEL, ContentFormat.IMAGE],
        description="Gear review, flat-lay, or equipment recommendation",
        caption_theme="gear_review",
        scene_keywords=["gear flat-lay", "running shoes close-up", "hydration vest", "gear on trail"],
        outfit_type="casual",
        posting_times=["09:00", "12:00"],
    ),
    ContentTheme(
        name="long_run_saturday",
        display_name="Long Run Saturday",
        day=DayOfWeek.SATURDAY,
        formats=[ContentFormat.REEL, ContentFormat.STORY],
        description="Long run recap, in-progress trail footage, or running vlog style",
        caption_theme="training_log",
        scene_keywords=["long trail run", "mountain run", "ultra distance", "aid station"],
        outfit_type="trail_running",
        posting_times=["06:00", "15:00"],
    ),
    ContentTheme(
        name="rest_sunday",
        display_name="Rest & Reflect",
        day=DayOfWeek.SUNDAY,
        formats=[ContentFormat.IMAGE, ContentFormat.STORY],
        description="Recovery, mindset, gratitude, or weekly reflection",
        caption_theme="vulnerability",
        scene_keywords=["coffee morning", "stretching", "foam roller", "cozy recovery", "sunset"],
        outfit_type="casual",
        posting_times=["09:00", "19:00"],
    ),
]


def get_theme_for_day(day: int) -> ContentTheme:
    """Get the content theme for a given day of the week (0=Monday)."""
    for theme in WEEKLY_THEMES:
        if theme.day.value == day:
            return theme
    return WEEKLY_THEMES[0]  # Default to Monday


def get_theme_by_name(name: str) -> ContentTheme | None:
    """Get a content theme by its name."""
    for theme in WEEKLY_THEMES:
        if theme.name == name:
            return theme
    # Also match partial names
    for theme in WEEKLY_THEMES:
        if name in theme.name:
            return theme
    return None


def get_all_themes() -> list[ContentTheme]:
    """Return all weekly themes."""
    return WEEKLY_THEMES
