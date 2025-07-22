import pytest

from hd44780 import HD44780


@pytest.fixture
def lcd(request) -> HD44780:
	lines, segments = request.param
	return HD44780(lines=lines, segments=segments, pixel_size=5, pixel_border=0.15, line_margin=10)

@pytest.mark.parametrize('lcd', [(1, 8), (1, 16), (1, 20), (1, 80), (2, 8), (2, 16), (2, 20), (2, 40), (4, 8), (4, 16), (4, 20)], indirect=True)
def test_init(lcd: HD44780):
	lcd.start()
	lcd.clear()
	lcd.return_home()
	assert lcd.ddram_pointer == 0x00, f"DDRAM Address at init is 0x{lcd.ddram_pointer:02X}, should be 0x00"
	lcd.thread.join(2)
	lcd.stop()

@pytest.mark.parametrize('lcd', [(1, 8), (1, 16), (1, 20), (1, 80), (2, 8), (2, 16), (2, 20), (2, 40), (4, 8), (4, 16), (4, 20)], indirect=True)
def test_cursor(lcd: HD44780):
	lcd.start()
	lcd.clear()
	lcd.return_home()
	lcd.entry_mode_set(increment=True, shift=False)
	assert lcd.display_on == False, f"Display should not be on"
	lcd.display_control(display=True, cursor=False, blink=False)
	assert lcd.display_on == True, f"Display should be on"
	assert lcd.cursor_active == False, f"Cursor should be inactive"
	lcd.display_control(display=True, cursor=True, blink=False)
	assert lcd.cursor_active == True, f"Cursor should be active"
	assert lcd.cursor_blinking == False, f"Cursor should not be blinking"
	lcd.display_control(display=True, cursor=True, blink=True)
	assert lcd.cursor_active == True, f"Cursor should be active"
	assert lcd.cursor_blinking == True, f"Cursor should be blinking"
	lcd.thread.join(2)
	lcd.stop()

@pytest.mark.parametrize('lcd', [(1, 8), (1, 16), (1, 20), (1, 80), (2, 8), (2, 16), (2, 20), (2, 40), (4, 8), (4, 16), (4, 20)], indirect=True)
def test_cursor_text(lcd: HD44780):
	lcd.start()
	lcd.clear()
	lcd.return_home()
	lcd.entry_mode_set(increment=True, shift=False)
	lcd.display_control(display=True, cursor=False, blink=False)
	assert lcd.ddram_pointer == 0x00, f"DDRAM Address at init is 0x{lcd.ddram_pointer:02X}, should be 0x00"
	lcd.write_data('H')
	assert lcd.ddram[0x00] == ord('H'), f"Incorrect Data at 0x{lcd.ddram[0x00]:02X}, should be 0x{ord('H'):02X}"
	assert lcd.ddram_pointer == 0x01, f"DDRAM Address at init is 0x{lcd.ddram_pointer:02X}, should be 0x00"
	lcd.thread.join(2)
	lcd.stop()

@pytest.mark.parametrize('lcd', [(1, 8), (1, 16), (1, 20), (1, 80), (2, 8), (2, 16), (2, 20), (2, 40), (4, 8), (4, 16), (4, 20)], indirect=True)
def test_hello(lcd: HD44780):
	from time import sleep
	lcd.start()
	lcd.clear()
	lcd.return_home()
	lcd.entry_mode_set(increment=True, shift=False)
	lcd.display_control(display=True, cursor=False, blink=False)
	assert lcd.ddram_pointer == 0x00, f"DDRAM Address at init is 0x{lcd.ddram_pointer:02X}, should be 0x00"
	lcd.ddram_pointer = 0x38
	for x in "Hello, MX/11!":
		lcd.write_data(x)
		sleep(0.37)
		lcd.cursor_control(display_shift=True, shift_right=False)
		sleep(0.37)
	lcd.thread.join(2)
	lcd.stop()