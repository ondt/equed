from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Tuple, Union



def clean(s: str) -> str:
	return re.sub(r"\033 \[ [;\d]* [A-Za-z]", "", s, re.VERBOSE)



class Ansi:
	def __init__(self, codes: Union[int, List[Tuple[int, int]]], off_code: int = 0):
		self.codes: List[Tuple[int, int]] = [(codes, off_code)] if isinstance(codes, int) else codes
	
	
	@lru_cache
	def __str__(self) -> str:
		return f"\033[{';'.join([str(c[0]) for c in self.codes])}m"
	
	
	def __invert__(self) -> Ansi:
		return Ansi([(c[1], c[0]) for c in self.codes])
	
	
	def __ror__(self, other: Ansi) -> Ansi:  # for sum() to work
		if other == 0:
			return self
	
	
	def __or__(self, other: Ansi) -> Ansi:
		if isinstance(other, Ansi):
			return Ansi(self.codes + other.codes)
	
	
	def __call__(self, text: str) -> str:
		return f"{self}{text}{~self}"



reset = Ansi(0)
reset_color = Ansi(39)
reset_bg_color = Ansi(49)

bold = Ansi(1, 22)
faint = Ansi(2, 22)
blink = Ansi(5, 25)
inv = Ansi(7, 27)
hide = Ansi(8, 28)

italic = Ansi(3, 23)
underline = Ansi(4, 24)
underline_double = Ansi(21)
strikethrough = Ansi(9, 29)
overline = Ansi(53, 55)

black = Ansi(30, 39)
red = Ansi(31, 39)
green = Ansi(32, 39)
yellow = Ansi(33, 39)
blue = Ansi(34, 39)
magenta = Ansi(35, 39)
cyan = Ansi(36, 39)
white = Ansi(37, 39)
bright_black = Ansi(90, 39)
bright_red = Ansi(91, 39)
bright_green = Ansi(92, 39)
bright_yellow = Ansi(93, 39)
bright_blue = Ansi(94, 39)
bright_magenta = Ansi(95, 39)
bright_cyan = Ansi(96, 39)
bright_white = Ansi(97, 39)

bg_black = Ansi(40, 49)
bg_red = Ansi(41, 49)
bg_green = Ansi(42, 49)
bg_yellow = Ansi(43, 49)
bg_blue = Ansi(44, 49)
bg_magenta = Ansi(45, 49)
bg_cyan = Ansi(46, 49)
bg_white = Ansi(47, 49)
bg_bright_black = Ansi(100, 49)
bg_bright_red = Ansi(101, 49)
bg_bright_green = Ansi(102, 49)
bg_bright_yellow = Ansi(103, 49)
bg_bright_blue = Ansi(104, 49)
bg_bright_magenta = Ansi(105, 49)
bg_bright_cyan = Ansi(106, 49)
bg_bright_white = Ansi(107, 49)
