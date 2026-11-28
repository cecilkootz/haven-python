"""Haven color catalog.

Extracted from the Haven Lighting Android app (v2.5.67) Hermes bundle:

every color/pattern is an entry with an id, name, and hex color, and all

of them ride the same lightColorId command field. Pattern speed is sent

as patternSpeedId on the same command payload.



White temperature presets use ids 1-8, solid colors 11-57 (with gaps),

pattern groups 33-35, animated patterns 79-88, and 4294967295 is OFF.

"""

from __future__ import annotations



from dataclasses import dataclass

import colorsys

from typing import Final





@dataclass(frozen=True)

class ColorEntry:

    id: int

    name: str

    hex: str  # noqa: A003 - field name matches the app's catalog

    kind: str  # "white" | "solid" | "pattern" | "off"



    @property

    def rgb(self) -> tuple[int, int, int]:

        value = int(self.hex[1:], 16)

        return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)



    @property

    def hs(self) -> tuple[float, float]:

        r, g, b = (c / 255 for c in self.rgb)

        h, l, s = colorsys.rgb_to_hls(r, g, b)

        return (round(h * 360, 1), round(s * 100, 1))



    @property

    def is_pattern(self) -> bool:

        return self.kind == "pattern"



COLORS: Final[dict[int, ColorEntry]] = {
    1: ColorEntry(1, '2700K', '#F8E96C', 'white'),
    2: ColorEntry(2, '3000K', '#F6F08E', 'white'),
    3: ColorEntry(3, '3500K', '#F4F4AC', 'white'),
    4: ColorEntry(4, '3700K', '#F2F4C2', 'white'),
    5: ColorEntry(5, '4000K', '#ECF5DA', 'white'),
    6: ColorEntry(6, '4100K', '#E3F3E9', 'white'),
    7: ColorEntry(7, '4700K', '#DDF1F2', 'white'),
    8: ColorEntry(8, '5000K', '#D6EFF6', 'white'),
    11: ColorEntry(11, 'RED', '#FF0000', 'solid'),
    12: ColorEntry(12, 'FIRE', '#FF1500', 'solid'),
    13: ColorEntry(13, 'PUMPKIN', '#FF3F04', 'solid'),
    14: ColorEntry(14, 'AMBER', '#FFA65E', 'solid'),
    15: ColorEntry(15, 'TANGERINE', '#FDCB5A', 'solid'),
    16: ColorEntry(16, 'MARIGOLD', '#FF9C00', 'solid'),
    17: ColorEntry(17, 'SUNSET', '#FF7800', 'solid'),
    18: ColorEntry(18, 'YELLOW', '#FFEA00', 'solid'),
    19: ColorEntry(19, 'LIME', '#BBFF00', 'solid'),
    20: ColorEntry(20, 'LIGHT GREEN', '#8CFF00', 'solid'),
    21: ColorEntry(21, 'GREEN', '#20A301', 'solid'),
    22: ColorEntry(22, 'SEA FOAM', '#04F57B', 'solid'),
    23: ColorEntry(23, 'TURQUOISE', '#00C7F3', 'solid'),
    24: ColorEntry(24, 'OCEAN', '#1E98F3', 'solid'),
    25: ColorEntry(25, 'DEEP BLUE', '#2160FF', 'solid'),
    26: ColorEntry(26, 'VIOLET', '#BC63F4', 'solid'),
    27: ColorEntry(27, 'PURPLE', '#A66AFF', 'solid'),
    28: ColorEntry(28, 'LAVENDER', '#C26AFF', 'solid'),
    29: ColorEntry(29, 'PINK', '#FF00EA', 'solid'),
    30: ColorEntry(30, 'HOT PINK', '#FF008A', 'solid'),
    33: ColorEntry(33, 'WARM COLORS', '#F8E96C', 'pattern'),
    34: ColorEntry(34, 'COOL COLORS', '#2E8FFD', 'pattern'),
    35: ColorEntry(35, 'ALL COLORS', '#FF0000', 'pattern'),
    39: ColorEntry(39, 'ORANGE', '#FF5E00', 'solid'),
    40: ColorEntry(40, 'LEMON', '#FFC000', 'solid'),
    41: ColorEntry(41, 'PALE GREEN', '#59ED02', 'solid'),
    42: ColorEntry(42, 'EMERALD', '#23BD00', 'solid'),
    44: ColorEntry(44, 'ARCTIC', '#17E57D', 'solid'),
    45: ColorEntry(45, 'SKY', '#00FCFF', 'solid'),
    46: ColorEntry(46, 'WATER', '#00CCFF', 'solid'),
    47: ColorEntry(47, 'SAPPHIRE', '#217FFF', 'solid'),
    48: ColorEntry(48, 'LIGHT BLUE', '#2E8FFD', 'solid'),
    50: ColorEntry(50, 'ORCHID', '#967FFE', 'solid'),
    51: ColorEntry(51, 'LILAC', '#EC6AFF', 'solid'),
    52: ColorEntry(52, 'BUBBLEGUM', '#FF00BB', 'solid'),
    53: ColorEntry(53, 'FLAMINGO', '#ED2693', 'solid'),
    54: ColorEntry(54, 'DEEP PINK', '#FF3D8F', 'solid'),
    55: ColorEntry(55, 'AQUA', '#17E5A8', 'solid'),
    56: ColorEntry(56, 'APPLE GREEN', '#27D600', 'solid'),
    57: ColorEntry(57, 'ROYAL BLUE', '#6141FF', 'solid'),
    79: ColorEntry(79, '2 Wave', '#FFFFFF', 'pattern'),
    80: ColorEntry(80, 'Sparkle', '#FFFFFF', 'pattern'),
    81: ColorEntry(81, '1 Wave', '#FFFFFF', 'pattern'),
    83: ColorEntry(83, 'Cascade', '#FFFFFF', 'pattern'),
    84: ColorEntry(84, '3 Wave', '#FFFFFF', 'pattern'),
    88: ColorEntry(88, 'USA', '#FFFFFF', 'pattern'),
    4294967295: ColorEntry(4294967295, 'OFF', '#515151', 'off'),
}

SOLID_COLORS: Final = {k: c for k, c in COLORS.items() if c.kind in ("white", "solid")}
PATTERNS: Final = {k: c for k, c in COLORS.items() if c.is_pattern}

def color_id_for_name(name: str) -> int | None:
    """Case-insensitive color/pattern lookup by name."""
    wanted = name.strip().lower()
    for entry in COLORS.values():
        if entry.name.lower() == wanted:
            return entry.id
    return None

def nearest_color_id(rgb: tuple[int, int, int]) -> int:
    """Closest white/solid catalog color to an RGB triple."""
    best, best_d = None, None
    for entry in SOLID_COLORS.values():
        d = sum((a - b) ** 2 for a, b in zip(entry.rgb, rgb))
        if best_d is None or d < best_d:
            best, best_d = entry, d
    assert best is not None
    return best.id

