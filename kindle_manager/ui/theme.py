BG = "#F4F1EA"
SURFACE = "#FCFBF8"
SURFACE_ALT = "#ECE8DE"
SIDEBAR = "#19352F"
SIDEBAR_HOVER = "#26483F"
TEXT = "#1F2926"
MUTED = "#6F7772"
MUTED_LIGHT = "#AAB7B1"
ACCENT = "#2F7966"
ACCENT_HOVER = "#3B8B76"
ACCENT_SOFT = "#DCEAE4"
GOLD = "#C28A45"
RED = "#B6534B"
BORDER = "#DDD8CD"
SHADOW = "#14000000"


def page_title(title: str, subtitle: str) -> str:
    return (
        f"<div style='color:{TEXT}; font-size:23px; font-weight:700'>{title}</div>"
        f"<div style='color:{MUTED}; font-size:12px; margin-top:3px'>{subtitle}</div>"
    )
