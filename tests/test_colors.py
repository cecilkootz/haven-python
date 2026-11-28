from havenlighting.colors import (
    COLORS,
    PATTERNS,
    SOLID_COLORS,
    color_id_for_name,
    nearest_color_id,
)


def test_catalog_sizes():
    assert len(COLORS) == 55
    assert len(SOLID_COLORS) == 45  # 8 whites + 37 solids
    assert len(PATTERNS) == 9


def test_known_entries():
    assert COLORS[11].name == "RED"
    assert COLORS[11].hex == "#FF0000"
    assert COLORS[1].name == "2700K"
    assert COLORS[80].name == "Sparkle"
    assert COLORS[80].is_pattern


def test_hs_conversion():
    hs = COLORS[11].hs  # pure red
    assert hs[0] == 0.0
    assert hs[1] == 100.0


def test_color_id_for_name_case_insensitive():
    assert color_id_for_name("deep blue") == 25
    assert color_id_for_name("SPARKLE") == 80
    assert color_id_for_name("no such color") is None


def test_nearest_color_id_exact_and_close():
    assert nearest_color_id((255, 0, 0)) == 11  # RED
    assert nearest_color_id((250, 5, 5)) == 11   # still RED
    assert nearest_color_id((30, 160, 255)) == 24  # OCEAN-ish
