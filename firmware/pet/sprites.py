"""1-bit art as text rows. '#' is ink, '.' is background.

Pure data, no displayio: ui.py turns these into bitmaps. Our own drawings in
the style of the original's dot-matrix LCD. T10 can redraw any of it; keep
the names and sizes and nothing else needs to change.

Three 1-bit sheets:
    pet frames   16x16, drawn at 8x: Sprout, the pet, in every pose
    icons        12x12, drawn at 4x: menu icons, attention, the want bubble
    fx           8x8, drawn at 8x next to the pet: food, cup, hearts,
                 sparkles, Z's, the flush wave, the UFO, the game's arrow
                 and digits
and the poop, 8x8 at 8x in colour (POOP_FRAMES, POOP_COLORS).
"""

PET_SIZE = 16
ICON_SIZE = 12
FX_SIZE = 8

_BLANK16 = "................"

# Sprout: our own round critter in outline, the way the original's LCD pets
# are drawn, with a leaf on top, dot eyes and stubby feet. Its feet stand on
# row 13 in every standing pose.
_IDLE0 = (
    "................",
    "........##......",
    ".......###......",
    ".......#........",
    ".....######.....",
    "...##......##...",
    "..#..##..##..#..",
    "..#..##..##..#..",
    "..#..........#..",
    ".##..#....#..##.",
    "..#...####...#..",
    "...#........#...",
    "....########....",
    "....###..###....",
    "................",
    "................",
)

# Squashed one row (the empty row under the eyes goes), feet still down:
# alternating with _IDLE0 it breathes.
_IDLE1 = (_BLANK16,) + _IDLE0[:8] + _IDLE0[9:]

# Eyes squeezed shut, mouth wide open, arms up.
_HAPPY = (
    "................",
    "........##......",
    ".......###......",
    ".......#........",
    ".....######.....",
    "...##......##...",
    "..#..#....#..#..",
    "..#.#.#..#.#.#..",
    ".##..........##.",
    "..#..######..#..",
    "..#...#..#...#..",
    "...#...##...#...",
    "....########....",
    "....###..###....",
    "................",
    "................",
)

# Same pose one row higher: alternating with _HAPPY is the happy hop. Hops
# are drawn into the frame instead of moving the sprite: on the board moving a
# 128x128 sprite redraws its old and new rectangles (118 ms), a frame swap
# redraws one (50-60 ms).
_HAPPY_UP = _HAPPY[1:] + (_BLANK16,)

# Eyes low, a frown, arms hanging.
_SAD = (
    "................",
    "........##......",
    ".......###......",
    ".......#........",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#..##..##..#..",
    "..#..##..##..#..",
    "..#..........#..",
    ".##...####...##.",
    "...#.#....#.#...",
    "....########....",
    "....###..###....",
    "................",
    "................",
)

# Looking away: one eye off to the side, no mouth, the leaf drooping.
_SULK = (
    "................",
    "................",
    ".......#........",
    ".....###........",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......#..",
    "..#..........#..",
    ".##..........##.",
    "...#........#...",
    "....########....",
    "....###..###....",
    "................",
    "................",
)

# Side on, facing left (flip_x to face right): eats, and turns in the game.
_SIDE = (
    "................",
    ".........##.....",
    "........###.....",
    "........#.......",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......#..",
    "..#..........##.",
    "..###........#..",
    "...#........#...",
    "....########....",
    "...###...###....",
    "................",
    "................",
)

# Side on with the mouth wide open: the bite.
_SIDE_EAT = _SIDE[:9] + (
    "..###........##.",
    "....#........#..",
    "...##.......#...",
) + _SIDE[12:]

# Eyes to one side and a frown, the whole body one column over: shaking its
# head "no". flip_x swings it to the other side.
_NO = (
    "................",
    ".......##.......",
    "......###.......",
    "......#.........",
    "....######......",
    "..##......##....",
    ".#.##..##...#...",
    ".#.##..##...#...",
    ".#..........#...",
    "##..........##..",
    ".#...####...#...",
    "..#.#....#.#....",
    "...########.....",
    "...###..###.....",
    "................",
    "................",
)

# Eyes shut, mouth a big O.
_YAWN = (
    "................",
    "........##......",
    ".......###......",
    ".......#........",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##....##.#..",
    "..#....##....#..",
    ".##...#..#...##.",
    "..#...#..#...#..",
    "...#...##...#...",
    "....########....",
    "....###..###....",
    "................",
    "................",
)

# Lying flat on the floor, the leaf flopped over to the left.
_LIE = (_BLANK16,) * 6 + (
    "...##...........",
    ".....##.........",
    "....########....",
    "..##........##..",
    ".#...##..##...#.",
    ".#...##..##...#.",
    ".#.....##.....#.",
    "..############..",
    "................",
    "................",
)

# Lying flat, eyes shut: asleep.
_LIE_SLEEP = _LIE[:10] + (
    ".#............#.",
    ".#..###..###..#.",
) + _LIE[12:]

# Beamed up into the UFO: lying, lifted two rows to the saucer's underside,
# then shrunk to a speck just under it.
_RISE1 = _LIE[2:] + (_BLANK16,) * 2
_RISE2 = (_BLANK16,) * 7 + (
    "......####......",
    ".....#.##.#.....",
    "......####......",
) + (_BLANK16,) * 6

# Frame order in each critter's block of the pet sprite sheet (the egg frames
# are the same in every block). ui.py looks frames up by name.
PET_FRAMES = (
    "idle0",
    "idle1",
    "happy",
    "happy_up",
    "sad",
    "sulk",
    "side",
    "side_eat",
    "no",
    "yawn",
    "lie",
    "lie_sleep",
    "rise1",
    "rise2",
    "egg",
    "egg_tilt",
    "egg_crack1",
    "egg_crack2",
)
_PET_ART = {
    "idle0": _IDLE0,
    "idle1": _IDLE1,
    "happy": _HAPPY,
    "happy_up": _HAPPY_UP,
    "sad": _SAD,
    "sulk": _SULK,
    "side": _SIDE,
    "side_eat": _SIDE_EAT,
    "no": _NO,
    "yawn": _YAWN,
    "lie": _LIE,
    "lie_sleep": _LIE_SLEEP,
    "rise1": _RISE1,
    "rise2": _RISE2,
}

# ---- More critters ----------------------------------------------------------
# A new pet hatches from an egg as one of CHARACTERS, picked at random
# (pet.game). Our own designs, not Bandai's. Each has every frame in
# PET_FRAMES, drawn to Sprout's marks so every animation fits them all: feet
# on row 13 standing; happy poses inside columns 1-14 with row 0 empty (the
# hearts and the sparkle sit just outside, and happy_up is happy one row
# higher); side on, the mouth at the left edge on rows 9-11, where the food
# goes; lying low enough to stay clear of the Z's top-right.


def _right(rows):
    """Shifted one column right: a top leaning back as it turns side on."""
    return tuple("." + r[:-1] for r in rows)


def _left(rows):
    """Shifted one column left, like the whole body in the head shake."""
    return tuple(r[1:] + "." for r in rows)


def _critter(idle0, squash_row, happy, sad, sulk, side, side_eat, no, yawn, lie):
    """A critter's frames by name (all but the egg's), the in-between ones made the way Sprout's are."""
    return {
        "idle0": idle0,
        "idle1": (_BLANK16,) + idle0[:squash_row] + idle0[squash_row + 1 :],
        "happy": happy,
        "happy_up": happy[1:] + (_BLANK16,),
        "sad": sad,
        "sulk": sulk,
        "side": side,
        "side_eat": side_eat,
        "no": no,
        "yawn": yawn,
        "lie": lie,
        "lie_sleep": lie[:10] + (".#............#.", ".#..###..###..#.") + lie[12:],
        "rise1": lie[2:] + (_BLANK16,) * 2,
        "rise2": _RISE2,
    }


# Dabble: chubby and always hungry, with big duck lips, a two-hair tuft and
# wide feet.
_DABBLE_IDLE0 = (
    _BLANK16,
    _BLANK16,
    "......#...#.....",
    ".......#.#......",
    ".....######.....",
    "...##......##...",
    "..#..##..##..#..",
    "..#..##..##..#..",
    "..#.########.#..",
    ".##.#......#.##.",
    "..#..######..#..",
    "...#........#...",
    "....########....",
    "...####..####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_HAPPY = (
    _BLANK16,
    _BLANK16,
    "......#...#.....",
    ".......#.#......",
    ".....######.....",
    "...##......##...",
    "..#..#....#..#..",
    "..#.#.#..#.#.#..",
    ".##.########.##.",
    "..#.#......#.#..",
    "..#.#......#.#..",
    "...#.######.#...",
    "....########....",
    "...####..####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_SAD = (
    _BLANK16,
    _BLANK16,
    "................",
    "......##.##.....",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#..##..##..#..",
    "..#..##..##..#..",
    "..#.########.#..",
    ".##.#......#.##.",
    "...#.######.#...",
    "....########....",
    "...####..####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_SULK = (
    _BLANK16,
    _BLANK16,
    "................",
    ".....##.##......",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......#..",
    "#####........#..",
    "#...#........##.",
    "#####.......#...",
    "....########....",
    "...####..####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_SIDE = (
    _BLANK16,
    _BLANK16,
    ".......#...#....",
    "........#.#.....",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......#..",
    "#####........##.",
    "#...#........#..",
    "#####.......#...",
    "....########....",
    "..####...####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_SIDE_EAT = _DABBLE_SIDE[:8] + (
    "#####.......#...",
    "#...#........##.",
    "....#........#..",
    "#####.......#...",
) + _DABBLE_SIDE[12:]
_DABBLE_NO = (
    _BLANK16,
    _BLANK16,
    ".....#...#......",
    "......#.#.......",
    "....######......",
    "..##......##....",
    ".#.##..##...#...",
    ".#.##..##...#...",
    ".#..........#...",
    "##.#######..##..",
    ".#.#.....#..#...",
    "..#.#######.#...",
    "...########.....",
    "..####..####....",
    _BLANK16,
    _BLANK16,
)
_DABBLE_YAWN = (
    _BLANK16,
    _BLANK16,
    "......#...#.....",
    ".......#.#......",
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##....##.#..",
    "..#..######..#..",
    ".##.#......#.##.",
    "..#.#......#.#..",
    "...#.######.#...",
    "....########....",
    "...####..####...",
    _BLANK16,
    _BLANK16,
)
_DABBLE_LIE = (_BLANK16,) * 6 + (
    "..#.#...........",
    "...#.#..........",
    "....########....",
    "..##........##..",
    ".#...##..##...#.",
    ".#...##..##...#.",
    ".#..########..#.",
    "..############..",
    _BLANK16,
    _BLANK16,
)

# Ribbon: a big bow on top, lashes and a little dress.
_RIBBON_BOW = (
    _BLANK16,
    "....###..###....",
    "....#..##..#....",
    "....###..###....",
)
_RIBBON_DRESS = (
    "...#........#...",
    "..############..",
    "....##....##....",
)
_RIBBON_IDLE0 = _RIBBON_BOW + (
    ".....######.....",
    "...##......##...",
    "..#.###..###.#..",
    "..#..##..##..#..",
    "..#..........#..",
    ".##..#....#..##.",
    "..#...####...#..",
) + _RIBBON_DRESS + (_BLANK16, _BLANK16)
_RIBBON_HAPPY = _RIBBON_BOW + (
    ".....######.....",
    "...##......##...",
    "..#.##....##.#..",
    "..#.#.#..#.#.#..",
    ".##..........##.",
    "..#..######..#..",
    "..#...#..#...#..",
    "...#...##...#...",
    "..############..",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_RIBBON_SAD = _RIBBON_BOW + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.###..###.#..",
    "..#..##..##..#..",
    "..#..........#..",
    ".##...####...##.",
    "...#.#....#.#...",
    "..############..",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_RIBBON_SULK = _RIBBON_BOW + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..####.......#..",
    "..#.##.......#..",
    "..#..........#..",
    ".##..........##.",
) + _RIBBON_DRESS + (_BLANK16, _BLANK16)
_RIBBON_SIDE = _right(_RIBBON_BOW) + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..####.......#..",
    "..#.##.......#..",
    "..#..........##.",
    "..###........#..",
) + _RIBBON_DRESS + (_BLANK16, _BLANK16)
_RIBBON_SIDE_EAT = _RIBBON_SIDE[:9] + (
    "..###........##.",
    "....#........#..",
    "...##.......#...",
) + _RIBBON_SIDE[12:]
_RIBBON_NO = _left(_RIBBON_BOW) + (
    "....######......",
    "..##......##....",
    ".#.###.###..#...",
    ".#.##..##...#...",
    ".#..........#...",
    "##..........##..",
    ".#...####...#...",
    "..#.#....#.#....",
    ".############...",
    "...##....##.....",
    _BLANK16,
    _BLANK16,
)
_RIBBON_YAWN = _RIBBON_BOW + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##....##.#..",
    "..#....##....#..",
    ".##...#..#...##.",
    "..#...#..#...#..",
    "...#...##...#...",
    "..############..",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_RIBBON_LIE = (_BLANK16,) * 6 + (
    "..#.#...........",
    "...#............",
    "..#.#######.....",
    "..##........##..",
    ".#..###..###..#.",
    ".#...##..##...#.",
    ".#.....##.....#.",
    "..############..",
    _BLANK16,
    _BLANK16,
)

# Heartlet: a heart on top (its point is the stalk; it droops when sad), blush
# cheeks and a sweet smile.
_HEARTLET_TOP = (
    _BLANK16,
    "......##.##.....",
    "......#####.....",
    ".......###......",
    "........#.......",
)
_HEARTLET_TOP_DROOP = (
    _BLANK16,
    _BLANK16,
    ".....##.##......",
    ".....#####......",
    "......###.......",
)
_HEARTLET_IDLE0 = _HEARTLET_TOP + (
    ".....######.....",
    "...##......##...",
    "..#..##..##..#..",
    "..#..##..##..#..",
    ".##.##....##.##.",
    "..#..#....#..#..",
    "...#..####..#...",
    "....########....",
    "....###..###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_HAPPY = _HEARTLET_TOP + (
    ".....######.....",
    "...##......##...",
    "..#..#....#..#..",
    ".##.#.#..#.#.##.",
    "..#.##....##.#..",
    "..#..######..#..",
    "...#..#..#..#...",
    "....########....",
    "....###..###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_SAD = _HEARTLET_TOP_DROOP + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#..##..##..#..",
    "..#.###..###.#..",
    ".##...####...##.",
    "...#.#....#.#...",
    "....########....",
    "....###..###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_SULK = _HEARTLET_TOP_DROOP + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..####.......#..",
    ".##..........##.",
    "...#........#...",
    "....########....",
    "....###..###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_SIDE = _right(_HEARTLET_TOP) + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..####.......##.",
    "..###........#..",
    "...#........#...",
    "....########....",
    "...###...###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_SIDE_EAT = _HEARTLET_SIDE[:9] + (
    "..####.......##.",
    "....#........#..",
    "...#........#...",
) + _HEARTLET_SIDE[12:]
_HEARTLET_NO = _left(_HEARTLET_TOP) + (
    "....######......",
    "..##......##....",
    ".#.##..##...#...",
    ".#.##..##...#...",
    "##.##.##....##..",
    ".#...####...#...",
    "..#.#....#.#....",
    "...########.....",
    "...###..###.....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_YAWN = _HEARTLET_TOP + (
    ".....######.....",
    "...##......##...",
    "..#.##....##.#..",
    "..#....##....#..",
    ".##.#.#..#.#.##.",
    "..#...#..#...#..",
    "...#...##...#...",
    "....########....",
    "....###..###....",
    _BLANK16,
    _BLANK16,
)
_HEARTLET_LIE = (_BLANK16,) * 5 + (
    ".##.##..........",
    ".#####..........",
    "..###...........",
    "...#########....",
    "..##........##..",
    ".#..###..###..#.",
    ".#...##..##...#.",
    ".#.....##.....#.",
    "..############..",
    _BLANK16,
    _BLANK16,
)

# Lyra: tall bunny ears that flop down when sad or sulking, and a little "w"
# mouth.
_LYRA_EARS = (
    _BLANK16,
    ".....#....#.....",
    "....#.#..#.#....",
    "....#.#..#.#....",
    "....#.#..#.#....",
)
_LYRA_EARS_DROOP = (
    _BLANK16,
    _BLANK16,
    _BLANK16,
    "..###......###..",
    "....##....##....",
)
_LYRA_IDLE0 = _LYRA_EARS + (
    ".....######.....",
    "...##......##...",
    "..#..##..##..#..",
    "..#..##..##..#..",
    ".##...#..#...##.",
    "..#....##....#..",
    "...#........#...",
    "....########....",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_HAPPY = _LYRA_EARS + (
    ".....######.....",
    "...##......##...",
    "..#..#....#..#..",
    ".##.#.#..#.#.##.",
    "..#..######..#..",
    "..#...#..#...#..",
    "...#...##...#...",
    "....########....",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_SAD = _LYRA_EARS_DROOP + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#..##..##..#..",
    "..#..##..##..#..",
    ".##...####...##.",
    "...#.#....#.#...",
    "....########....",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_SULK = _LYRA_EARS_DROOP + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......#..",
    ".##..........##.",
    "...#........#...",
    "....########....",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_SIDE = _right(_LYRA_EARS) + (
    ".....######.....",
    "...##......##...",
    "..#..........#..",
    "..#.##.......#..",
    "..#.##.......##.",
    "..##.........#..",
    "...#........#...",
    "....########....",
    "...##.....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_SIDE_EAT = _LYRA_SIDE[:9] + (
    "..#.##.......##.",
    "..###........#..",
    "....#.......#...",
) + _LYRA_SIDE[12:]
_LYRA_NO = _left(_LYRA_EARS) + (
    "....######......",
    "..##......##....",
    ".#.##..##...#...",
    ".#.##..##...#...",
    "##...#..#...##..",
    ".#....##....#...",
    "..#.#....#.#....",
    "...########.....",
    "...##....##.....",
    _BLANK16,
    _BLANK16,
)
_LYRA_YAWN = _LYRA_EARS + (
    ".....######.....",
    "...##......##...",
    "..#.##....##.#..",
    "..#....##....#..",
    ".##...#..#...##.",
    "..#...#..#...#..",
    "...#...##...#...",
    "....########....",
    "....##....##....",
    _BLANK16,
    _BLANK16,
)
_LYRA_LIE = (_BLANK16,) * 6 + (
    ".....#...#......",
    "....#.#.#.#.....",
    "....########....",
    "..##........##..",
    ".#...##..##...#.",
    ".#...##..##...#.",
    ".#....#..#....#.",
    "..############..",
    _BLANK16,
    _BLANK16,
)

# The egg every pet hatches from (pet.anim.HATCH): spotted; it leans to wobble
# (flip_x leans it the other way), then cracks across the middle, twice.
_EGG = (
    _BLANK16,
    _BLANK16,
    _BLANK16,
    "......####......",
    ".....#....#.....",
    "....#.##...#....",
    "....#.##...#....",
    "...#........#...",
    "...#........#...",
    "...#........#...",
    "...#....##..#...",
    "...#....##..#...",
    "....#......#....",
    ".....######.....",
    _BLANK16,
    _BLANK16,
)
_EGG_TILT = _left(_EGG[:8]) + _EGG[8:]
_EGG_CRACK1 = _EGG[:7] + (
    "...#.#.#....#...",
    "...##.#.#...#...",
) + _EGG[9:]
_EGG_CRACK2 = _EGG[:7] + (
    "...#.#.#.#.##...",
    "...##.#.#.#.#...",
) + _EGG[9:]
_EGG_ART = {
    "egg": _EGG,
    "egg_tilt": _EGG_TILT,
    "egg_crack1": _EGG_CRACK1,
    "egg_crack2": _EGG_CRACK2,
}

# Who can hatch, and the order of their blocks in the pet sprite sheet.
CHARACTERS = ("sprout", "dabble", "ribbon", "heartlet", "lyra")
_ART = {
    "sprout": _PET_ART,
    "dabble": _critter(
        _DABBLE_IDLE0, 7, _DABBLE_HAPPY, _DABBLE_SAD, _DABBLE_SULK,
        _DABBLE_SIDE, _DABBLE_SIDE_EAT, _DABBLE_NO, _DABBLE_YAWN, _DABBLE_LIE,
    ),
    "ribbon": _critter(
        _RIBBON_IDLE0, 8, _RIBBON_HAPPY, _RIBBON_SAD, _RIBBON_SULK,
        _RIBBON_SIDE, _RIBBON_SIDE_EAT, _RIBBON_NO, _RIBBON_YAWN, _RIBBON_LIE,
    ),
    "heartlet": _critter(
        _HEARTLET_IDLE0, 7, _HEARTLET_HAPPY, _HEARTLET_SAD, _HEARTLET_SULK,
        _HEARTLET_SIDE, _HEARTLET_SIDE_EAT, _HEARTLET_NO, _HEARTLET_YAWN, _HEARTLET_LIE,
    ),
    "lyra": _critter(
        _LYRA_IDLE0, 7, _LYRA_HAPPY, _LYRA_SAD, _LYRA_SULK,
        _LYRA_SIDE, _LYRA_SIDE_EAT, _LYRA_NO, _LYRA_YAWN, _LYRA_LIE,
    ),
}


_EAT = (  # burger
    "............",
    "...######...",
    "..########..",
    ".##########.",
    "............",
    "############",
    "............",
    ".##########.",
    ".##########.",
    "..########..",
    "............",
    "............",
)

_DRINK = (  # cup with a straw
    ".......#....",
    "......#.....",
    "......#.....",
    ".##########.",
    ".#........#.",
    ".#........#.",
    ".##########.",
    ".##########.",
    "..########..",
    "..########..",
    "...######...",
    "............",
)

_SLEEP = (  # crescent moon: lights off
    "....####....",
    "..####......",
    ".####.......",
    ".###........",
    "####........",
    "####........",
    "####........",
    ".###........",
    ".####.......",
    "..####......",
    "....####....",
    "............",
)

_PLAY = (  # game controller: D-pad on the left, four buttons on the right
    "............",
    "............",
    "..########..",
    ".#........#.",
    "#..#....#..#",
    "#.###..#.#.#",
    "#..#....#..#",
    "#..........#",
    "#...####...#",
    "#..#....#..#",
    ".##......##.",
    "............",
)

_CLEAN = (  # rubber duck: the flush
    "............",
    "..###.......",
    ".#####......",
    ".#.###......",
    "######....#.",
    "..####...##.",
    "..#########.",
    ".##########.",
    ".##########.",
    "..########..",
    "...######...",
    "............",
)

_AFFECTION = (  # heart
    "............",
    "..##....##..",
    ".####..####.",
    "############",
    "############",
    "############",
    ".##########.",
    "..########..",
    "...######...",
    "....####....",
    ".....##.....",
    "............",
)

_STATS = (  # bar chart
    "............",
    ".........##.",
    ".........##.",
    "......##.##.",
    "......##.##.",
    "...##.##.##.",
    "...##.##.##.",
    "##.##.##.##.",
    "##.##.##.##.",
    "##.##.##.##.",
    "############",
    "............",
)

_ATTENTION = (  # exclamation mark
    "....####....",
    "....####....",
    "....####....",
    "....####....",
    "....####....",
    ".....##.....",
    ".....##.....",
    "............",
    "............",
    "....####....",
    "....####....",
    "............",
)

# Icon order in the icon sprite sheet. The first six are the menu actions and
# double as the stat icons on the stats page.
ICON_NAMES = ("eat", "drink", "sleep", "play", "clean", "affection", "stats", "attention")
_ICON_ART = {
    "eat": _EAT,
    "drink": _DRINK,
    "sleep": _SLEEP,
    "play": _PLAY,
    "clean": _CLEAN,
    "affection": _AFFECTION,
    "stats": _STATS,
    "attention": _ATTENTION,
}


# ---- fx: 8x8, drawn at 8x beside the pet ------------------------------------
# Props sit on the floor: their ink ends on row 6, and the stage puts them at
# y = 7 so it lines up with the pet's feet. Bites come off the right side,
# where the pet stands.

_FX_ART = {
    "food0": (  # burger
        "........",
        "..####..",
        ".######.",
        "########",
        "........",
        "########",
        ".######.",
        "........",
    ),
    "food1": (
        "........",
        "..###...",
        ".#####..",
        "#####...",
        "........",
        "#####...",
        ".###....",
        "........",
    ),
    "food2": (
        "........",
        "..#.....",
        ".##.....",
        "###.....",
        "........",
        "##......",
        ".#......",
        "........",
    ),
    "cup0": (  # full
        "........",
        "#......#",
        "########",
        "########",
        "########",
        ".######.",
        "..####..",
        "........",
    ),
    "cup1": (
        "........",
        "#......#",
        "#......#",
        "########",
        "########",
        ".######.",
        "..####..",
        "........",
    ),
    "cup2": (
        "........",
        "#......#",
        "#......#",
        "#......#",
        "########",
        ".######.",
        "..####..",
        "........",
    ),
    "cup3": (  # empty
        "........",
        "#......#",
        "#......#",
        "#......#",
        "#......#",
        ".#....#.",
        "..####..",
        "........",
    ),
    "wave": (  # the flush: two stacked make a column of water sweeping across
        ".##..##.",
        "#..##..#",
        "........",
        "........",
        ".##..##.",
        "#..##..#",
        "........",
        "........",
    ),
    "heart": (
        "........",
        ".##.##..",
        "#######.",
        "#######.",
        ".#####..",
        "..###...",
        "...#....",
        "........",
    ),
    "sparkle0": (
        "....#...",
        "....#...",
        "..#.#.#.",
        "...###..",
        ".#######",
        "...###..",
        "..#.#.#.",
        "....#...",
    ),
    "sparkle1": (
        "........",
        ".#...#..",
        "..#.#...",
        "...#....",
        "..#.#...",
        ".#...#..",
        "........",
        "........",
    ),
    "z_small": (
        "........",
        "........",
        "........",
        ".####...",
        "...#....",
        "..#.....",
        ".####...",
        "........",
    ),
    "z_big": (
        "######..",
        "....#...",
        "...#....",
        "..#.....",
        ".#......",
        "######..",
        "........",
        "........",
    ),
    "arrow": (  # points left; flip_x points right. 6 wide, so it clears the pet
        "........",
        "..#.....",
        ".##.....",
        "######..",
        "######..",
        ".##.....",
        "..#.....",
        "........",
    ),
    "d0": (
        ".###....",
        "#...#...",
        "#..##...",
        "#.#.#...",
        "##..#...",
        "#...#...",
        ".###....",
        "........",
    ),
    "d1": (
        "..#.....",
        ".##.....",
        "..#.....",
        "..#.....",
        "..#.....",
        "..#.....",
        ".###....",
        "........",
    ),
    "d2": (
        ".###....",
        "#...#...",
        "....#...",
        "...#....",
        "..#.....",
        ".#......",
        "#####...",
        "........",
    ),
    "d3": (
        "#####...",
        "...#....",
        "..#.....",
        "...#....",
        "....#...",
        "#...#...",
        ".###....",
        "........",
    ),
    "d4": (
        "...#....",
        "..##....",
        ".#.#....",
        "#..#....",
        "#####...",
        "...#....",
        "...#....",
        "........",
    ),
    "d5": (
        "#####...",
        "#.......",
        "####....",
        "....#...",
        "....#...",
        "#...#...",
        ".###....",
        "........",
    ),
    # The UFO that takes the pet away: a 16-wide saucer as two tiles side by
    # side (ufo_l at x, ufo_r at x + 8), the beam under its middle, and the
    # tiny one left in the sky afterwards.
    "ufo_l": (
        "......##",
        "....##..",
        "...#....",
        ".#######",
        "#..#..#.",
        ".#######",
        "....####",
        "........",
    ),
    "ufo_r": (
        "##......",
        "..##....",
        "....#...",
        "#######.",
        ".#..#..#",
        "#######.",
        "####....",
        "........",
    ),
    "beam": (
        "...##...",
        "..#..#..",
        "..#..#..",
        ".#....#.",
        ".#....#.",
        "#......#",
        "#......#",
        "#......#",
    ),
    "ufo_tiny": (
        "........",
        "...##...",
        "..####..",
        "########",
        ".#.##.#.",
        "..####..",
        "........",
        "........",
    ),
    "shell": (  # a piece of eggshell flying off as it hatches (flip_x for the other side)
        "..###...",
        ".#...#..",
        "#..##.#.",
        "#.#.#.#.",
        ".#.#.#..",
        "........",
        "........",
        "........",
    ),
    "slash": (
        "....#...",
        "....#...",
        "...#....",
        "..#.....",
        ".#......",
        "#.......",
        "#.......",
        "........",
    ),
}

# Tile order in the fx sprite sheet.
FX_NAMES = (
    "food0",
    "food1",
    "food2",
    "cup0",
    "cup1",
    "cup2",
    "cup3",
    "wave",
    "heart",
    "sparkle0",
    "sparkle1",
    "z_small",
    "z_big",
    "arrow",
    "d0",
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "slash",
    "ufo_l",
    "ufo_r",
    "beam",
    "ufo_tiny",
    "shell",
)


def pet_sheet():
    """Every critter's frames stacked vertically, PET_SIZE rows each: one block
    per critter in CHARACTERS order, PET_FRAMES order within each."""
    rows = []
    for character in CHARACTERS:
        art = _ART[character]
        for name in PET_FRAMES:
            rows.extend(art[name] if name in art else _EGG_ART[name])
    return rows


def icon_sheet():
    """All icons stacked vertically, ICON_SIZE rows each, in ICON_NAMES order."""
    rows = []
    for name in ICON_NAMES:
        rows.extend(_ICON_ART[name])
    return rows


def pet_frame_index(name, character=CHARACTERS[0]):
    return CHARACTERS.index(character) * len(PET_FRAMES) + PET_FRAMES.index(name)


def icon_index(name):
    return ICON_NAMES.index(name)


def fx_sheet():
    """All fx tiles stacked vertically, FX_SIZE rows each, in FX_NAMES order."""
    rows = []
    for name in FX_NAMES:
        rows.extend(_FX_ART[name])
    return rows


def fx_index(name):
    return FX_NAMES.index(name)


# ---- The poop: 8x8 at 8x ----------------------------------------------------
# A solid lump in the LCD's ink, the way the original draws it: a small peak,
# stepping down on both sides to a wide flat base, with a light hole for a
# highlight. Two little
# stink squiggles float clear of it, the left one higher, and flip > / < to
# wiggle (POOP_FRAMES 0 and 1). A poop with another stacked on top of it shows POOP_PLAIN (no
# squiggles), so the pile reads. Everything stays in columns 0-5: the pile
# puts poops 7 apart, so neighbours keep a one-column gap.
# '.' is see-through; the other characters index POOP_COLORS.

_POOP_LUMP = (
    "..#.....",
    ".###....",
    ".#.##...",
    "######..",
)
POOP_FRAMES = (
    (
        "~.......",
        ".~..~...",
        "~....~..",
        "....~...",
    ) + _POOP_LUMP,
    (
        ".~......",
        "~....~..",
        ".~..~...",
        ".....~..",
    ) + _POOP_LUMP,
    ("........",) * 4 + _POOP_LUMP,
)
POOP_PLAIN = 2  # index in POOP_FRAMES: no stink lines
POOP_CHARS = ".#~"  # bitmap value = index here
POOP_COLORS = (None, 0x14201A, 0x14201A)  # see-through, lump, stink: the day ink (ui.INK_DAY)


def poop_sheet():
    """The poop frames stacked vertically, FX_SIZE rows each."""
    rows = []
    for f in POOP_FRAMES:
        rows.extend(f)
    return rows
