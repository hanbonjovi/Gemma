"""CLI interface — Click-based commands for the Gemma content pipeline."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path

import click

from gemma.config import Config


def run_async(coro):
    """Run an async coroutine from sync CLI code."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
@click.option("--env", default=None, help="Path to .env file")
@click.pass_context
def cli(ctx, env):
    """Gemma Park — AI Running Influencer Content Generator."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.load(env)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current configuration status and validate API keys."""
    config: Config = ctx.obj["config"]
    warnings = config.validate()

    click.echo("=== Gemma Park — Status ===\n")
    click.echo(f"Image Engine:  {config.image.default_engine}")
    click.echo(f"LLM Provider:  {config.llm.default_provider}")
    click.echo(f"Output Dir:    {config.output_dir}")
    click.echo(f"Replicate:     {'configured' if config.image.replicate_api_token else 'not set'}")
    click.echo(f"Google API:    {'configured' if config.image.google_api_key else 'not set'}")
    click.echo(f"Anthropic:     {'configured' if config.llm.anthropic_api_key else 'not set'}")
    click.echo(f"OpenAI:        {'configured' if config.llm.openai_api_key else 'not set'}")
    click.echo(f"HeyGen:        {'configured' if config.video.heygen_api_key else 'not set'}")
    click.echo(f"Instagram:     {'configured' if config.instagram.access_token else 'not set'}")

    if warnings:
        click.echo("\n⚠️  Warnings:")
        for w in warnings:
            click.echo(f"  - {w}")
    else:
        click.echo("\n✅ All configured!")


@cli.command()
@click.pass_context
def persona(ctx):
    """Display Gemma Park's full character profile."""
    from gemma.persona.character import get_character
    from gemma.persona.voice import get_voice_guide

    char = get_character()
    voice = get_voice_guide()

    click.echo("=== Gemma Park — Character Bible ===\n")
    click.echo(f"Name:       {char.name}")
    click.echo(f"Handle:     {char.handle}")
    click.echo(f"Tagline:    {char.tagline}")
    click.echo(f"Age:        {char.age}")
    click.echo(f"Ethnicity:  {char.ethnicity}")
    click.echo(f"Location:   {char.location}")
    click.echo(f"Occupation: {char.occupation}")
    click.echo(f"\nBackstory:\n{char.backstory}")
    click.echo(f"\nPersonality:")
    for trait in char.personality_traits:
        click.echo(f"  - {trait}")
    click.echo(f"\nRace PRs:")
    for race, time in char.race_prs.items():
        click.echo(f"  {race}: {time}")
    click.echo(f"\nFavorite Trails:")
    for trail in char.favorite_trails:
        click.echo(f"  - {trail}")
    click.echo(f"\nImage Prompt Preview:")
    click.echo(f"  {char.to_image_prompt()[:200]}...")


@cli.command("generate")
@click.option("--theme", default=None, help="Content theme (e.g., trail_run, motivation)")
@click.option("--format", "fmt", type=click.Choice(["image", "reel", "carousel"]), default="image")
@click.option("--engine", type=click.Choice(["flux_kontext", "nano_banana"]), default=None)
@click.option("--reference", default=None, help="Reference image path for character consistency")
@click.option("--broll", default=None, help="B-roll video path for reel character swap")
@click.option("--dry-run", is_flag=True, help="Preview prompts without making API calls")
@click.pass_context
def generate(ctx, theme, fmt, engine, reference, broll, dry_run):
    """Generate a single post (image or reel)."""
    config: Config = ctx.obj["config"]
    if engine:
        config.image.default_engine = engine

    from gemma.automation.pipeline import ContentPipeline
    from gemma.content.themes import get_theme_by_name, get_theme_for_day

    pipeline = ContentPipeline(config)

    # Resolve theme
    content_theme = None
    if theme:
        content_theme = get_theme_by_name(theme)
        if not content_theme:
            click.echo(f"Unknown theme: {theme}")
            click.echo("Available: motivation_monday, trail_tuesday, workout_wednesday, "
                       "throwback_thursday, gear_friday, long_run_saturday, rest_sunday")
            return
    else:
        content_theme = get_theme_for_day(date.today().weekday())

    if dry_run:
        result = run_async(pipeline.dry_run(theme_name=theme))
        click.echo("\n=== Dry Run Preview ===\n")
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"Generating {fmt} for {content_theme.display_name}...")
    click.echo(f"Engine: {config.image.default_engine}")

    if fmt == "reel":
        post = run_async(
            pipeline.generate_reel_post(content_theme, reference, broll)
        )
    else:
        post = run_async(
            pipeline.generate_image_post(content_theme, reference)
        )

    # Export
    from gemma.instagram.publisher import ManualPublisher
    publisher = ManualPublisher(config)
    post_dir = publisher.export_post(post)

    click.echo(f"\n✅ Post generated!")
    click.echo(f"   Theme:   {post.metadata.get('display_name', post.theme)}")
    click.echo(f"   Format:  {post.format}")
    if post.media_paths:
        click.echo(f"   Media:   {post.media_paths[0]}")
    click.echo(f"   Output:  {post_dir}")
    click.echo(f"\n--- Caption ---")
    click.echo(post.caption[:500])
    if post.hook_text:
        click.echo(f"\n--- Hook ---")
        click.echo(post.hook_text)


@cli.command("generate-week")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD), defaults to this week")
@click.option("--reference", default=None, help="Reference image path")
@click.option("--dry-run", is_flag=True, help="Preview without API calls")
@click.pass_context
def generate_week(ctx, start, reference, dry_run):
    """Generate a full week of content."""
    config: Config = ctx.obj["config"]
    pipeline_module = __import__("gemma.automation.pipeline", fromlist=["ContentPipeline"])
    pipeline = pipeline_module.ContentPipeline(config)

    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None

    if dry_run:
        from datetime import timedelta
        s = start_date or date.today()
        s = s - timedelta(days=s.weekday())
        click.echo("\n=== Weekly Content Plan (Dry Run) ===\n")
        for offset in range(7):
            current = s + timedelta(days=offset)
            result = run_async(pipeline.dry_run(target_date=current))
            click.echo(f"{current.strftime('%A %m/%d')}: {result['theme']} [{result['format']}]")
            click.echo(f"  Prompt: {result['image_prompt'][:100]}...")
        return

    click.echo("Generating weekly content...")
    posts = run_async(pipeline.generate_weekly_content(start_date, reference))
    click.echo(f"\n✅ Generated {len(posts)} posts!")
    for p in posts:
        click.echo(f"  [{p.format}] {p.metadata.get('display_name', p.theme)}")


@cli.command("hooks")
@click.option("--theme", default="motivation", help="Content theme")
@click.option("--audience", type=click.Choice(["cold", "warm", "hot"]), default="cold")
@click.option("--count", default=10, help="Number of hooks to generate")
@click.pass_context
def hooks(ctx, theme, audience, count):
    """Generate viral hooks for Instagram Reels."""
    config: Config = ctx.obj["config"]
    from gemma.generators.hooks import HookGenerator

    gen = HookGenerator(config)
    click.echo(f"Generating {count} {audience} hooks for '{theme}'...\n")
    hook_list = run_async(gen.generate_hooks(theme, audience, count))

    for i, hook in enumerate(hook_list, 1):
        click.echo(f"  {i}. {hook.text}")

    click.echo(f"\n✅ Generated {len(hook_list)} hooks")


@cli.command("caption")
@click.option("--theme", default="motivation", help="Caption theme")
@click.option("--image", "image_path", default=None, help="Image to describe for context")
@click.option("--context", default="", help="Additional context")
@click.pass_context
def caption(ctx, theme, image_path, context):
    """Generate a caption in Gemma's voice."""
    config: Config = ctx.obj["config"]
    from gemma.generators.caption import CaptionGenerator

    gen = CaptionGenerator(config)
    desc = ""
    if image_path:
        desc = f"Image at {image_path}"

    click.echo(f"Generating '{theme}' caption...\n")
    result = run_async(gen.generate(theme=theme, image_description=desc, context=context))

    click.echo("--- Caption ---")
    click.echo(result.caption)
    click.echo("\n--- Hashtags ---")
    click.echo(" ".join(result.hashtags))


@cli.command("calendar")
@click.option("--week", is_flag=True, help="Show this week's plan")
@click.option("--generate", "gen_cal", is_flag=True, help="Generate a new weekly plan")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD)")
@click.pass_context
def calendar(ctx, week, gen_cal, start):
    """View or generate the content calendar."""
    from gemma.content.calendar import ContentCalendar

    cal = ContentCalendar()
    cal.load()

    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None

    if gen_cal:
        posts = cal.generate_week(start_date)
        click.echo(f"✅ Generated {len(posts)} posts for the week")

    click.echo(cal.display_week(start_date))


@cli.command("export")
@click.option("--date", "target_date", default=None, help="Date to export (YYYY-MM-DD)")
@click.option("--all-pending", is_flag=True, help="Export all pending posts")
@click.pass_context
def export(ctx, target_date, all_pending):
    """Export generated posts for manual Instagram posting."""
    config: Config = ctx.obj["config"]
    from gemma.content.calendar import ContentCalendar
    from gemma.instagram.publisher import ManualPublisher

    cal = ContentCalendar()
    cal.load()
    publisher = ManualPublisher(config)

    if all_pending:
        posts = cal.get_generated_posts()
    elif target_date:
        d = datetime.strptime(target_date, "%Y-%m-%d").date()
        posts = cal.get_posts_for_date(d)
    else:
        posts = cal.get_posts_for_date(date.today())

    if not posts:
        click.echo("No posts to export.")
        return

    dirs = publisher.export_batch(posts)
    click.echo(f"✅ Exported {len(dirs)} posts:")
    for d in dirs:
        click.echo(f"  {d}")


@cli.command("init-character")
@click.option("--engine", type=click.Choice(["flux_kontext", "nano_banana"]), default="nano_banana")
@click.option("--count", default=5, help="Number of reference images to generate")
@click.pass_context
def init_character(ctx, engine, count):
    """Generate initial reference images for Gemma Park."""
    config: Config = ctx.obj["config"]
    config.image.default_engine = engine

    from gemma.persona.character import get_character

    char = get_character()
    ref_dir = Path("./assets/reference")
    ref_dir.mkdir(parents=True, exist_ok=True)

    prompts = [
        char.to_image_prompt(
            scene="Close-up portrait, looking directly at camera, confident expression. "
                  "Outdoor natural lighting, blurred forest background.",
            outfit_type="trail_running",
        ),
        char.to_image_prompt(
            scene="Running on a misty forest trail, mid-stride, powerful form. "
                  "Moody Pacific Northwest atmosphere, tall evergreen trees.",
            outfit_type="trail_running",
        ),
        char.to_image_prompt(
            scene="Standing at a mountain summit, hands on hips, overlooking a valley. "
                  "Golden hour lighting, Mt. Hood in background.",
            outfit_type="trail_running",
        ),
        char.to_image_prompt(
            scene="Sitting on a rock after a long run, sweaty, drinking from a hydration flask. "
                  "Raw, authentic moment. Forest clearing.",
            outfit_type="trail_running",
        ),
        char.to_image_prompt(
            scene="Crossing a finish line at an ultramarathon, arms raised in triumph. "
                  "Race bib visible, emotional expression, crowd in background.",
            outfit_type="race_day",
        ),
    ]

    if engine == "nano_banana":
        from gemma.generators.nano_banana import NanoBananaGenerator
        gen = NanoBananaGenerator(config)
    else:
        from gemma.generators.flux_kontext import FluxKontextGenerator
        gen = FluxKontextGenerator(config)

    click.echo(f"Generating {count} reference images with {engine}...\n")

    for i, prompt in enumerate(prompts[:count]):
        click.echo(f"  [{i+1}/{count}] Generating...")
        out_path = ref_dir / f"gemma_ref_{i+1:03d}.png"
        try:
            result = run_async(gen.generate(prompt=prompt, output_path=out_path))
            click.echo(f"    ✅ Saved: {result}")
        except Exception as e:
            click.echo(f"    ❌ Error: {e}")

    click.echo(f"\n✅ Reference images saved to {ref_dir}/")
    click.echo("Review them and pick the best 2-3 for consistent character generation.")


if __name__ == "__main__":
    cli()
