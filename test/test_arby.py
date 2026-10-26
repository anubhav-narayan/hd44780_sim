import time

import pygame
import pytest

from hd44780_sim import HD44780
from hd44780_sim import HD44780X


def text(lcd, row):
    """What the display currently shows on a row (from the mapped grid)."""
    lcd.map_ddram()
    inv = {tuple(v): chr(k) for k, v in lcd.cgrom.items()}
    return "".join(inv.get(tuple(c), "?") if any(c) else " " for c in lcd.grid[row])


def send(lcd, *cmds):
    for c in cmds:
        lcd.command(0, 0, c)


def put(lcd, s):
    for ch in s:
        lcd.command(1, 0, ord(ch))


# ----------------------------------------------------------------- basics
def test_is_a_drop_in_subclass():
    assert issubclass(HD44780X, HD44780)
    lcd = HD44780X(16, 2)
    for name in ("start", "stop", "run", "clear", "return_home", "entry_mode_set",
                 "display_control", "cursor_control", "function_set",
                 "set_ddram_addr", "write_data", "read_data", "command",
                 "update_display", "set_backlight", "draw"):
        assert callable(getattr(lcd, name))


def test_original_constructor_signature_positional():
    lcd = HD44780X(16, 2, 5, 8, 5, 0.15, 10, 10, 20)       # same positional order
    assert (lcd.segments, lcd.lines, lcd.pixel_size, lcd.line_margin) == (16, 2, 5, 10)


def test_default_geometry_matches_original_for_small_displays():
    a, b = HD44780(16, 2), HD44780X(16, 2)
    assert (a.pixel_size, a.segment_margin, a.line_margin, a.display_border) == \
           (b.pixel_size, b.segment_margin, b.line_margin, b.display_border)
    assert (a.width, a.height) == (b.width, b.height)


@pytest.mark.parametrize("seg, lines", [(80, 24), (132, 43), (200, 60), (3, 100)])
def test_arbitrary_sizes_fit_the_window(seg, lines):
    lcd = HD44780X(seg, lines)
    assert (lcd.width <= 1900 and lcd.height <= 1000) or lcd.pixel_size == 1
    assert len(lcd.ddram) == seg * lines
    assert len(lcd.grid) == lines and len(lcd.grid[0]) == seg


def test_fit_none_keeps_requested_pixel_size():
    assert HD44780X(80, 24, pixel_size=20, fit=None).pixel_size == 20


# ------------------------------------------------------------- addressing
def test_goto_and_write_to_every_corner_of_80x24():
    lcd = HD44780X(80, 24)
    send(lcd, 0x38, 0x0C, 0x06, 0x01)
    for r, c, ch in [(0, 0, "A"), (0, 79, "B"), (23, 0, "C"), (23, 79, "D"), (11, 40, "E")]:
        lcd.goto(r, c)
        lcd.write_data(ch)
    assert text(lcd, 0)[0] == "A" and text(lcd, 0)[79] == "B"
    assert text(lcd, 23)[0] == "C" and text(lcd, 23)[79] == "D"
    assert text(lcd, 11)[40] == "E"


def test_command_bus_reaches_full_range_with_page():
    """8-bit bus: low 7 bits from the instruction, high bits from the page."""
    lcd = HD44780X(80, 24)
    addr = 23 * 80 + 79                                   # last cell = 1919
    lcd.command(0, 0, 0x80 | (addr & 0x7F), page=addr >> 7)
    assert lcd.ddram_pointer == addr
    put(lcd, "Z")
    assert lcd.ddram[addr] == ord("Z")
    # page is sticky: next low-7 command stays in the same page
    lcd.command(0, 0, 0x80 | 0x05)
    assert lcd.ddram_pointer == (addr >> 7 << 7) | 5


def test_set_address_masks_the_instruction_bit():
    """Original: command(0,0,0x80) left the pointer at 48; here it is 0."""
    lcd = HD44780X(16, 2)
    lcd.command(0, 0, 0x80)
    assert lcd.ddram_pointer == 0
    lcd.command(0, 0, 0x80 | 0x10)
    assert lcd.ddram_pointer == 0x10


def test_entry_mode_increments_across_rows_and_wraps():
    lcd = HD44780X(10, 3)
    send(lcd, 0x38, 0x0C, 0x06, 0x01)
    put(lcd, "0123456789abc")                              # overflows row 0 into row 1
    assert text(lcd, 0) == "0123456789" and text(lcd, 1)[:3] == "abc"
    lcd.goto(2, 9)
    put(lcd, "xy")                                         # wraps to address 0
    assert lcd.ddram[29] == ord("x") and lcd.ddram[0] == ord("y")


def test_decrement_mode():
    lcd = HD44780X(8, 2)
    send(lcd, 0x0C, 0x04, 0x01)                            # entry mode: decrement
    lcd.goto(0, 3)
    put(lcd, "abcd")
    assert [lcd.ddram[i] for i in range(0, 4)] == [ord("d"), ord("c"), ord("b"), ord("a")]


def test_read_data_matches_write():
    lcd = HD44780X(80, 24)
    lcd.goto(5, 7)
    lcd.write_data("Q")
    lcd.goto(5, 7)
    assert lcd.command(1, 1, 0) == ord("Q")


def test_custom_row_starts_emulate_a_datasheet_16x2():
    lcd = HD44780X(16, 2, row_starts=[0x00, 0x40], line_length=40, ddram_size=0x68)
    send(lcd, 0x0C, 0x06, 0x01)
    lcd.command(0, 0, 0x80 | 0x40)                         # datasheet "line 2" address
    put(lcd, "second")
    assert text(lcd, 1).startswith("second")
    lcd.command(0, 0, 0x80)
    put(lcd, "first")
    assert text(lcd, 0).startswith("first")


@pytest.mark.parametrize("kw", [dict(row_starts=[0]), dict(line_length=3),
                                dict(ddram_size=10)])
def test_bad_config_rejected(kw):
    with pytest.raises(ValueError):
        HD44780X(8, 2, **kw)


# ----------------------------------------------------------------- shifts
def test_display_shift_rotates_each_row_independently():
    lcd = HD44780X(6, 2)
    send(lcd, 0x0C, 0x06, 0x01)
    lcd.goto(0, 0); put(lcd, "ABCDEF")
    lcd.goto(1, 0); put(lcd, "123456")
    send(lcd, 0x18)                                        # shift display left
    assert text(lcd, 0) == "BCDEFA" and text(lcd, 1) == "234561"
    send(lcd, 0x1C, 0x1C)                                  # shift right twice
    assert text(lcd, 0) == "FABCDE" and text(lcd, 1) == "612345"


def test_return_home_and_clear_reset_shift():
    lcd = HD44780X(6, 1)
    send(lcd, 0x0C, 0x06, 0x01)
    put(lcd, "ABCDEF")
    send(lcd, 0x18, 0x02)
    assert lcd.shift_offset == 0 and lcd.ddram_pointer == 0
    send(lcd, 0x18, 0x01)
    assert lcd.shift_offset == 0 and set(lcd.ddram) == {0x20}


def test_cursor_move_follows_datasheet_direction():
    lcd = HD44780X(8, 1)
    send(lcd, 0x14)                                        # S/C=0 R/L=1 -> cursor right
    assert lcd.ddram_pointer == 1
    send(lcd, 0x10)                                        # R/L=0 -> cursor left
    assert lcd.ddram_pointer == 0


def test_entry_shift_mode_scrolls_text():
    lcd = HD44780X(4, 1)
    send(lcd, 0x0C, 0x07, 0x01)                            # I/D=1, S=1
    put(lcd, "ABCDEF")
    assert text(lcd, 0) == "CDEF"                          # display followed the writes


# ----------------------------------------------------------------- cursor
def test_cursor_position_tracks_row_and_col():
    lcd = HD44780X(80, 24)
    send(lcd, 0x0E)                                        # display + cursor on
    lcd.goto(17, 33)
    lcd.update_cursor()
    assert lcd.cursor_ptr == [17, 33]


def test_cursor_accounts_for_display_shift_and_hides_offscreen():
    lcd = HD44780X(4, 1, line_length=10)
    send(lcd, 0x0E)
    lcd.goto(0, 6)
    lcd.update_cursor()
    assert lcd.cursor_ptr == [-1, -1]                      # col 6 is outside the 4 visible
    send(lcd, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18)          # shift left 6 -> col 6 now at 0
    lcd.update_cursor()
    assert lcd.cursor_ptr == [0, 0]


# --------------------------------------------------------------- rendering
def test_first_paint_draws_everything_then_only_changes():
    lcd = HD44780X(80, 24)
    send(lcd, 0x0C, 0x06, 0x01)
    assert lcd.refresh() == 80 * 24                        # first frame: all cells
    assert lcd.refresh() == 0                              # nothing changed
    lcd.goto(10, 10)
    lcd.write_data("X")
    assert lcd.refresh() == 1                              # exactly one cell repainted
    lcd.goto(0, 0)
    lcd.write_string("hello")
    assert lcd.refresh() == 5


def test_display_off_blanks_and_on_restores():
    lcd = HD44780X(20, 4)
    send(lcd, 0x0C, 0x06, 0x01)
    put(lcd, "visible")
    lcd.refresh(force=True)
    send(lcd, 0x08)                                        # display off (data kept)
    lcd.refresh()
    assert lcd.ddram[0] == ord("v")
    assert all(not any(c) for row in lcd.grid for c in row)
    send(lcd, 0x0C)
    lcd.refresh()
    assert any(any(c) for c in lcd.grid[0])


def test_blinking_cursor_repaints_one_cell():
    lcd = HD44780X(8, 2)
    send(lcd, 0x0F, 0x01)                                  # display, cursor, blink
    lcd.refresh()
    lcd.blink_start_time = pygame.time.get_ticks() - 600   # force the "off" phase
    n_off = lcd.refresh()
    lcd.blink_start_time = pygame.time.get_ticks()         # "on" phase
    n_on = lcd.refresh()
    assert n_off <= 1 and n_on == 1


def test_update_display_reshapes():
    lcd = HD44780X(16, 2)
    lcd.update_display(lines=4, segments=20, pixel_size=6)
    assert (len(lcd.grid), len(lcd.grid[0]), len(lcd.ddram)) == (4, 20, 80)
    assert lcd.screen.get_size() == (lcd.width, lcd.height)


def test_screenshot_and_full_frame_speed(tmp_path):
    lcd = HD44780X(80, 24)
    send(lcd, 0x0C, 0x06, 0x01)
    for r in range(24):
        lcd.goto(r, 0)
        lcd.write_string(f"{r + 1:02d} " + "The quick brown fox jumps over the lazy dog. "[: 77])
    t = time.perf_counter()
    lcd.refresh(force=True)
    full = time.perf_counter() - t
    lcd.goto(5, 5); lcd.write_data("#")
    t = time.perf_counter()
    lcd.refresh()
    delta = time.perf_counter() - t
    assert full < 2.0 and delta < 0.05
    lcd.save(tmp_path / "lcd.png")
    assert (tmp_path / "lcd.png").stat().st_size > 1000


def test_threaded_start_stop():
    lcd = HD44780X(16, 2, fps=120)
    lcd.start()
    send(lcd, 0x0C, 0x06, 0x01)
    put(lcd, "threaded")
    time.sleep(0.4)
    lcd.stop()
    assert not lcd.running and lcd._drawn is not None



# -------------------------------------------------------------------- font
def _pixels(lcd, ch, cursor=False):
    """5x8 on/off matrix sampled from the rendered glyph surface."""
    if lcd.screen is None:
        lcd.update_display()
    surf = lcd._glyph((tuple(lcd.cgrom[ord(ch)]), cursor))
    padx, pady = lcd._pad()
    size = lcd.pixel_size
    return ["".join("#" if surf.get_at((padx + c * size + size // 2,
                                        pady + r * size + size // 2))[:3]
                    == lcd.pixel_on_color else "." for c in range(lcd.cols))
            for r in range(lcd.rows)]


def test_cursor_overlays_underline_on_the_glyph():
    lcd = HD44780X(16, 2, pixel_size=6)
    with_cur = _pixels(lcd, "B", cursor=True)
    assert with_cur[7] == "#####" and with_cur[0] == "####."   # glyph kept + underline
