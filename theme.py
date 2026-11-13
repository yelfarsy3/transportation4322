"""Design tokens shared by Streamlit and the explorer iframe.

Shared colors and fonts come only from .streamlit/config.toml; the few
board-only tones are defined here once. Nothing else should hardcode a hex.
"""
import tomllib
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / '.streamlit' / 'config.toml'
_config = tomllib.loads(CONFIG.read_text(encoding='utf-8'))
_theme = _config['theme']
_side = _theme['sidebar']

TOKENS = {
    # shared with Streamlit (read from config.toml)
    'chart': _theme['backgroundColor'],
    'slate': _theme['secondaryBackgroundColor'],
    'ink': _theme['textColor'],
    'signal': _theme['primaryColor'],
    'line': _theme['borderColor'],
    'undo-light': _theme['redColor'],
    'harbor': _side['backgroundColor'],
    'deck': _side['secondaryBackgroundColor'],
    'mist': _side['textColor'],
    'lane': _side['borderColor'],
    'glow': _side['linkColor'],
    # board-only tones (navy context)
    'muted': '#4E6476',
    'fog': '#93A9B9',
    'undo': '#FF6B6B',
    'undo-text': '#FFC2C2',
    'gauge': '#24425C',
    'gauge-fill': '#C6D5DF',
    'used': '#7FA6BF',
}
BODY_FONT = "'Barlow', 'Arial Narrow', sans-serif"
DISPLAY_FONT = "'Barlow Semi Condensed', 'Barlow', 'Arial Narrow', sans-serif"


def font_face_css():
    """@font-face rules for the iframe, pointing at the same self-hosted files."""
    rules = []
    for face in _theme.get('fontFaces', ()):
        rules.append(f"@font-face{{font-family:'{face['family']}';src:url('/{face['url']}');"
                     f"font-weight:{face.get('weight', 400)};font-style:normal;font-display:swap}}")
    return '\n'.join(rules)


def css_variables():
    body = ';'.join(f'--{name}:{value}' for name, value in TOKENS.items())
    return f':root{{{body};--body:{BODY_FONT};--display:{DISPLAY_FONT}}}'
