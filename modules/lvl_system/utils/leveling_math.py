"""
XP-Kurve für das Leveling-System.

Formel (angelehnt an das gängige MEE6/Arcane-Muster, leicht vereinfacht):
    xp_fuer_naechstes_level(level) = 5 * level^2 + 50 * level + 100

Level 0 -> 1 braucht 100 XP, Level 1 -> 2 braucht 155 XP, usw.
Das sorgt für eine sanft ansteigende Kurve, die frühe Level schnell,
hohe Level spürbar langsamer macht.
"""

from __future__ import annotations


def xp_for_next_level(level: int) -> int:
    """XP, die nötig sind, um von `level` auf `level + 1` zu kommen."""
    return 5 * (level ** 2) + 50 * level + 100


def add_xp(current_xp: int, current_level: int, gained_xp: int) -> tuple[int, int, int]:
    """
    Addiert gained_xp auf current_xp und wandelt Levelaufstiege um.

    Returns:
        (neues_xp_im_level, neues_level, anzahl_levelaufstiege)
    """
    xp = current_xp + gained_xp
    level = current_level
    levelups = 0
    needed = xp_for_next_level(level)
    while xp >= needed:
        xp -= needed
        level += 1
        levelups += 1
        needed = xp_for_next_level(level)
    return xp, level, levelups


def total_xp_for_level(level: int) -> int:
    """Kumulative XP, die insgesamt nötig ist, um `level` zu erreichen."""
    return sum(xp_for_next_level(lv) for lv in range(level))
