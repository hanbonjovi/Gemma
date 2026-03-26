# Gemma Park — AI Running Influencer

An AI-powered content generation system for **Gemma Park**, a virtual female ultra-running influencer on Instagram.

## Who is Gemma Park?

- **28-year-old pan-Asian (Korean-Japanese) ultra runner** based in Portland, OR
- **"Female David Goggins"** — tough, gritty, motivational, but warm and approachable
- Former D1 track athlete who discovered ultra running after burnout
- Completed Western States 100, UTMB, Leadville 100
- Runs 70-90 miles/week on Pacific Northwest trails
- All content is **100% AI-generated** — images, videos, captions

## Tech Stack

| Component | Primary | Alternative |
|-----------|---------|-------------|
| **Images** | FLUX Kontext (via Replicate) | Google Nano Banana 2 (free tier) |
| **Videos** | Wan-Animate (free/open-source) | HeyGen ($29/mo) |
| **Captions** | Claude API (Anthropic) | OpenAI GPT-4o |
| **Posting** | Manual export | Instagram Graph API |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your API keys

# Check configuration
python -m gemma status

# View Gemma's character profile
python -m gemma persona

# Generate reference images for character consistency
python -m gemma init-character --engine nano_banana --count 5

# Generate a single post (dry run — no API calls)
python -m gemma generate --theme trail_run --dry-run

# Generate a single image post
python -m gemma generate --theme motivation --reference assets/reference/gemma_ref_001.png

# Generate a reel with hook + script
python -m gemma generate --theme trail_run --format reel --reference assets/reference/gemma_ref_001.png

# Generate viral hooks
python -m gemma hooks --theme motivation --audience cold --count 10

# Generate a caption in Gemma's voice
python -m gemma caption --theme trail_run

# View content calendar
python -m gemma calendar --week

# Generate a full week of content
python -m gemma generate-week --reference assets/reference/gemma_ref_001.png

# Export posts for manual Instagram posting
python -m gemma export --all-pending
```

## Project Structure

```
Gemma/
├── gemma/
│   ├── persona/        # Character bible & voice guide
│   ├── generators/     # Image, caption, & hook generators
│   ├── video/          # Video generation (Wan-Animate, HeyGen)
│   ├── content/        # Calendar, themes, post model
│   ├── instagram/      # Publishing & hashtag strategy
│   ├── automation/     # Full content pipeline orchestrator
│   └── cli.py          # CLI commands
├── prompts/            # YAML prompt templates (easy to customize)
├── assets/
│   ├── reference/      # Character reference images
│   ├── broll/          # B-roll footage for character swap
│   └── output/         # Generated content ready to post
└── tests/
```

## Content Calendar

| Day | Theme | Format |
|-----|-------|--------|
| Monday | Motivation Monday | Image + Reel |
| Tuesday | Trail Tuesday | Image carousel |
| Wednesday | Workout Wednesday | Reel |
| Thursday | Throwback Thursday | Image |
| Friday | Gear Friday | Carousel |
| Saturday | Long Run Saturday | Reel + Stories |
| Sunday | Rest & Reflect | Image |

## Workflow

### Static Posts (Images)
1. Generate character reference images with `init-character`
2. Use FLUX Kontext to place Gemma in new scenes with character consistency
3. Generate captions in Gemma's voice with Claude
4. Export and post to Instagram

### Reels (Videos) — Ernesto Lopez Workflow
1. Generate base character images (Nano Banana / FLUX)
2. Download real running b-roll as motion templates
3. Use Wan-Animate to swap Gemma onto b-roll footage (free)
4. Add hook text via Instagram native editor
5. Post!

## API Costs

| Setup | Monthly Cost |
|-------|-------------|
| **Free** (Nano Banana + Wan-Animate free tiers) | $0 |
| **Recommended** (Replicate + Claude API) | ~$5-12 |
| **Full** (all engines + HeyGen) | ~$35-45 |

## Configuration

See `.env.example` for all API keys and settings.
