import pytest

from gfmodel.contrast import contrast_ratio, parse_tokens

CSS = """
:root { --bg: #ffffff; --ink: #000; --c-x: #123456; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #101010; --ink: #eee; }
}
:root[data-theme="dark"] { --bg: #101010; --ink: #eeeeee; }
.other { --bg: #ff0000; }
"""


def test_black_on_white_is_21():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=1e-9)


def test_threshold_grey_is_about_4_54():
    assert contrast_ratio("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)
    assert contrast_ratio("#ffffff", "#767676") == pytest.approx(4.54, abs=0.01)


def test_parse_tokens_reads_the_three_blocks():
    t = parse_tokens(CSS)
    assert t["light"] == {"bg": "#ffffff", "ink": "#000000", "c-x": "#123456"}
    assert t["dark_media"]["bg"] == "#101010"
    assert t["dark_media"]["ink"] == "#eeeeee"
    assert t["dark"] == {"bg": "#101010", "ink": "#eeeeee"}
