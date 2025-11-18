"""
AuroraCollab theme for Team Synapse.

Modern, meeting-focused theme with a deep indigo primary, teal accent,
and soft neutral background – inspired by tools like Slack/Teams.
"""
from __future__ import annotations
from typing import Iterable
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class AuroraCollab(Base):
    """AuroraCollab theme with indigo primary and teal secondary colors."""
    
    def __init__(
        self,
        *,
        # Deep, trustworthy primary + bright accent for CTAs
        primary_hue: colors.Color | str = colors.indigo,
        secondary_hue: colors.Color | str = colors.teal,
        # Slightly cooler neutral base for app chrome
        neutral_hue: colors.Color | str = colors.slate,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_lg,
        text_size: sizes.Size | str = sizes.text_md,
        font: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Quicksand"),
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("IBM Plex Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )


# Create theme instance used by the app
seafoam = AuroraCollab()