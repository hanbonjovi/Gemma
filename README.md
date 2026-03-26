# Gemma Park — AI Running Influencer

An AI-powered content generation system for **Gemma Park**, a virtual female ultra-running influencer on Instagram.

## Overview

Gemma Park is a pan-Asian female ultra runner — a "female David Goggins" who combines raw grit, motivational energy, and trail running passion. All content (images, captions, stories) is AI-generated and posted to Instagram.

## Architecture

```
gemma/
├── persona/          # Character bible, voice guide, visual identity
├── generators/       # Image & caption generation engines
├── content/          # Content calendar, templates, scheduling
├── instagram/        # Instagram API integration & posting
├── assets/           # Reference images, generated content output
└── config/           # Configuration & environment settings
```

## Tech Stack

- **Python 3.11+**
- **Image Generation**: FLUX Kontext (primary), Google Nano Banana 2 (alternative)
- **Caption/Text AI**: Claude API (Anthropic) — configurable for other providers
- **Instagram**: Graph API via Meta Business SDK (+ manual posting mode)
- **Scheduling**: APScheduler for content calendar automation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your API keys

# Generate a single post
python -m gemma generate-post --theme trail-run

# Generate a week of content
python -m gemma generate-week

# Post to Instagram (requires API setup)
python -m gemma post --draft  # Preview only
python -m gemma post          # Post to Instagram
```

## Configuration

See `.env.example` for all required API keys and settings.

## Content Types

- Trail running photography
- Motivational quotes & captions
- Training logs & race recaps
- Running tips & gear reviews
- Story content (carousel/reels concepts)
