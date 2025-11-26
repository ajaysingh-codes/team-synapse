"""UI modules for Team Synapse."""
from .theme import team_synapse_theme
from .components import (
    create_info_banner,
    create_features_section,
    create_tips_section,
    create_footer,
    format_analysis_summary,
    # Homepage components
    create_homepage_hero,
    create_problem_section,
    create_how_it_works_section,
    create_features_grid,
    create_use_cases_section,
    create_cta_section,
)

__all__ = [
    "team_synapse_theme",
    "create_info_banner",
    "create_features_section",
    "create_tips_section",
    "create_footer",
    "format_analysis_summary",
    # Homepage components
    "create_homepage_hero",
    "create_problem_section",
    "create_how_it_works_section",
    "create_features_grid",
    "create_use_cases_section",
    "create_cta_section",
]