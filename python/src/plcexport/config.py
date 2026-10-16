"""Settings of the extractors. All values come from environment variables prefixed ``PLCEXPORT_``
(or a ``.env`` file)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLCEXPORT_", env_file=".env", extra="ignore")

    # STEP 7 V5.x
    s7dump_path: Path | None = None  # default: s7dump/publish/<rid>/s7dump[.exe] in this repo
    s7_mnemonic: Literal["en", "de"] = "en"
    s7_fallback_for: str = ""  # comma list; allowed: "languages"
    s7_text_language: str = "de"  # language of comments when s7dump reports "und"
    s7dump_timeout_s: int = Field(default=600, ge=1)
    s7_policy_file: Path | None = None

    # TIA Portal
    tiadump_path: Path | None = None  # default: tiadump/publish/tiadump.exe in this repo
    tiadump_paths: dict[str, Path] = Field(default_factory=dict)  # {"V20": path, ...}
    tia_version: str = "auto"  # "auto" = newest installed TIA Portal, "none", or e.g. "V21"
    tia_timeout_s: int = Field(default=1800, ge=1)
    tia_work_root: Path = Path("C:/tiaw")  # short: TIA refuses project paths > 143 chars
    tia_libraries_file: Path | None = None  # YAML list of the company libraries


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
