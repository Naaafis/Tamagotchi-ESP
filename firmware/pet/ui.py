"""displayio layout: icon rows, pet in the middle, attention icon, stats page.

Hardware-agnostic: this only builds displayio groups. The caller puts
PetUI.root into display.root_group, on the ILI9341 or in the pygame simulator.
Everything is drawn inside the centered SQUARE x SQUARE area; nothing is
drawn outside it, and displayio paints uncovered pixels black.

Layout (inside the square, Tamagotchi style):
    y   4.. 52   top icon row: eat, drink, sleep, play
    y  56..184   pet, 16x16 art at 8x; reaction / "I want" bubble top-right
    y 188..236   bottom icon row: treat, affection, stats, [attention]
The stats page covers the middle with six bars when open.
"""

import displayio

from pet import sprites
from pet.state import (
    POSE_HAPPY,
    POSE_IDLE,
    POSE_SAD,
    POSE_SLEEP,
    POSE_SULK,
    STAT_ACTION,
    STAT_MAX,
    STAT_NAMES,
)

SQUARE = 240

# Colours. T10 owns the final look; these only need to read from a few feet
# away. Day is a lit LCD green with near-black ink; night (lights off) is dark.
BG_DAY = 0xA8D08D
INK_DAY = 0x14201A
BG_NIGHT = 0x0B1020
INK_NIGHT = 0x5C6B8A

ICON_SCALE = 4
ICON_PX = sprites.ICON_SIZE * ICON_SCALE  # 48
ICONS_PER_ROW = 4
ICON_X = (6, 66, 126, 186)  # 60 px slots, icon centered in each
TOP_Y = 4
BOTTOM_Y = SQUARE - 4 - ICON_PX  # 188
MAX_MENU_ITEMS = ICONS_PER_ROW * 2 - 1  # last bottom slot is the attention icon

PET_SCALE = 8
PET_PX = sprites.PET_SIZE * PET_SCALE  # 128
PET_X = (SQUARE - PET_PX) // 2  # 56
PET_Y = (SQUARE - PET_PX) // 2  # 56

BUBBLE_X = 186
BUBBLE_Y = 58

# Stats page: six rows of icon + bar.
BAR_W = 42  # bitmap cells: 1 border + 40 fill + 1 border
BAR_H = 7
BAR_SEGMENTS = BAR_W - 2
BAR_SCALE = 4
ROW_Y0 = 12
ROW_PITCH = 36
ROW_ICON_X = 20
ROW_ICON_SCALE = 2
ROW_BAR_X = 56

BLINK_SECONDS = 0.5  # attention icon on/off
IDLE_FRAME_SECONDS = 0.6
SLEEP_FRAME_SECONDS = 1.0


def bitmap_from_rows(rows, width):
    """2-colour Bitmap from text rows ('#' = 1). Raises on a row of the wrong width."""
    bitmap = displayio.Bitmap(width, len(rows), 2)
    y = 0
    for row in rows:
        if len(row) != width:
            raise ValueError("row %d is %d wide, want %d" % (y, len(row), width))
        for x in range(width):
            if row[x] == "#":
                bitmap[x, y] = 1
        y += 1
    return bitmap


def _frame_bitmap(width, height):
    """Bitmap with a 1-cell ink border and an empty inside."""
    bitmap = displayio.Bitmap(width, height, 2)
    for x in range(width):
        bitmap[x, 0] = 1
        bitmap[x, height - 1] = 1
    for y in range(height):
        bitmap[0, y] = 1
        bitmap[width - 1, y] = 1
    return bitmap


class PetUI:
    def __init__(self, menu_items, width=320, height=240):
        self.menu_items = tuple(menu_items)
        if len(self.menu_items) > MAX_MENU_ITEMS:
            raise ValueError("at most %d menu items fit" % MAX_MENU_ITEMS)

        self.root = displayio.Group()
        self.square = displayio.Group(x=(width - SQUARE) // 2, y=(height - SQUARE) // 2)
        self.root.append(self.square)

        self._palettes = []  # every 2-colour palette, for the day/night theme
        self._night = False

        # Background: one colour, re-tinted at night.
        self._bg_palette = displayio.Palette(1)
        self._bg_palette[0] = BG_DAY
        background = displayio.Bitmap(SQUARE, SQUARE, 1)
        self.square.append(displayio.TileGrid(background, pixel_shader=self._bg_palette))

        self._icon_sheet = bitmap_from_rows(sprites.icon_sheet(), sprites.ICON_SIZE)
        self._pet_sheet = bitmap_from_rows(sprites.pet_sheet(), sprites.PET_SIZE)

        # Icon rows.
        self.icons_group = displayio.Group()
        self._icon_palettes = []
        for i in range(len(self.menu_items)):
            col = i % ICONS_PER_ROW
            row = i // ICONS_PER_ROW
            palette = self._new_palette()
            grid = self._icon_grid(palette, self.menu_items[i])
            group = displayio.Group(
                scale=ICON_SCALE, x=ICON_X[col], y=TOP_Y if row == 0 else BOTTOM_Y
            )
            group.append(grid)
            self.icons_group.append(group)
            self._icon_palettes.append(palette)
        self.square.append(self.icons_group)

        # Attention icon, bottom-right slot, blinks while a need is low.
        self._attention_group = displayio.Group(
            scale=ICON_SCALE, x=ICON_X[ICONS_PER_ROW - 1], y=BOTTOM_Y
        )
        self._attention_group.append(self._icon_grid(self._new_palette(), "attention"))
        self._attention_group.hidden = True
        self.square.append(self._attention_group)

        # The pet.
        self._pet_palette = self._new_palette()
        self._pet_grid = displayio.TileGrid(
            self._pet_sheet,
            pixel_shader=self._pet_palette,
            width=1,
            height=1,
            tile_width=sprites.PET_SIZE,
            tile_height=sprites.PET_SIZE,
        )
        self.pet_group = displayio.Group(scale=PET_SCALE, x=PET_X, y=PET_Y)
        self.pet_group.append(self._pet_grid)
        self.square.append(self.pet_group)

        # Bubble next to the pet: what it is getting, or what it wants.
        self._bubble_grid = self._icon_grid(self._new_palette(), "eat")
        self._bubble_group = displayio.Group(scale=ICON_SCALE, x=BUBBLE_X, y=BUBBLE_Y)
        self._bubble_group.append(self._bubble_grid)
        self._bubble_group.hidden = True
        self.square.append(self._bubble_group)

        # Stats page.
        self.page_group = displayio.Group()
        self._bars = []  # (bitmap, segments_shown) per stat
        for i in range(len(STAT_NAMES)):
            row_y = ROW_Y0 + ROW_PITCH * i
            icon_group = displayio.Group(scale=ROW_ICON_SCALE, x=ROW_ICON_X, y=row_y + 2)
            icon_group.append(self._icon_grid(self._new_palette(), STAT_ACTION[STAT_NAMES[i]]))
            self.page_group.append(icon_group)
            bar = _frame_bitmap(BAR_W, BAR_H)
            bar_palette = self._new_palette(opaque=True)
            bar_group = displayio.Group(scale=BAR_SCALE, x=ROW_BAR_X, y=row_y)
            bar_group.append(displayio.TileGrid(bar, pixel_shader=bar_palette))
            self.page_group.append(bar_group)
            self._bars.append([bar, 0])
        self.page_group.hidden = True
        self.square.append(self.page_group)

        # Change tracking so a render only touches displayio when something moved.
        self._cursor = -1
        self._frame = -1
        self._bubble = None
        self._attention_shown = False
        self._page_open = False
        self._frame_index = {}
        for name in sprites.PET_FRAMES:
            self._frame_index[name] = sprites.pet_frame_index(name)

    # ---- building blocks ----

    def _new_palette(self, opaque=False):
        palette = displayio.Palette(2)
        palette[0] = BG_DAY
        palette[1] = INK_DAY
        if not opaque:
            palette.make_transparent(0)
        self._palettes.append(palette)
        return palette

    def _icon_grid(self, palette, name):
        grid = displayio.TileGrid(
            self._icon_sheet,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=sprites.ICON_SIZE,
            tile_height=sprites.ICON_SIZE,
        )
        grid[0] = sprites.icon_index(name)
        return grid

    def _colors(self):
        if self._night:
            return BG_NIGHT, INK_NIGHT
        return BG_DAY, INK_DAY

    def _style_icon(self, index, selected):
        """Highlight = inverted: ink box with the glyph cut out of it."""
        bg, ink = self._colors()
        palette = self._icon_palettes[index]
        if selected:
            palette[0] = ink
            palette[1] = bg
            palette.make_opaque(0)
        else:
            palette[0] = bg
            palette[1] = ink
            palette.make_transparent(0)

    def _apply_theme(self, night):
        self._night = night
        bg, ink = self._colors()
        self._bg_palette[0] = bg
        for palette in self._palettes:
            palette[0] = bg
            palette[1] = ink
        if self._cursor >= 0:
            self._style_icon(self._cursor, True)

    def _frame_for(self, pet, now):
        pose = pet.pose
        if pose == POSE_SLEEP:
            name = "sleep0" if int(now / SLEEP_FRAME_SECONDS) % 2 == 0 else "sleep1"
        elif pose == POSE_HAPPY:
            name = "happy"
        elif pose == POSE_SAD:
            name = "sad"
        elif pose == POSE_SULK:
            name = "sulk"
        else:  # POSE_IDLE
            name = "idle0" if int(now / IDLE_FRAME_SECONDS) % 2 == 0 else "idle1"
        return self._frame_index[name]

    def _update_bars(self, pet):
        for i in range(len(STAT_NAMES)):
            segments = int(pet.stats[STAT_NAMES[i]] * BAR_SEGMENTS / STAT_MAX + 0.5)
            entry = self._bars[i]
            if segments == entry[1]:
                continue
            bitmap = entry[0]
            for x in range(BAR_SEGMENTS):
                value = 1 if x < segments else 0
                for y in range(1, BAR_H - 1):
                    bitmap[1 + x, y] = value
            entry[1] = segments

    # ---- per-frame update ----

    def render(self, game, now):
        """Bring the screen in line with the game state. Cheap when nothing changed."""
        pet = game.pet

        night = pet.asleep
        if night != self._night:
            self._apply_theme(night)

        page_open = game.page is not None
        if page_open != self._page_open:
            self._page_open = page_open
            self.page_group.hidden = not page_open
            self.icons_group.hidden = page_open
            self.pet_group.hidden = page_open
            self._attention_group.hidden = page_open or not self._attention_shown
            self._bubble_group.hidden = page_open or self._bubble is None
        if page_open:
            self._update_bars(pet)
            return

        cursor = game.menu.cursor
        if cursor != self._cursor:
            if self._cursor >= 0:
                self._style_icon(self._cursor, False)
            if cursor >= 0:
                self._style_icon(cursor, True)
            self._cursor = cursor

        frame = self._frame_for(pet, now)
        if frame != self._frame:
            self._pet_grid[0] = frame
            self._frame = frame

        if pet.asleep:
            bubble = None
        elif pet.reaction is not None:
            bubble = pet.reaction
        else:
            bubble = pet.wants
        if bubble != self._bubble:
            self._bubble = bubble
            if bubble is None:
                self._bubble_group.hidden = True
            else:
                self._bubble_grid[0] = sprites.icon_index(bubble)
                self._bubble_group.hidden = False

        shown = pet.attention and int(now / BLINK_SECONDS) % 2 == 0
        if shown != self._attention_shown:
            self._attention_shown = shown
            self._attention_group.hidden = not shown
