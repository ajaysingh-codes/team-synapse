"""
Design System for Team Synapse.
Centralized design tokens and CSS class generation.
"""

# Color Palette - Blue Theme
COLORS = {
    # Primary (Blue)
    "primary_50": "#eff6ff",
    "primary_100": "#dbeafe",
    "primary_200": "#bfdbfe",
    "primary_300": "#93c5fd",
    "primary_400": "#60a5fa",
    "primary_500": "#3b82f6",  # Main brand color
    "primary_600": "#2563eb",
    "primary_700": "#1d4ed8",
    "primary_800": "#1e40af",
    "primary_900": "#1e3a8a",

    # Accent (Teal)
    "accent_400": "#2dd4bf",
    "accent_500": "#14b8a6",
    "accent_600": "#0d9488",

    # Neutral (Slate)
    "neutral_50": "#f8fafc",
    "neutral_100": "#f1f5f9",
    "neutral_200": "#e2e8f0",
    "neutral_300": "#cbd5e1",
    "neutral_400": "#94a3b8",
    "neutral_500": "#64748b",
    "neutral_600": "#475569",
    "neutral_700": "#334155",
    "neutral_800": "#1e293b",
    "neutral_900": "#0f172a",

    # Semantic Colors
    "success": "#10b981",
    "success_light": "#d1fae5",
    "warning": "#f59e0b",
    "warning_light": "#fef3c7",
    "error": "#ef4444",
    "error_light": "#fee2e2",
    "info": "#3b82f6",
    "info_light": "#dbeafe",
}

# Typography Scale
TYPOGRAPHY = {
    # Font sizes
    "display_xl": "3.5rem",    # 56px - Hero headlines
    "display_lg": "3rem",      # 48px
    "display_md": "2.5rem",    # 40px
    "heading_xl": "2rem",      # 32px - Section headers
    "heading_lg": "1.75rem",   # 28px
    "heading_md": "1.5rem",    # 24px
    "heading_sm": "1.25rem",   # 20px
    "body_lg": "1.125rem",     # 18px - Large body text
    "body_md": "1rem",         # 16px - Standard body text
    "body_sm": "0.875rem",     # 14px - Small text
    "caption": "0.75rem",      # 12px - Captions, labels

    # Font weights
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",
    "weight_extrabold": "800",

    # Line heights
    "leading_tight": "1.25",
    "leading_normal": "1.5",
    "leading_relaxed": "1.75",
}

# Spacing Scale
SPACING = {
    "xs": "0.5rem",   # 8px
    "sm": "0.75rem",  # 12px
    "md": "1rem",     # 16px
    "lg": "1.5rem",   # 24px
    "xl": "2rem",     # 32px
    "2xl": "3rem",    # 48px
    "3xl": "4rem",    # 64px
    "4xl": "6rem",    # 96px
}

# Border Radius
RADIUS = {
    "sm": "0.375rem",   # 6px
    "md": "0.5rem",     # 8px
    "lg": "0.75rem",    # 12px
    "xl": "1rem",       # 16px
    "2xl": "1.5rem",    # 24px
    "full": "9999px",   # Fully rounded
}

# Shadows
SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
    "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",
}


def get_design_system_css() -> str:
    """
    Generate complete CSS for the design system.

    Returns:
        CSS string with all design tokens and utility classes
    """
    css = """
/* ===== DESIGN SYSTEM CSS ===== */

/* === Color Variables === */
:root {
    /* Primary (Blue) */
    --color-primary-50: #eff6ff;
    --color-primary-100: #dbeafe;
    --color-primary-200: #bfdbfe;
    --color-primary-300: #93c5fd;
    --color-primary-400: #60a5fa;
    --color-primary-500: #3b82f6;
    --color-primary-600: #2563eb;
    --color-primary-700: #1d4ed8;
    --color-primary-800: #1e40af;
    --color-primary-900: #1e3a8a;

    /* Accent (Teal) */
    --color-accent-400: #2dd4bf;
    --color-accent-500: #14b8a6;
    --color-accent-600: #0d9488;

    /* Neutral (Slate) */
    --color-neutral-50: #f8fafc;
    --color-neutral-100: #f1f5f9;
    --color-neutral-200: #e2e8f0;
    --color-neutral-300: #cbd5e1;
    --color-neutral-400: #94a3b8;
    --color-neutral-500: #64748b;
    --color-neutral-600: #475569;
    --color-neutral-700: #334155;
    --color-neutral-800: #1e293b;
    --color-neutral-900: #0f172a;

    /* Semantic */
    --color-success: #10b981;
    --color-success-light: #d1fae5;
    --color-warning: #f59e0b;
    --color-warning-light: #fef3c7;
    --color-error: #ef4444;
    --color-error-light: #fee2e2;
    --color-info: #3b82f6;
    --color-info-light: #dbeafe;

    /* Spacing */
    --space-xs: 0.5rem;
    --space-sm: 0.75rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;
    --space-3xl: 4rem;
    --space-4xl: 6rem;

    /* Radius */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    --radius-2xl: 1.5rem;
    --radius-full: 9999px;

    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    --shadow-inner: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
}

/* === Typography === */
.text-display-xl {
    font-size: 3.5rem;
    line-height: 1.25;
    font-weight: 800;
}

.text-display-lg {
    font-size: 3rem;
    line-height: 1.25;
    font-weight: 800;
}

.text-display-md {
    font-size: 2.5rem;
    line-height: 1.25;
    font-weight: 700;
}

.text-heading-xl {
    font-size: 2rem;
    line-height: 1.5;
    font-weight: 700;
}

.text-heading-lg {
    font-size: 1.75rem;
    line-height: 1.5;
    font-weight: 600;
}

.text-heading-md {
    font-size: 1.5rem;
    line-height: 1.5;
    font-weight: 600;
}

.text-heading-sm {
    font-size: 1.25rem;
    line-height: 1.5;
    font-weight: 600;
}

.text-body-lg {
    font-size: 1.125rem;
    line-height: 1.75;
    font-weight: 400;
}

.text-body-md {
    font-size: 1rem;
    line-height: 1.5;
    font-weight: 400;
}

.text-body-sm {
    font-size: 0.875rem;
    line-height: 1.5;
    font-weight: 400;
}

.text-caption {
    font-size: 0.75rem;
    line-height: 1.5;
    font-weight: 400;
    color: var(--color-neutral-500);
}

/* === Button Styles === */
.btn-primary {
    background: linear-gradient(135deg, var(--color-primary-600), var(--color-primary-500));
    color: white;
    padding: var(--space-md) var(--space-xl);
    border-radius: var(--radius-lg);
    font-weight: 600;
    font-size: 1rem;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: var(--shadow-md);
}

.btn-primary:hover {
    background: linear-gradient(135deg, var(--color-primary-700), var(--color-primary-600));
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

.btn-secondary {
    background: white;
    color: var(--color-primary-600);
    padding: var(--space-md) var(--space-xl);
    border-radius: var(--radius-lg);
    font-weight: 600;
    font-size: 1rem;
    border: 2px solid var(--color-primary-200);
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-secondary:hover {
    background: var(--color-primary-50);
    border-color: var(--color-primary-300);
    transform: translateY(-2px);
}

.btn-accent {
    background: linear-gradient(135deg, var(--color-accent-500), var(--color-accent-400));
    color: white;
    padding: var(--space-md) var(--space-xl);
    border-radius: var(--radius-lg);
    font-weight: 600;
    font-size: 1rem;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: var(--shadow-md);
}

.btn-accent:hover {
    background: linear-gradient(135deg, var(--color-accent-600), var(--color-accent-500));
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
}

/* === Card Styles === */
.card {
    background: white;
    border-radius: var(--radius-xl);
    padding: var(--space-xl);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-neutral-200);
    transition: all 0.3s ease;
}

.card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}

.card-feature {
    background: white;
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-neutral-100);
    text-align: center;
    transition: all 0.3s ease;
}

.card-feature:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--color-primary-200);
    transform: translateY(-2px);
}

.card-stat {
    background: linear-gradient(135deg, var(--color-primary-50), white);
    border-radius: var(--radius-lg);
    padding: var(--space-lg);
    text-align: center;
    border: 1px solid var(--color-primary-100);
}

/* === Container Styles === */
.container-hero {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-4xl) var(--space-xl);
    text-align: center;
}

.container-section {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
}

.container-narrow {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-xl);
}

/* === Layout Utilities === */
.grid-2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-xl);
}

.grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-lg);
}

.grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-lg);
}

.flex-center {
    display: flex;
    justify-content: center;
    align-items: center;
}

.flex-between {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.flex-column {
    display: flex;
    flex-direction: column;
}

/* === Spacing Utilities === */
.gap-xs { gap: var(--space-xs); }
.gap-sm { gap: var(--space-sm); }
.gap-md { gap: var(--space-md); }
.gap-lg { gap: var(--space-lg); }
.gap-xl { gap: var(--space-xl); }
.gap-2xl { gap: var(--space-2xl); }

.mt-xs { margin-top: var(--space-xs); }
.mt-sm { margin-top: var(--space-sm); }
.mt-md { margin-top: var(--space-md); }
.mt-lg { margin-top: var(--space-lg); }
.mt-xl { margin-top: var(--space-xl); }
.mt-2xl { margin-top: var(--space-2xl); }
.mt-3xl { margin-top: var(--space-3xl); }

.mb-xs { margin-bottom: var(--space-xs); }
.mb-sm { margin-bottom: var(--space-sm); }
.mb-md { margin-bottom: var(--space-md); }
.mb-lg { margin-bottom: var(--space-lg); }
.mb-xl { margin-bottom: var(--space-xl); }
.mb-2xl { margin-bottom: var(--space-2xl); }
.mb-3xl { margin-bottom: var(--space-3xl); }

/* === Badge Styles === */
.badge {
    display: inline-block;
    padding: var(--space-xs) var(--space-md);
    border-radius: var(--radius-full);
    font-size: 0.875rem;
    font-weight: 600;
}

.badge-success {
    background: var(--color-success-light);
    color: var(--color-success);
}

.badge-warning {
    background: var(--color-warning-light);
    color: var(--color-warning);
}

.badge-error {
    background: var(--color-error-light);
    color: var(--color-error);
}

.badge-info {
    background: var(--color-info-light);
    color: var(--color-info);
}

.badge-primary {
    background: var(--color-primary-100);
    color: var(--color-primary-700);
}

/* === Icon Styles === */
.icon-lg {
    font-size: 3rem;
    margin-bottom: var(--space-md);
}

.icon-md {
    font-size: 2rem;
    margin-bottom: var(--space-sm);
}

.icon-primary {
    color: var(--color-primary-500);
}

.icon-accent {
    color: var(--color-accent-500);
}

/* === Gradient Backgrounds === */
.bg-gradient-primary {
    background: linear-gradient(135deg, var(--color-primary-600), var(--color-primary-400));
}

.bg-gradient-accent {
    background: linear-gradient(135deg, var(--color-accent-600), var(--color-accent-400));
}

.bg-gradient-hero {
    background: linear-gradient(180deg, var(--color-primary-50), white);
}

/* === Text Colors === */
.text-primary { color: var(--color-primary-600); }
.text-accent { color: var(--color-accent-500); }
.text-neutral { color: var(--color-neutral-600); }
.text-muted { color: var(--color-neutral-500); }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-error { color: var(--color-error); }

/* === Responsive Design === */
@media (max-width: 768px) {
    .text-display-xl { font-size: 2.5rem; }
    .text-display-lg { font-size: 2rem; }
    .text-display-md { font-size: 1.75rem; }

    .grid-2, .grid-3, .grid-4 {
        grid-template-columns: 1fr;
        gap: var(--space-md);
    }

    .container-hero {
        padding: var(--space-2xl) var(--space-md);
    }

    .container-section {
        padding: var(--space-xl) var(--space-md);
    }
}

/* === Animation Utilities === */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in {
    animation: fadeIn 0.6s ease-out;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(40px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-up {
    animation: slideUp 0.8s ease-out;
}

/* === Focus States === */
button:focus,
input:focus,
textarea:focus {
    outline: 2px solid var(--color-primary-500);
    outline-offset: 2px;
}
"""

    return css
