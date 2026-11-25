"""WCAG 2.x contrast ratio and a reader for the colour tokens in docs/style.css."""

import re

_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_PROP = re.compile(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\s*;")


def _rgb(color: str) -> tuple[int, int, int]:
    m = _HEX.match(color.strip())
    if not m:
        raise ValueError(f"not a hex colour: {color!r}")
    h = m.group(1)
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _channel(v: int) -> float:
    c = v / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b = (_channel(v) for v in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _tokens(block: str) -> dict[str, str]:
    out = {}
    for name, value in _PROP.findall(block):
        out[name] = "#" + "".join(ch * 2 for ch in value[1:]) if len(value) == 4 else value
        out[name] = out[name].lower()
    return out


def parse_tokens(css: str) -> dict[str, dict[str, str]]:
    """Hex custom properties of ``:root`` (light), the dark media block and ``[data-theme=dark]``."""
    light = re.search(r"^:root\s*\{(.*?)\}", css, re.S | re.M)
    media = re.search(
        r'@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme="light"\]\)\s*\{(.*?)\}',
        css,
        re.S,
    )
    dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S)
    return {
        "light": _tokens(light.group(1)) if light else {},
        "dark_media": _tokens(media.group(1)) if media else {},
        "dark": _tokens(dark.group(1)) if dark else {},
    }
