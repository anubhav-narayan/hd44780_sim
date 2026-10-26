"""
HD44780X - an HD44780 character-display model with arbitrary dimensions.

Drop-in subclass of ``HD44780``: same constructor arguments, same methods
(``start/stop/run``, ``clear``, ``return_home``, ``entry_mode_set``,
``display_control``, ``cursor_control``, ``function_set``, ``set_ddram_addr``,
``write_data``, ``read_data``, ``command(rs, rw, db)``, ...).

    lcd = HD44780X(segments=80, lines=24)      # an 80x24 text display
    lcd.start()

Everything the original does not need to change is inherited, so keep the
original module importable (adjust the import below to wherever it lives).

Copyright (C) 2025  Anubhav Mattoo
"""
from __future__ import annotations

import pygame

from .hd44780 import HD44780

_BLANK = [0x00] * 8


def _geometry(segments, lines, cols, rows, pixel_size, segment_margin,
              line_margin, display_border, fit):
    """Resolve pixel size and margins so the window fits ``fit`` (w, h).

    Unspecified margins scale with the pixel size (20 -> 10/20/20, exactly the
    original defaults).  Explicit margins are kept as given.
    """
    ps = 20 if pixel_size is None else pixel_size
    while True:
        k = ps / 20
        sm = segment_margin if segment_margin is not None else max(1, round(10 * k))
        lm = line_margin if line_margin is not None else max(1, round(20 * k))
        db = display_border if display_border is not None else max(2, round(20 * k))
        w = segments * cols * ps + (segments - 1) * sm + 2 * db
        h = lines * rows * ps + (lines - 1) * lm + 2 * db
        if fit is None or ps <= 1 or (w <= fit[0] and h <= fit[1]):
            return ps, sm, lm, db
        ps -= 1


class HD44780X(HD44780):
    """HD44780 with ``segments`` x ``lines`` of any size.

    Extra constructor arguments (all optional, keyword-only):

    row_starts   DDRAM start address of every display row.  Default is
                 linear: row r starts at ``r * line_length``.
    line_length  Characters per DDRAM line (what display-shift rotates).
                 Default ``segments``.
    ddram_size   Total DDRAM bytes.  Default is the minimum that fits.
    fit          (max_w, max_h) window size; pixel size is reduced until the
                 window fits.  ``None`` disables auto-fit.  Default 1900x1000 (small
                 displays such as 16x2 are left exactly as the original draws them).
    fps          Refresh rate of the render thread.  Default 60.

    Addressing
    ----------
    The real chip has a 7-bit DDRAM address.  A big display needs more, so
    the full address is ``(addr_page << 7) | low7``: ``command(0, 0, 0x80|low7)``
    sets the low 7 bits and keeps the current ``addr_page``.  Change the page
    with ``set_addr_page(n)``, ``command(..., page=n)`` or use ``goto(row, col)``
    from Python.
    """

    def __init__(self, segments=8, lines=1, cols=5, rows=8, pixel_size=None,
                 pixel_border=0.2, segment_margin=None, line_margin=None,
                 display_border=None, *, row_starts=None, line_length=None,
                 ddram_size=None, fit=(1900, 1000), fps=60):
        ps, sm, lm, db = _geometry(segments, lines, cols, rows, pixel_size,
                                   segment_margin, line_margin, display_border, fit)
        super().__init__(segments, lines, cols, rows, ps, pixel_border, sm, lm, db)
        self.fit = fit
        self.fps = fps
        self.screen = None
        self._glyphs = {}
        self._drawn = None
        self._last_state = None
        self._last_ddram = None
        self.cells_drawn = 0                 # cells repainted by the last refresh
        self._configure(row_starts, line_length, ddram_size)

    # ------------------------------------------------------------ state setup
    def _configure(self, row_starts, line_length, ddram_size):
        S, L = self.segments, self.lines
        if S < 1 or L < 1:
            raise ValueError("segments and lines must be >= 1")
        self.line_length = line_length or S
        if self.line_length < S:
            raise ValueError("line_length must be >= segments")
        self.row_starts = (list(row_starts) if row_starts is not None
                           else [r * self.line_length for r in range(L)])
        if len(self.row_starts) != L:
            raise ValueError("row_starts needs one entry per line")
        need = max(self.row_starts) + self.line_length
        self.ddram_size = ddram_size or need
        if self.ddram_size < need:
            raise ValueError(f"ddram_size must be >= {need}")
        self.row_visible_address = self.row_starts      # name used by the original
        self.ddram = [0x00] * self.ddram_size
        self.grid = [[_BLANK] * S for _ in range(L)]
        self.ddram_pointer = 0x00
        self.addr_page = 0
        self.shift_offset = 0
        self.cursor_ptr = [0x00, 0x00]

    # ------------------------------------------------------------ addressing
    def xy_to_addr(self, row, col):
        return self.row_starts[row] + col

    def set_addr_page(self, page):
        self.addr_page = int(page)

    def goto(self, row, col=0):
        """Python-level cursor placement (sets page and address together)."""
        addr = self.xy_to_addr(row, col)
        self.addr_page = addr >> 7
        self.set_ddram_addr(addr)

    def write_string(self, text):
        for ch in text:
            self.write_data(ch)

    def set_ddram_addr(self, addr):
        self.ddram_pointer = addr % self.ddram_size

    def command(self, rs: int, rw: int, db: int, page=None):
        """Same as the original, plus the optional DDRAM address ``page``."""
        if page is not None:
            self.addr_page = int(page)
        if rs == 0 and rw == 0 and (db & 0x80):          # Set DDRAM address
            self.set_ddram_addr((self.addr_page << 7) | (db & 0x7F))
            return None
        return super().command(rs, rw, db)

    # ----------------------------------------------------- controller behaviour
    def map_ddram(self) -> None:
        cg, dd, size, off = self.cgrom, self.ddram, self.ddram_size, self.shift_offset
        L = self.line_length
        for r in range(self.lines):
            base, row = self.row_starts[r], self.grid[r]
            for c in range(self.segments):
                row[c] = cg.get(dd[(base + (c + off) % L) % size], _BLANK)

    def clear_display(self):
        for row in self.grid:
            for c in range(self.segments):
                row[c] = _BLANK

    def set_cursor_ptr(self) -> None:
        p = self.ddram_pointer
        for r, base in enumerate(self.row_starts):
            off = p - base
            if 0 <= off < self.line_length:
                col = (off - self.shift_offset) % self.line_length
                self.cursor_ptr[:] = [r, col] if col < self.segments else [-1, -1]
                return
        self.cursor_ptr[:] = [-1, -1]

    def update_entry_mode(self):
        step = 1 if self.entry_mode_dir else -1
        self.ddram_pointer = (self.ddram_pointer + step) % self.ddram_size
        if self.entry_mode_shift:
            self.shift_offset = (self.shift_offset + step) % self.line_length

    def shift_display(self, display_shift: bool, shift_right: bool) -> None:
        if display_shift:                       # shift the whole display
            step = -1 if shift_right else 1
            self.shift_offset = (self.shift_offset + step) % self.line_length
        else:                                   # move cursor only (datasheet: R/L=1 -> AC+1)
            step = 1 if shift_right else -1
            self.ddram_pointer = (self.ddram_pointer + step) % self.ddram_size

    def clear(self):
        self.ddram = [0x20] * self.ddram_size
        self.ddram_pointer = 0x00
        self.shift_offset = 0

    def return_home(self):
        self.ddram_pointer = 0x00
        self.shift_offset = 0

    # --------------------------------------------------------------- rendering
    def update_display(self, **kwargs):
        lines = kwargs.get('lines', self.lines)
        segments = kwargs.get('segments', self.segments)
        reshape = (lines, segments) != (self.lines, self.segments)
        self.lines, self.segments = lines, segments
        self.pixel_size = kwargs.get('pixel_size', self.pixel_size)
        self.segment_width = self.cols * self.pixel_size
        self.segment_height = self.rows * self.pixel_size
        self.width = (self.segments * self.segment_width
                      + (self.segments - 1) * self.segment_margin + 2 * self.display_border)
        self.height = (self.lines * self.segment_height
                       + (self.lines - 1) * self.line_margin + 2 * self.display_border)
        if reshape:
            self._configure(None, None, None)
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.invalidate()

    def invalidate(self):
        """Drop render caches (call after changing colours at run time)."""
        self._glyphs.clear()
        self._drawn = None
        self._last_state = None
        self._last_ddram = None

    def _pad(self):
        return (min(4, self.segment_margin // 2), min(4, self.line_margin // 2))

    def _glyph(self, key):
        surf = self._glyphs.get(key)
        if surf is not None:
            return surf
        pattern, cursor = key
        padx, pady = self._pad()
        surf = pygame.Surface((self.segment_width + 2 * padx,
                               self.segment_height + 2 * pady))
        surf.fill(self.segment_bg_color)
        size = self.pixel_size
        border = int(size * self.pixel_border)
        fill = size - 2 * border
        for row in range(self.rows):
            bits = pattern[row] if row < len(pattern) else 0
            if cursor and row == self.rows - 1:
                bits |= (1 << self.cols) - 1            # underline cursor
            for col in range(self.cols):
                on = (bits >> (self.cols - 1 - col)) & 1
                color = self.pixel_on_color if on else self.pixel_off_color
                x, y = padx + col * size, pady + row * size
                if fill >= 3:
                    pygame.draw.circle(surf, color, (x + size // 2, y + size // 2), fill // 2)
                else:
                    pygame.draw.rect(surf, color, (x + border, y + border,
                                                   max(fill, 1), max(fill, 1)))
        self._glyphs[key] = surf
        return surf

    def draw_segment(self, line, index):
        """Paint one cell (kept for API compatibility)."""
        key = (tuple(self.grid[line][index]), self._cursor_at(line, index))
        self._blit(line, index, key)

    def _cursor_at(self, line, index):
        return (self.cursor_active and self.cursor_visible
                and self.cursor_ptr[0] == line and self.cursor_ptr[1] == index)

    def _blit(self, line, index, key):
        padx, pady = self._pad()
        x0 = self.display_border + index * (self.segment_width + self.segment_margin) - padx
        y0 = self.display_border + line * (self.segment_height + self.line_margin) - pady
        g = self._glyph(key)
        self.screen.blit(g, (x0, y0))
        return pygame.Rect(x0, y0, g.get_width(), g.get_height())

    def _paint(self, full=False):
        if full or self._drawn is None:
            self.screen.fill(self.display_bg_color)
            self._drawn = [[None] * self.segments for _ in range(self.lines)]
        dirty = []
        for r in range(self.lines):
            grow, drow = self.grid[r], self._drawn[r]
            for c in range(self.segments):
                key = (tuple(grow[c]), self._cursor_at(r, c))
                if drow[c] != key:
                    drow[c] = key
                    dirty.append(self._blit(r, c, key))
        self.cells_drawn = len(dirty)
        if len(dirty) > (self.lines * self.segments) // 2:
            pygame.display.flip()
        elif dirty:
            pygame.display.update(dirty)

    def draw(self):
        """Full repaint."""
        self._paint(full=True)

    def refresh(self, force=False):
        """Repaint only what changed since the last call; returns cells redrawn."""
        if self.screen is None:
            self.update_display()
        if self.display_on:
            self.update_cursor()
        state = (self.display_on, self.shift_offset, tuple(self.cursor_ptr),
                 self.cursor_active and self.cursor_visible)
        if not force and state == self._last_state and self.ddram == self._last_ddram:
            return 0
        self._last_state, self._last_ddram = state, list(self.ddram)
        if self.display_on:
            self.map_ddram()
        else:
            self.clear_display()
        self._paint(full=force)
        return self.cells_drawn

    def save(self, path):
        """Render the current state and write it to a PNG (handy in CI)."""
        self.refresh(force=True)
        pygame.image.save(self.screen, path)

    def run(self):
        self.update_display()
        pygame.display.set_caption(
            f"HD44780X LCD Display Emulator ({self.segments}x{self.lines})")
        clock = pygame.time.Clock()
        self.running = True
        while self.running:
            self.refresh()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            clock.tick(self.fps)
        pygame.display.quit()
