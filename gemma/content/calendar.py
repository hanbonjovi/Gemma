"""Content calendar — generates and manages the weekly/monthly content schedule."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from gemma.content.post import Post, PostStatus
from gemma.content.themes import ContentTheme, get_theme_for_day


@dataclass
class ContentCalendar:
    """Manages the content schedule and tracks post status."""

    posts: list[Post] = field(default_factory=list)
    calendar_file: Path = field(default=Path("./assets/output/calendar.json"))

    def generate_week(self, start_date: date | None = None) -> list[Post]:
        """Generate a week of content plans based on the theme schedule."""
        start = start_date or date.today()
        # Adjust to Monday
        start = start - timedelta(days=start.weekday())

        week_posts: list[Post] = []
        for day_offset in range(7):
            current_date = start + timedelta(days=day_offset)
            theme = get_theme_for_day(current_date.weekday())
            posts = self._create_daily_posts(current_date, theme)
            week_posts.extend(posts)

        self.posts.extend(week_posts)
        self.save()
        return week_posts

    def generate_month(self, start_date: date | None = None) -> list[Post]:
        """Generate a full month of content plans."""
        start = start_date or date.today().replace(day=1)
        all_posts: list[Post] = []

        current = start
        while current.month == start.month:
            theme = get_theme_for_day(current.weekday())
            posts = self._create_daily_posts(current, theme)
            all_posts.extend(posts)
            current += timedelta(days=1)

        self.posts.extend(all_posts)
        self.save()
        return all_posts

    def _create_daily_posts(
        self, post_date: date, theme: ContentTheme
    ) -> list[Post]:
        """Create post entries for a single day based on its theme."""
        posts: list[Post] = []

        # Primary post (first format)
        primary_format = theme.formats[0].value
        primary_time = theme.posting_times[0] if theme.posting_times else "07:00"
        scheduled = datetime.combine(
            post_date, datetime.strptime(primary_time, "%H:%M").time()
        )

        posts.append(
            Post(
                theme=theme.name,
                format=primary_format,
                scheduled_time=scheduled.isoformat(),
                status=PostStatus.PLANNED.value,
                metadata={
                    "display_name": theme.display_name,
                    "description": theme.description,
                    "caption_theme": theme.caption_theme,
                    "scene_keywords": theme.scene_keywords,
                    "outfit_type": theme.outfit_type,
                },
            )
        )

        # Secondary post if there's a second posting time
        if len(theme.posting_times) > 1 and len(theme.formats) > 1:
            secondary_format = theme.formats[1].value
            secondary_time = theme.posting_times[1]
            scheduled_2 = datetime.combine(
                post_date, datetime.strptime(secondary_time, "%H:%M").time()
            )
            posts.append(
                Post(
                    theme=theme.name,
                    format=secondary_format,
                    scheduled_time=scheduled_2.isoformat(),
                    status=PostStatus.PLANNED.value,
                    metadata={
                        "display_name": theme.display_name,
                        "description": theme.description,
                        "caption_theme": theme.caption_theme,
                        "scene_keywords": theme.scene_keywords,
                        "outfit_type": theme.outfit_type,
                        "is_secondary": True,
                    },
                )
            )

        return posts

    def get_posts_for_date(self, target_date: date) -> list[Post]:
        """Get all posts scheduled for a specific date."""
        target_str = target_date.isoformat()
        return [
            p
            for p in self.posts
            if p.scheduled_time.startswith(target_str)
        ]

    def get_pending_posts(self) -> list[Post]:
        """Get all posts that haven't been posted yet."""
        return [
            p for p in self.posts if p.status != PostStatus.POSTED.value
        ]

    def get_generated_posts(self) -> list[Post]:
        """Get posts that are generated but not yet posted."""
        return [
            p
            for p in self.posts
            if p.status == PostStatus.GENERATED.value
        ]

    def update_post_status(self, post_id: str, status: PostStatus) -> None:
        """Update the status of a post."""
        for post in self.posts:
            if post.id == post_id:
                post.status = status.value
                break
        self.save()

    def save(self) -> None:
        """Save the calendar to disk."""
        self.calendar_file.parent.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in self.posts]
        self.calendar_file.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        """Load the calendar from disk."""
        if self.calendar_file.exists():
            data = json.loads(self.calendar_file.read_text())
            self.posts = [Post.from_dict(p) for p in data]

    def display_week(self, start_date: date | None = None) -> str:
        """Format the week's content plan for display."""
        start = start_date or date.today()
        start = start - timedelta(days=start.weekday())

        lines = [f"📅 Content Calendar — Week of {start.strftime('%B %d, %Y')}\n"]
        for day_offset in range(7):
            current = start + timedelta(days=day_offset)
            posts = self.get_posts_for_date(current)
            day_name = current.strftime("%A")
            lines.append(f"\n{day_name} ({current.strftime('%m/%d')}):")
            if posts:
                for p in posts:
                    status_icon = {
                        "planned": "⬜",
                        "generated": "🟨",
                        "reviewed": "🟦",
                        "posted": "✅",
                    }.get(p.status, "⬜")
                    display = p.metadata.get("display_name", p.theme)
                    lines.append(
                        f"  {status_icon} [{p.format}] {display} @ "
                        f"{p.scheduled_time.split('T')[1][:5] if 'T' in p.scheduled_time else '??:??'}"
                    )
            else:
                lines.append("  (no posts scheduled)")

        return "\n".join(lines)
