"""
Software model of the Hitachi HD44780 LCD Controller.
Copyright (C) 2025  Anubhav Mattoo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pygame
import threading

class HD44780():
    """
    Software model of the Hitachi HD44780 LCD Controller.

    This class emulates the behavior of the Hitachi HD44780 LCD controller,
    widely used in alphanumeric displays. It supports partial command set handling,
    data writes, cursor movement, display shifting, and internal state management.

    Key Features:
        8-bit only mode (4-bit interface not implemented).
        Supports basic commands (clear display, return home, entry mode set, etc.).
        Internal DDRAM storage model, only base CGROM (no custom characters).
        Cursor tracking and display shift operations.
        Supports display ON/OFF, cursor visibility, and blinking.

    Attributes:
        Graphic
        segments (int): The number of segments (characters) to display horizontally.
        lines (int): The number of lines (rows) on the LCD.
        cols (int): The number of columns per segment, typically 5.
        rows (int): The number of rows per segment, typically 8.
        pixel_size (int): The size (in pixels) of each logical pixel in the character grid.
        pixel_border (float): The thickness ratio of the border between pixels, ranging from 0.0 to 1.0.
        segment_margin (int): The space (in pixels) between adjacent segments of characters.
        line_margin (int): The space (in pixels) between adjacent lines of the display.
        display_border (int): The size (in pixels) of the border around the entire display.
        display_bg_color (tuple): Background color for the display (RGB values).
        segment_bg_color (tuple): Background color for a segment (RGB values).
        pixel_on_color (tuple): Color for a pixel when it is on (RGB values).
        pixel_off_color (tuple): Color for a pixel when it is off (RGB values).
        cursor_char (list): Character pattern for the cursor (8x8 pixel pattern).
        segment_width (int): Width of each segment (in pixels).
        segment_height (int): Height of each segment (in pixels).
        width (int): Total width of the display (in pixels).
        height (int): Total height of the display (in pixels).
        grid (list): Pixel state for each segment on the display [line][segment][pixel].
        backlight (bool): Flag indicating whether the backlight is on or off. NOT FUNCTIONAL BOOO!
        Controller
        running (bool): Flag indicating whether the display is currently running or not.
        cgrom (dict): A dictionary mapping character codes to their corresponding 8x8 pixel patterns.
        ddram (list): A list representing the DDRAM, where each element holds a byte of data for display.
        row_visible_address (list): A list defining the visible start address for each row in the DDRAM.
        ddram_pointer (int): Pointer to the current position in the DDRAM.
        display_on (bool): Flag indicating whether the display is turned on.
        cursor_ptr (list): A 2-element list holding the current cursor position [row, column].
        cursor_active (bool): Flag indicating whether the cursor is active (blinking or not).
        cursor_visible (bool): Flag indicating whether the cursor is visible.
        cursor_blinking (bool): Flag indicating whether the cursor is blinking.
        entry_mode_dir (bool): Determines the direction in which the cursor moves (True for right, False for left).
        entry_mode_shift (bool): Flag indicating whether the display shifts when the cursor moves.

    Example:
    The followinf example initialises a 16x2 display.
    ```python
    from hd77480 import HD44780
    lcd = HD44780(lines=2, segments=16, pixel_size=5, pixel_border=0.15, line_margin=10)
    lcd.start()
    lcd.clear()
    lcd.return_home()
    ```
    """
    def __init__(self, segments=8, lines=1, cols=5, rows=8, pixel_size=20, pixel_border=0.2,
                 segment_margin=10, line_margin=20, display_border=20):
        """
        Initialize the HD44780 display emulator graphical settings.

        Args
            segments (int): Number of segments (characters) per line. Typically 8, 16, or 20.
            lines (int): Number of display lines. Common values are 1 or 2.
            cols (int): Number of character columns (pixels) per character. Default is 5.
            rows (int): Number of character rows (pixels) per character. Default is 8.
            pixel_size (int): Size (in pixels) of each logical pixel in the character grid.
            pixel_border (float): Thickness ratio of the border between pixels (0.0 to 1.0).
            segment_margin (int): Space (in pixels) between adjacent character segments.
            line_margin (int): Space (in pixels) between adjacent display lines.
            display_border (int): Size (in pixels) of the border around the entire display.
        """

        pygame.init()

        # Configuration
        self.segments = segments
        self.lines = lines
        self.cols = cols
        self.rows = rows
        self.pixel_size = pixel_size
        self.pixel_border = pixel_border
        self.segment_margin = segment_margin
        self.line_margin = line_margin
        self.display_border = display_border

        # CGROM
        self.cgrom = {
            # 0x20–0x2F: Space and punctuation
            0x20: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # ' '
            0x21: [0x04, 0x04, 0x04, 0x04, 0x00, 0x04, 0x00, 0x00],  # '!'
            0x22: [0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00],  # '"'
            0x23: [0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A, 0x00],  # '#'
            0x24: [0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04, 0x00],  # '$'
            0x25: [0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03, 0x00],  # '%'
            0x26: [0x0C, 0x12, 0x0C, 0x16, 0x19, 0x16, 0x0D, 0x00],  # '&'
            0x27: [0x06, 0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00],  # '''
            0x28: [0x01, 0x02, 0x04, 0x04, 0x04, 0x02, 0x01, 0x00],  # '('
            0x29: [0x04, 0x02, 0x01, 0x01, 0x01, 0x02, 0x04, 0x00],  # ')'
            0x2A: [0x00, 0x04, 0x15, 0x0E, 0x0E, 0x15, 0x04, 0x00],  # '*'
            0x2B: [0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00, 0x00],  # '+'
            0x2C: [0x00, 0x00, 0x00, 0x00, 0x04, 0x04, 0x02, 0x00],  # ','
            0x2D: [0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00, 0x00],  # '-'
            0x2E: [0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00],  # '.'
            0x2F: [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x00, 0x00],  # '/'

            # 0x30–0x39: Digits '0'–'9'
            0x30: [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E, 0x00],  # '0'
            0x31: [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E, 0x00],  # '1'
            0x32: [0x0E, 0x11, 0x10, 0x0C, 0x02, 0x11, 0x1F, 0x00],  # '2'
            0x33: [0x1F, 0x08, 0x04, 0x04, 0x04, 0x11, 0x0E, 0x00],  # '3'
            0x34: [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02, 0x00],  # '4'
            0x35: [0x1F, 0x01, 0x0F, 0x10, 0x10, 0x11, 0x0E, 0x00],  # '5'
            0x36: [0x0C, 0x02, 0x01, 0x0F, 0x11, 0x11, 0x0E, 0x00],  # '6'
            0x37: [0x1F, 0x11, 0x10, 0x08, 0x04, 0x04, 0x04, 0x00],  # '7'
            0x38: [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E, 0x00],  # '8'
            0x39: [0x0E, 0x11, 0x11, 0x1E, 0x10, 0x08, 0x06, 0x00],  # '9'

            # 0x3A–0x40: More punctuation and special symbols
            0x3A: [0x00, 0x04, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00],  # ':'
            0x3B: [0x00, 0x04, 0x00, 0x00, 0x00, 0x04, 0x04, 0x00],  # ';'
            0x3C: [0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02, 0x00],  # '<'
            0x3D: [0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00, 0x00],  # '='
            0x3E: [0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08, 0x00],  # '>'
            0x3F: [0x0E, 0x11, 0x10, 0x08, 0x04, 0x00, 0x04, 0x00],  # '?'
            0x40: [0x0E, 0x11, 0x15, 0x15, 0x1D, 0x01, 0x0E, 0x00],  # '@'

            # 0x41–0x4F: Uppercase letters 'A'–'O'
            0x41: [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11, 0x00],  # 'A'
            0x42: [0x0F, 0x11, 0x11, 0x0F, 0x11, 0x11, 0x0F, 0x00],  # 'B'
            0x43: [0x0E, 0x11, 0x01, 0x01, 0x01, 0x11, 0x0E, 0x00],  # 'C'
            0x44: [0x07, 0x09, 0x11, 0x11, 0x11, 0x09, 0x07, 0x00],  # 'D'
            0x45: [0x1F, 0x10, 0x10, 0x1C, 0x10, 0x10, 0x1F, 0x00],  # 'E'
            0x46: [0x1F, 0x10, 0x10, 0x1C, 0x10, 0x10, 0x10, 0x00],  # 'F'
            0x47: [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F, 0x00],  # 'G'
            0x48: [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11, 0x00],  # 'H'
            0x49: [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E, 0x00],  # 'I'
            0x4A: [0x07, 0x02, 0x02, 0x02, 0x12, 0x12, 0x0C, 0x00],  # 'J'
            0x4B: [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11, 0x00],  # 'K'
            0x4C: [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F, 0x00],  # 'L'
            0x4D: [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11, 0x00],  # 'M'
            0x4E: [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11, 0x00],  # 'N'
            0x4F: [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E, 0x00],  # 'O'

            # 0x50–0x5A: Uppercase letters 'P'–'Z'
            0x50: [0x0F, 0x11, 0x11, 0x0F, 0x10, 0x10, 0x10, 0x00],  # 'P'
            0x51: [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D, 0x00],  # 'Q'
            0x52: [0x0F, 0x11, 0x11, 0x0F, 0x12, 0x11, 0x11, 0x00],  # 'R'
            0x53: [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x11, 0x0E, 0x00],  # 'S'
            0x54: [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x00],  # 'T'
            0x55: [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E, 0x00],  # 'U'
            0x56: [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04, 0x00],  # 'V'
            0x57: [0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A, 0x00],  # 'W'
            0x58: [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11, 0x00],  # 'X'
            0x59: [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04, 0x00],  # 'Y'
            0x5A: [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F, 0x00],  # 'Z'

            # 0x5B–0x60: Punctuation and miscellaneous symbols
            0x5B: [0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E, 0x00],  # '['
            0x5C: [0x00, 0x10, 0x08, 0x04, 0x02, 0x01, 0x00, 0x00],  # '\\'
            0x5D: [0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E, 0x00],  # ']'
            0x5E: [0x04, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00, 0x00],  # '^'
            0x5F: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],  # '_'
            0x60: [0x08, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00],  # '`'

            # 0x61–0x7A: Lowercase letters 'a'–'z'
            0x61: [0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F, 0x00],  # 'a'
            0x62: [0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E, 0x00],  # 'b'
            0x63: [0x00, 0x00, 0x0E, 0x11, 0x10, 0x11, 0x0E, 0x00],  # 'c'
            0x64: [0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F, 0x00],  # 'd'
            0x65: [0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E, 0x00],  # 'e'
            0x66: [0x06, 0x09, 0x08, 0x1C, 0x08, 0x08, 0x08, 0x00],  # 'f'
            0x67: [0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E, 0x00],  # 'g'
            0x68: [0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x11, 0x00],  # 'h'
            0x69: [0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E, 0x00],  # 'i'
            0x6A: [0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x12, 0x0C],  # 'j'
            0x6B: [0x10, 0x10, 0x11, 0x12, 0x1C, 0x12, 0x11, 0x00],  # 'k'
            0x6C: [0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E, 0x00],  # 'l'
            0x6D: [0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15, 0x00],  # 'm'
            0x6E: [0x00, 0x00, 0x1E, 0x11, 0x11, 0x11, 0x11, 0x00],  # 'n'
            0x6F: [0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E, 0x00],  # 'o'
            0x70: [0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x10, 0x10],  # 'p'
            0x71: [0x00, 0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x01],  # 'q'
            0x72: [0x00, 0x00, 0x0B, 0x0C, 0x08, 0x08, 0x08, 0x00],  # 'r'
            0x73: [0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E, 0x00],  # 's'
            0x74: [0x04, 0x04, 0x0E, 0x04, 0x04, 0x04, 0x03, 0x00],  # 't'
            0x75: [0x00, 0x00, 0x11, 0x11, 0x11, 0x11, 0x0F, 0x00],  # 'u'
            0x76: [0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04, 0x00],  # 'v'
            0x77: [0x00, 0x00, 0x11, 0x11, 0x15, 0x15, 0x0A, 0x00],  # 'w'
            0x78: [0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x00],  # 'x'
            0x79: [0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E, 0x00],  # 'y'
            0x7A: [0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F, 0x00],  # 'z'

            # 0x7B–0x7F: Final punctuation and DEL (often left blank)
            0x7B: [0x02, 0x04, 0x04, 0x08, 0x04, 0x04, 0x02, 0x00],  # '{'
            0x7C: [0x04, 0x04, 0x04, 0x00, 0x04, 0x04, 0x04, 0x00],  # '|'
            0x7D: [0x08, 0x04, 0x04, 0x02, 0x04, 0x04, 0x08, 0x00],  # '}'
            0x7E: [0x00, 0x00, 0x0A, 0x15, 0x00, 0x00, 0x00, 0x00],  # '~'
            0x7F: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]   # DEL/blank
        }

        # Controls
        self.ddram = [0x00] * 80
        self.row_visible_address = [0x00, 0x28, 0x14, 0x40]
        self.ddram_pointer = 0x00
        self.display_on = False
        self.cursor_ptr = [0x00, 0x00]
        self.cursor_active = False
        self.cursor_visible = False
        self.cursor_blinking = False
        self.entry_mode_dir = True
        self.entry_mode_shift = False

        # Colors
        self.display_bg_color = (30, 120, 30)
        self.segment_bg_color = (30, 100, 30)
        self.pixel_on_color = (0, 0, 0)
        self.pixel_off_color = (30, 85, 30)

        # Cursor
        self.cursor_char = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F]

        # Segment size
        self.segment_width = self.cols * self.pixel_size
        self.segment_height = self.rows * self.pixel_size

        # Total display size
        self.width = (segments * self.segment_width) + (segments - 1) * segment_margin + 2 * display_border
        self.height = (lines * self.segment_height) + (lines - 1) * line_margin + 2 * display_border

        # Pixel state per segment [line][segment][pixel]
        self.grid = [[[0x00] * (cols) for _ in range(segments)] for _ in range(lines)]
        self.backlight = False
        self.running = False

    def set_backlight(self, stat):
        self.backlight = stat

    def map_ddram(self) -> None:
        """
        Updates the display grid based on the contents of DDRAM.

        Iterates over each visible line and segment to map the corresponding
        character data from DDRAM to the display grid. If the character code
        is not found in the CGROM, a blank 8-row pattern is used.

        The DDRAM address wraps modulo 80, consistent with HD44780 addressing rules.

        Args:
            None

        Returns:
            None
        """
        for x in range(self.lines):
            for y in range(self.segments):
                address = self.row_visible_address[x] + y
                address %= 80
                self.grid[x][y] = self.cgrom.get(self.ddram[address], [0x00] * 8)


    def update_display(self, **kwargs):
        # Update params
        self.pixel_size = kwargs.get('pixel_size', self.pixel_size)
        self.lines = kwargs.get('lines', self.lines)
        self.segments = kwargs.get('segments', self.segments)
        
        # Segment size
        self.segment_width = self.cols * self.pixel_size
        self.segment_height = self.rows * self.pixel_size

        # Total display size
        self.width = (self.segments * self.segment_width) + (self.segments - 1) * self.segment_margin + 2 * self.display_border
        self.height = (self.lines * self.segment_height) + (self.lines - 1) * self.line_margin + 2 * self.display_border
        self.screen = pygame.display.set_mode((self.width, self.height))

    def set_cursor_ptr(self) -> None:
        """
        Updates the internal cursor pointer based on the DDRAM address.

        For a single-line display, calculates the horizontal cursor position.
        For multi-line displays, determines the line and horizontal position
        by comparing the DDRAM pointer to the starting addresses of each line.

        Args:
            None

        Returns:
            None
        """
        if self.lines == 1:
            self.cursor_ptr[0] = 0x00
            self.cursor_ptr[1] = self.ddram_pointer - self.row_visible_address[0]
        elif self.lines > 1:
            for x in range(0, len(self.row_visible_address)):
                if self.ddram_pointer >= self.row_visible_address[x]:
                    self.cursor_ptr[0] = x
                    self.cursor_ptr[1] = self.ddram_pointer - self.row_visible_address[x]

    def update_cursor(self) -> None:
        """
        Updates the appearance and blinking state of the cursor.

        If cursor blinking is enabled, sets the cursor character pattern
        to fully lit and toggles its visibility every 500 milliseconds.
        If blinking is disabled, the cursor pattern is cleared.
        After updating the cursor, recalculates the cursor position based on the DDRAM pointer.

        Args:
            None

        Returns:
            None
        """
        if self.cursor_blinking:
            self.cursor_char = [0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F]
        else:
            self.cursor_char = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        if self.cursor_blinking:
            pygame.time.wait(500)  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
        self.set_cursor_ptr()

    def update_entry_mode(self):
        """
        Updates the DDRAM pointer and display shift based on the entry mode settings.

        Adjusts the DDRAM address pointer either forward or backward depending on 
        the entry mode direction `I/D`. If display shifting is enabled 
        `S`, shifts the visible window addresses accordingly.

        Args:
            None

        Returns:
            None
        """
        if self.entry_mode_dir:
            self.ddram_pointer += 1
        else:
            self.ddram_pointer -= 1
        self.ddram_pointer %= 80
        if self.entry_mode_shift:
            if self.entry_mode_dir:
                for x in range(len(self.row_visible_address)):
                    self.row_visible_address[x] += 1
                    self.row_visible_address[x] %= 80
            else:
                for x in range(len(self.row_visible_address)):
                    self.row_visible_address[x] -= 1
                    self.row_visible_address[x] %= 80

    def shift_display(self, display_shift, shift_right):
        """
        Shifts the visible display or moves the DDRAM address pointer.

        If `display_shift` is True, shifts the visible display window left or right 
        by adjusting the row visible addresses. Otherwise, adjusts the DDRAM pointer 
        left or right.

        Args:
            display_shift (bool): 
                If True, shift the visible display window; if False, move the DDRAM pointer.
            shift_right (bool): 
                If True, shift right or increment; if False, shift left or decrement.

        Returns:
            None
        """
        if display_shift:
            if shift_right:
                for x in range(len(self.row_visible_address)):
                    self.row_visible_address[x] -= 1
                    self.row_visible_address[x] %= 80
            else:
                for x in range(len(self.row_visible_address)):
                    self.row_visible_address[x] += 1
                    self.row_visible_address[x] %= 80
        else:
            if shift_right:
                self.ddram_pointer += 1
            else:
                self.ddram_pointer -= 1
            self.ddram_pointer %= 80


    def clear_display(self):
        """
        Clears the entire display grid.

        Sets all pixels in the display grid to 'off' by filling each cell with 
        8 rows of zeros. This effectively blanks the visual representation of the screen.

        Returns:
            None
        """
        for x in range(self.lines):
            for y in range(self.segments):
                self.grid[x][y] = [0x00] * 8

    def run(self):
        """
        Runs the main event loop for the HD44780 LCD Display Emulator.

        Initializes the Pygame display window and continuously updates the 
        LCD screen contents based on internal state. Handles display updates, 
        cursor blinking, DDRAM mapping, clearing the screen when display is off,
        and user events (such as quitting the emulator).

        The loop runs at a maximum of 200 frames per second.

        Returns:
            None
        """
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("HD44780 LCD Display Emulator")
        clock = pygame.time.Clock()
        self.running = True

        while self.running:
            if self.display_on:
                self.update_cursor()
                self.map_ddram()
            else:
                self.clear_display()
            self.draw()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                clock.tick(200)

        pygame.display.quit()

    def start(self):
        """
        Start the LCD display emulator asynchronously.

        Launches the `run` method in a separate daemon thread to allow
        non-blocking operation of the LCD emulation.

        Returns:
            None
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        """
        Stop the LCD display emulator and exit the event loop.

        Signals the `run` loop to terminate and waits for the emulator
        thread to finish execution if it is still alive.

        Returns:
            None
        """
        if self.running:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join()
    
    def draw(self):
        """
        Clear and redraw the entire LCD display.

        Fills the background, redraws all lines and segments,
        and updates the screen with the latest contents.

        Returns:
            None
        """
        self.screen.fill(self.display_bg_color)
        for line in range(self.lines):
            self.draw_line(line)
        pygame.display.flip()

    def draw_line(self, line):
        """
        Draw all segments for a given line.

        Args:
            line (int): The index of the line to be drawn.

        Returns:
            None
        """
        for seg in range(self.segments):
            self.draw_segment(line, seg)

    def draw_segment(self, line, index):
        """
        Draw a single segment of the LCD display at the specified position.

        Args:
            line (int): The line number (vertical position) where the segment is drawn.
            index (int): The segment index (horizontal position) where the segment is drawn.

        Returns:
            None
        """
        x0 = self.display_border + index * (self.segment_width + self.segment_margin)
        y0 = self.display_border + line * (self.segment_height + self.line_margin)

        pygame.draw.rect(self.screen, self.segment_bg_color,
                         (x0 - 4, y0 - 4, self.segment_width + 8, self.segment_height + 8))

        def cgrom_to_bitmap(entry, cols=5, rows=8):
            """
            Convert a CGROM entry (list of bytes) into a 2D bitmap array.
            
            Args:
                entry: List of integers (one per row), usually 8 items for 8 rows.
                cols: Number of columns (default 5 for HD44780).
                rows: Number of rows (default 8 for HD44780).
            
            Returns:
                A 2D list of 0s and 1s [row][col].
            """
            bitmap = []
            for row in range(rows):
                if row >= len(entry):
                    bitmap.append([0] * cols)
                    continue
                row_bitmap = []
                for col in range(cols):
                    bit = (entry[row] >> (cols - 1 - col)) & 1
                    row_bitmap.append(bit)
                bitmap.append(row_bitmap)
            return bitmap

        bitmap = cgrom_to_bitmap(self.grid[line][index], self.cols, self.rows)
        if self.cursor_ptr == [line, index]:
            if self.cursor_visible:
                bitmap = cgrom_to_bitmap(self.cursor_char)
            if self.cursor_active:
                bitmap[7] = [1] * 5
        for row in range(self.rows):
            for col in range(self.cols):
                on = bitmap[row][col]
                self.draw_pixel(x0, y0, col, row, on)

    def draw_pixel(self, x0, y0, col, row, on):
        """
        Draw a single pixel on the LCD display.

        Args:
            x0 (int): The x-coordinate of the top-left corner of the segment.
            y0 (int): The y-coordinate of the top-left corner of the segment.
            col (int): The column index (position) of the pixel within the segment.
            row (int): The row index (position) of the pixel within the segment.
            on (bool): True if the pixel should be on, False if it should be off.

        Returns:
            None
        """
        size = self.pixel_size
        border = int(size * self.pixel_border)
        fill_size = size - 2 * border

        x = x0 + col * size + border
        y = y0 + row * size + border
        color = self.pixel_on_color if on else self.pixel_off_color

        pygame.draw.circle(self.screen, color, (x + size // 2, y + size // 2), fill_size // 2)
        # pygame.draw.rect(self.screen, color, (x, y, fill_size, fill_size))



    def _set_segment(self, data=' ', row=0, col=0):
        self.grid[col][row] = self.cgrom[ord(data)]

    # --------------------------
    # HD44780 Instruction Methods
    # --------------------------
    
    def clear(self):
        """
        Clear the display and reset the DDRAM.
        Instruction: RS=0, RW=0, DB7-DB0=0000 0001.
        This sets all DDRAM addresses to the space character and resets the cursor to the home position.
        """
        self.ddram = [0x20] * 80  # Use 0x20 (space) as the blank character.
    
    def return_home(self):
        """
        Return the cursor to the home position (address 0).
        Instruction: RS=0, RW=0, DB7-DB0=0000 0010.
        """
        self.ddram_pointer = 0x00
        self.row_visible_address = [0x00, 0x28, 0x14, 0x40] # Back to initial
    
    def entry_mode_set(self, increment=True, shift=False):
        """
        Set the entry mode. This command controls:
          - whether the DDRAM address is incremented or decremented after a data write.
          - whether the display is shifted.
        Instruction: RS=0, RW=0, DB7-DB0=0000 01 I/D S (I = increment, D = decrement, S = shift).
        """
        self.entry_mode_dir = increment
        self.entry_mode_shift = shift
    
    def display_control(self, display=True, cursor=False, blink=False):
        """
        Control the display on/off, cursor visibility, and blinking.
        Instruction: RS=0, RW=0, DB7-DB0=0000 1DCB  (D=Display, C=Cursor, B=Blink).
        """
        self.display_on = display
        self.cursor_active = cursor
        self.cursor_visible = cursor
        self.cursor_blinking = blink

    def cursor_control(self, display_shift=False, shift_right=True):
        """
        Move the cursor and/or shift the display.
        Instruction: RS=0, RW=0, DB7-DB0=0001 S/C R/L
          - S/C = 0: move cursor; 1: shift display.
          - R/L = 1: shift right; 0: shift left.
        """
        self.shift_display(display_shift, shift_right)
    
    def function_set(self, eight_bit_mode=True, two_lines=True, font_5x10=False):
        """
        UNSUPPORTED: NO 4-bit MODE BOOOOOOOOO!
        Set the interface data length, number of display lines, 
        and character font.
        Instruction: RS=0, RW=0, DB7-DB0=001DLNF- (D=Data length, L = number of lines, F=font).
        """
        self._eight_bit_mode = eight_bit_mode
        self._two_lines = two_lines
        self._font_5x10 = font_5x10
        # Optional: Adjust the simulation’s dimensions here based on the new settings.


    def set_ddram_addr(self, addr):
        """
        Set the DDRAM address, which moves the cursor.
        Instruction: RS=0, RW=0, DB7-DB0=1AAAAAAA (A0-A6 = DDRAM address).
        This method maps the DDRAM address to a grid coordinate.
        """
        self.ddram_pointer = addr % 80  # Wrap-around the 80 DDRAM cells.
    
    def set_cgram_addr(self, addr):
        """
        UNSUPPORTED: NO CGRAM BOO!
        Set the CGRAM address to prepare for writing custom character patterns.
        Instruction: RS=0, RW=0, DB7-DB0=01AAAAAA (A0-A5 = CGRAM address).
        Subsequent data writes (with RS=1) will store custom pattern data.
        """
        self.cgram_address = addr % 64  # There are 64 bytes (6 bits) in CGRAM.
        self.in_cgram_mode = True
    
    def write_data(self, data):
        """
        Write data to the DDRAM or CGRAM (depending on mode).
        Instruction: RS=1, RW=0, data=DB7-DB0.
        If in CGRAM mode, the custom character bytes are stored.
        Otherwise, the character value is written to DDRAM.
        """
        # if self.in_cgram_mode:
        #     # Write one 5-bit row of a custom character.
        #     char_index = self.cgram_address // 8  # Which custom char (0-7)
        #     row_index = self.cgram_address % 8     # Which row (0-7)
        #     # Only 5 bits are used in HD44780 custom characters.
        #     self.cgram[char_index][row_index] = data & 0x1F
        #     self.cgram_address = (self.cgram_address + 1) % 64
        #     # Optionally, update the cgrom mapping so that this custom character
        #     # becomes available via its index.
        #     self.cgrom[char_index] = self.cgram[char_index]
        # else:
        # Write to DDRAM
        self.ddram[self.ddram_pointer] = data[0]
        self.update_entry_mode() # Update display
    
    def read_data(self):
        """
        Read data from DDRAM or CGRAM (depending on the current mode).
        Instruction: RS=1, RW=1, data=DB7-DB0.
        After reading, the addressing pointer advances (according to the entry mode).
        Returns the data from the appropriate memory region.
        """
        # if self.in_cgram_mode:
        #     char_index = self.cgram_address // 8
        #     row_index = self.cgram_address % 8
        #     data = self.cgram[char_index][row_index]
        #     self.cgram_address = (self.cgram_address + 1) % 64
        #     return data
        # else:
        data = self.ddram[self.ddram_pointer]
        self.update_entry_mode() #Update display
        return data

    def command(self, rs: int, rw: int, db: int) -> None | int:
        if rs == 1: # Register Select Data
            if rw == 1: # Read
                data = self.read_data()
                return data & 0xFF
            else: # Write
                self.write_data(db)
        else: # Register Select Instruction
            if rw == 1: # Read Busy
                # What you gonna do? huh?
                # TODO: Add BUSY
                return 0x00
            else:
                db_ = db
                dbl = [0] * 8
                for i in range(8):
                    dbl[i] = (db_ >> i) & 0x1
                if dbl[7]: # DDRAM Address
                    self.set_ddram_addr(db_)
                elif dbl[6]: # CGRAM Address
                    pass # TODO: Add CGRAM
                elif dbl[5]: # Function Set
                    self.function_set(bool(dbl[4]), bool(dbl[3]), bool(dbl[2]))
                elif dbl[4]: # Cursor Control
                    self.cursor_control(bool(dbl[3]), bool(dbl[2]))
                elif dbl[3]: # Display Control
                    self.display_control(bool(dbl[2]), bool(dbl[1]), bool(dbl[0]))
                elif dbl[2]: # Entry Mode Set
                    self.entry_mode_set(bool(dbl[1]), bool(dbl[0]))
                elif dbl[1]: # Return Home
                    self.return_home()
                elif dbl[0]: # Clear
                    self.clear()
                else:
                    raise Warning("Illegal Instruction")