"""UI modules for Team Synapse."""
from .theme import seafoam
from .components import (
    create_header,
    create_info_banner,
    create_features_section,
    create_tips_section,
    create_footer,
    format_analysis_summary,
)

__all__ = [
    "seafoam",
    "create_header",
    "create_info_banner",
    "create_features_section",
    "create_tips_section",
    "create_footer",
    "format_analysis_summary",
]