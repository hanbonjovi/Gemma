"""Configuration management — loads settings from .env and provides typed config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class ImageConfig:
    default_engine: str = "flux_kontext"
    replicate_api_token: str = ""
    fal_key: str = ""
    google_api_key: str = ""
    lora_model_path: str = ""
    lora_weight: float = 0.55


@dataclass
class LLMConfig:
    default_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""


@dataclass
class VideoConfig:
    replicate_api_token: str = ""  # Shared with image config
    heygen_api_key: str = ""


@dataclass
class InstagramConfig:
    access_token: str = ""
    business_account_id: str = ""
    facebook_page_id: str = ""


@dataclass
class Config:
    image: ImageConfig = field(default_factory=ImageConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    output_dir: Path = Path("./assets/output")

    @classmethod
    def load(cls, env_path: str | Path | None = None) -> Config:
        """Load configuration from .env file and environment variables."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        replicate_token = os.getenv("REPLICATE_API_TOKEN", "")

        return cls(
            image=ImageConfig(
                default_engine=os.getenv("DEFAULT_IMAGE_ENGINE", "flux_kontext"),
                replicate_api_token=replicate_token,
                fal_key=os.getenv("FAL_KEY", ""),
                google_api_key=os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", ""),
                lora_model_path=os.getenv("LORA_MODEL_PATH", ""),
                lora_weight=float(os.getenv("LORA_WEIGHT", "0.55")),
            ),
            llm=LLMConfig(
                default_provider=os.getenv("DEFAULT_LLM_PROVIDER", "anthropic"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            ),
            video=VideoConfig(
                replicate_api_token=replicate_token,
                heygen_api_key=os.getenv("HEYGEN_API_KEY", ""),
            ),
            instagram=InstagramConfig(
                access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
                business_account_id=os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", ""),
                facebook_page_id=os.getenv("FACEBOOK_PAGE_ID", ""),
            ),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./assets/output")),
        )

    def validate(self) -> list[str]:
        """Return list of warnings about missing configuration."""
        warnings = []
        engine = self.image.default_engine
        if engine == "flux_kontext" and not self.image.replicate_api_token and not self.image.fal_key:
            warnings.append("FLUX Kontext selected but no REPLICATE_API_TOKEN or FAL_KEY set")
        if engine == "nano_banana" and not self.image.google_api_key:
            warnings.append("Nano Banana selected but no GOOGLE_API_KEY set")

        provider = self.llm.default_provider
        if provider == "anthropic" and not self.llm.anthropic_api_key:
            warnings.append("Anthropic selected but no ANTHROPIC_API_KEY set")
        if provider == "openai" and not self.llm.openai_api_key:
            warnings.append("OpenAI selected but no OPENAI_API_KEY set")

        return warnings
