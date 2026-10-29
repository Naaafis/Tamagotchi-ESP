"""displayio layout: icon rows, pet in the middle, attention icon, stats page.

Hardware-agnostic: this only builds displayio groups. The caller puts
PetUI.root into display.root_group, on the ILI9341 or in the pygame simulator.
Everything is drawn inside the centered SQUARE x SQUARE area; nothing is
drawn outside it, and displayio paints uncovered pixels black.

Layout (inside the square, Tamagotchi style):
    y   4.. 52   top icon row: eat, drink, sleep, play
    y  56..184   the stage, drawn at 8x: the pet (16x16 art) plus up to
                 SLOT_COUNT 8x8 overlays (food, hearts, Z's, arrows, digits);
                 the "I want" bubble sits top-right on the main screen
    y 188..236   bottom icon row: treat, affection, stats, [attention]
The stats page covers the middle with six bars when open.

During an animation or the game the stage shows game.scene.frame (see
pet.anim for the frame format); otherwise the pet's pose. Measured on the
board: a pet frame swap redraws 128x128 px in 50 ms (opaque palette; 60 ms
transparent), moving it redraws the old and new rectangles (118 ms), an 8x8
overlay costs 19 ms to show and 35 ms to move. So render() only touches
displayio when a value actually changed, and hops are frames, not moves.
"""

import displayio

from pet import anim, sprites
from pet.state import (
    POSE_HAPPY,
    POSE_IDLE,
    POSE_SAD,
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

STAGE_SCALE = 8
STAGE_Y = (SQUARE - anim.STAGE_H * STAGE_SCALE) // 2  # 56
SLOT_COUNT = anim.MAX_OVERLAYS

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
        self._fx_sheet = bitmap_from_rows(sprites.fx_sheet(), sprites.FX_SIZE)

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

        # The stage: the pet, then the overlay slots on top of it. The pet's
        # palette is opaque (its background matches the stage, and a swap
        # redraws 17% faster); overlays stay transparent so they can overlap.
        self.stage = displayio.Group(scale=STAGE_SCALE, x=0, y=STAGE_Y)
        self._pet_grid = displayio.TileGrid(
            self._pet_sheet,
            pixel_shader=self._new_palette(opaque=True),
            width=1,
            height=1,
            tile_width=sprites.PET_SIZE,
            tile_height=sprites.PET_SIZE,
            x=anim.HOME_X,
            y=anim.HOME_Y,
        )
        self.stage.append(self._pet_grid)
        fx_palette = self._new_palette()
        self._slots = []
        for _ in range(SLOT_COUNT):
            slot = displayio.TileGrid(
                self._fx_sheet,
                pixel_shader=fx_palette,
                width=1,
                height=1,
                tile_width=sprites.FX_SIZE,
                tile_height=sprites.FX_SIZE,
            )
            slot.hidden = True
            self.stage.append(slot)
            self._slots.append(slot)
        self.square.append(self.stage)

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
        self._bubble = None
        self._attention_shown = False
        self._page_open = False
        self._pet_name = "idle0"  # what the pet grid shows now (None = hidden)
        self._pet_x = anim.HOME_X
        self._pet_y = anim.HOME_Y
        self._pet_flip = False
        self._slot_shown = [None] * SLOT_COUNT  # overlay tuple per slot, None = hidden
        self._pet_index = {}
        for name in sprites.PET_FRAMES:
            self._pet_index[name] = sprites.pet_frame_index(name)
        self._fx_index = {}
        for name in sprites.FX_NAMES:
            self._fx_index[name] = sprites.fx_index(name)

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

    def _pose_frame(self, pet, now):
        """Pet frame name for the main screen while awake."""
        pose = pet.pose
        if pose == POSE_HAPPY:
            return "happy"
        if pose == POSE_SAD:
            return "sad"
        if pose == POSE_SULK:
            return "sulk"
        # POSE_IDLE: bob up and down
        return "idle0" if int(now / IDLE_FRAME_SECONDS) % 2 == 0 else "idle1"

    def _show_pet(self, name, x, y, flip):
        grid = self._pet_grid
        if name is None:
            if self._pet_name is not None:
                grid.hidden = True
                self._pet_name = None
            return
        if name != self._pet_name:
            grid[0] = self._pet_index[name]
            if self._pet_name is None:
                grid.hidden = False
            self._pet_name = name
        if x != self._pet_x:
            grid.x = x
            self._pet_x = x
        if y != self._pet_y:
            grid.y = y
            self._pet_y = y
        if flip != self._pet_flip:
            grid.flip_x = flip
            self._pet_flip = flip

    def _show_overlays(self, overlays):
        """Put each (name, x, y, flip) in a slot, in order; hide the slots left over."""
        count = len(overlays)
        for i in range(SLOT_COUNT):
            want = overlays[i] if i < count else None
            shown = self._slot_shown[i]
            if want == shown:
                continue
            slot = self._slots[i]
            if want is None:
                slot.hidden = True
            else:
                if shown is None or want[0] != shown[0]:
                    slot[0] = self._fx_index[want[0]]
                if shown is None or want[1] != shown[1]:
                    slot.x = want[1]
                if shown is None or want[2] != shown[2]:
                    slot.y = want[2]
                if shown is None or want[3] != shown[3]:
                    slot.flip_x = want[3]
                if shown is None:
                    slot.hidden = False
            self._slot_shown[i] = want

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
        scene = game.scene

        night = game.lights_off
        if night != self._night:
            self._apply_theme(night)

        page_open = game.page is not None
        if page_open != self._page_open:
            self._page_open = page_open
            self.page_group.hidden = not page_open
            self.icons_group.hidden = page_open
            self.stage.hidden = page_open
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

        if scene is not None:
            f = scene.frame
            self._show_pet(f[anim.PET], f[anim.X], f[anim.Y], f[anim.FLIP])
            self._show_overlays(f[anim.OVERLAYS])
        elif pet.asleep:  # lights off
            self._show_pet("lie_sleep", anim.LIE_X, anim.HOME_Y, False)
            self._show_overlays(anim.SLEEPING[int(now / anim.Z_SECONDS) % len(anim.SLEEPING)])
        else:
            self._show_pet(self._pose_frame(pet, now), anim.HOME_X, anim.HOME_Y, False)
            self._show_overlays(())

        if scene is not None or pet.asleep:
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
