from __future__ import annotations

import atexit
import itertools
import sys
import termios
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, TypeVar

import readchar

from visual import ansi, utils

# config
NUM_COLOR = ansi.red
TXT_COLOR = ansi.yellow | ansi.italic
OP_COLOR = ansi.green
FUNC_COLOR = ansi.blue
FRAC_COLOR = ansi.reset
PAREN_COLOR = ansi.reset
FRAC_PADDING = 1

var = 10



def terminal_echo(enabled: bool):
	try:
		fd = sys.stdin.fileno()
		iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)
		
		if enabled:
			lflag |= termios.ECHO
		else:
			lflag &= ~termios.ECHO
		
		termios.tcsetattr(fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
	except termios.error:
		pass
	except ValueError:
		pass



atexit.register(terminal_echo, True)
terminal_echo(False)

T = TypeVar("T")



def flatten(nested: List[List[T]]) -> List[T]:
	"""Non-recursive list flattener."""
	return list(itertools.chain.from_iterable(nested))



def obj_index(iterable: Iterable, obj: object) -> int:  # todo: use Expression.replace() instead
	"""The same as `list.index()`, but compares the actual objects using `is` instead of their values using `==`."""
	for index, item in enumerate(iterable):
		if item is obj:
			return index
	
	raise ValueError  # not found



def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	sys.stderr.flush()



@dataclass(frozen=True)
class ScreenOffset:  # todo: a way to put the cursor at the end, without knowing the width (performance)
	row: int
	col: int
	
	def __post_init__(self):
		assert self.row >= 0
		assert self.col >= 0
	
	def left(self, distance: int):
		return ScreenOffset(self.row, self.col - distance)
	
	def right(self, distance: int):
		return ScreenOffset(self.row, self.col + distance)
	
	def up(self, distance: int):
		return ScreenOffset(self.row - distance, self.col)
	
	def down(self, distance: int):
		return ScreenOffset(self.row + distance, self.col)



def cursor_string(off: ScreenOffset) -> str:
	off = off or ScreenOffset(0, 0)
	assert off.row >= 0
	assert off.col >= 0
	return f"\033[{off.row + 1};{off.col + 1}H"



def str_align(s: str, /, width: int) -> str:
	return f"{s:^{width}}"



def list_align(ls: List[str], /, width: int) -> List[str]:
	if width == 0:
		return []
	
	out = []
	out.extend(ls)
	
	left = False
	while len(out) < width:
		if left := not left:
			out.append("")
		else:
			out.insert(0, "")
	
	assert len(out) == width, f"{len(out)} != {width}"
	return out



def align_space(expr_width: int, target_width: int):
	if expr_width == 0:
		return target_width // 2
	else:
		return f"{'x' * expr_width :^{target_width}}".index("x")



@dataclass(frozen=True)
class RenderOutput:
	lines: List[str]
	colors: List[List[str]]  # maybe list of tuples would be better?
	baseline: int
	width: int
	cursor: Optional[ScreenOffset]
	
	def __post_init__(self):  # sanity check
		assert 1 == len(set(len(x) for x in self.lines)), "All lines must have the same length"
		assert 1 == len(set(len(x) for x in self.colors)), "All colors must have the same length"
		assert len(self.lines) == len(self.colors)
		assert self.baseline >= 0
		assert self.width >= 0



class Expression:
	def children(self) -> List[Expression]:
		raise NotImplementedError
	
	def bfs_children(self) -> List[Expression]:
		return list(self._bfs_children())
	
	def _bfs_children(self) -> Iterator[Expression]:
		yield self
		for child in self.children():
			yield from child._bfs_children()
	
	def parentof(self, child: Expression) -> Optional[Expression]:
		assert isinstance(child, Expression)
		for parent in self.bfs_children():
			for c in parent.children():
				if c is child:  # `child in parent.children()` uses `==` as well as `is`
					return parent
		return None
	
	def replace(self, old: Expression, new: Expression) -> bool:
		assert isinstance(old, Expression)
		assert isinstance(new, Expression)
		for parent in self.bfs_children():
			for child in parent.children():
				if child is old:
					assert isinstance(parent, Row)
					parent.items[obj_index(parent.items, old)] = new
					return True
		return False
	
	def neighbor_left(self, node: Expression) -> Optional[Expression]:
		bfs_line = list(reversed(self.bfs_children()))
		for a, b in zip(bfs_line, bfs_line[1:]):
			if a is node:
				return b
		return None
	
	
	def neighbor_right(self, node: Expression) -> Optional[Expression]:
		bfs_line = self.bfs_children()
		for a, b in zip(bfs_line, bfs_line[1:]):
			if a is node:
				return b
		return None
	
	
	def width(self):  # SLOW!
		return len(self.render().lines[0])
	
	def render(self) -> RenderOutput:
		raise NotImplementedError
	
	def simplify(self):
		for child in self.children():
			child.simplify()
	
	def display(self, cursor: bool = True, colormap: bool = True, code: bool = True):  # todo: curses
		"""Render the expression onto the screen"""
		r = self.render()
		
		if not r.cursor:
			eprint(ansi.red("WARNING:"), "cursor is not present")
		
		output = []
		for line, color in zip(r.lines, r.colors):
			assert len(line) == len(color)
			colored_line = []
			
			for ch, pixel in zip(line, color):
				colored_line.append(f"{pixel}{ch}{ansi.reset}")
			
			output.append("".join(colored_line))
		
		if colormap:
			output.append("")
			for row in r.colors:
				line = []
				for color in row:
					line.append(f"{color or ansi.reset}▒{ansi.reset}")
				output.append("".join(line))
		
		if code:
			eval_result = utils.run(str(self))
			output.append("")
			output.append(f">>> {self}")
			output.append(f"{eval_result}")
		
		output.append("")  # newline at the end of the output
		
		if cursor:
			output.append(cursor_string(r.cursor))
		
		# clear, home, content
		print("\033[2J\033[H" + "\n".join(output), end="", flush=True)
	
	
	def press_key(self, key: str, root: Expression = None, skip_empty: bool = False) -> bool:
		"""Only Text can have a cursor (pass the key on by default)"""
		root = root or self
		for child in self.children():
			accepted = child.press_key(key, root)
			if accepted:
				return True  # cursor could be moved multiple times if we wouldn't stop right there
		return False  # not accepted yet... (dead end)
	
	
	def __str__(self):
		raise NotImplementedError



class Text(Expression):
	def __init__(self, text: str = "", cursor: Optional[ScreenOffset] = None):
		self.text: str = text
		self.cursor: Optional[ScreenOffset] = cursor
	
	def children(self) -> List[Expression]:
		return []
	
	def colorize(self) -> List[str]:  # list of colors
		output = []
		for char in self.text:
			if char.isalpha():
				output.append(TXT_COLOR)
			elif char.isdigit():
				output.append(NUM_COLOR)
			elif char in "+-*/=|&^@":
				output.append(OP_COLOR)
			else:
				output.append("")
		
		# todo: context-aware highlighting (string before paren is function, etc)
		return output
	
	def render(self) -> RenderOutput:
		return RenderOutput([self.text], [self.colorize()], 0, len(self.text), self.cursor)
	
	
	def press_key(self, key: str, root: Expression = None, skip_empty: bool = True) -> bool:
		assert root, "Text must always be inside row()."
		
		if not self.cursor:
			return False  # we don't have the cursor, move on
		
		if key.isprintable():
			eprint(ansi.yellow(f"INSERT: '{key}'"))
			self.text: str = self.text[:self.cursor.col] + key + self.text[self.cursor.col:]
			self.cursor = self.cursor.right(1)
			
			# todo: expanders (run always for all texts?)
			before_cursor = self.text[:self.cursor.col]
			
			if before_cursor.endswith("/"):
				eprint(ansi.red("INSERTING FRACTION"))
				back = len("/")
				before_cursor = before_cursor[:-back]
				after_cursor = self.text[self.cursor.col:]
				self.text = before_cursor + after_cursor
				self.cursor = self.cursor.left(back)
				
				parent = root.parentof(self)
				if isinstance(parent, Row):
					idx = obj_index(parent.children(), self)
					parent.items.pop(idx)  # remove myself
					parent.items.insert(idx, fraction(text(before_cursor), text(after_cursor, cursor=ScreenOffset(0, 0))))
			
			if before_cursor.endswith("("):
				eprint(ansi.red("INSERTING PARENTHESIS"))
				back = len("(")
				before_cursor = before_cursor[:-back]
				after_cursor = self.text[self.cursor.col:]
				self.text = before_cursor + after_cursor
				self.cursor = self.cursor.left(back)
				
				parent = root.parentof(self)
				if isinstance(parent, Row):
					idx = obj_index(parent.children(), self)
					parent.items.pop(idx)  # remove myself
					parent.items.insert(idx, row(text(before_cursor), parenthesis(text(after_cursor, cursor=ScreenOffset(0, 0)))))  # todo: take more objects, maybe? (desmos)
			
			if before_cursor.endswith("sqrt("):  # todo
				eprint(ansi.red("INSERTING SQUARE ROOT"))
				back = len("sqrt(")
				self.text = self.text[:self.cursor.col - back] + self.text[self.cursor.col:]
				self.cursor = self.cursor.left(back)
				eprint(self.text)
				assert False
		
		if key == readchar.key.BACKSPACE:
			if self.cursor.col == 0:
				# try to remove fraction
				parent1 = root.parentof(self)
				parent2 = root.parentof(parent1)
				if isinstance(parent1, Row) and isinstance(parent2, Fraction):
					if parent1 is parent2.denominator:
						eprint(ansi.yellow("REMOVING FRACTION"))
						frac_contents = parent2.numerator.items + parent2.denominator.items
						root.replace(parent2, row(*frac_contents))
					else:  # fraction will not get deleted if backspace was pressed inside the numerator
						self.press_key(readchar.key.LEFT, root)
			
			
			
			
			
			
			else:
				eprint(ansi.yellow(f"REMOVE: '{self.text[self.cursor.col - 1]}'"))
				self.text: str = self.text[:self.cursor.col - 1] + self.text[self.cursor.col:]
				self.cursor = self.cursor.left(1)
				assert self.cursor.col >= 0
		
		if key == readchar.key.LEFT:
			if self.cursor.col > 0:
				self.cursor = self.cursor.left(1)
			else:
				self.press_key(readchar.key.UP, root, skip_empty=False)
		
		if key == readchar.key.RIGHT:
			if self.cursor.col < self.width():  # + one space at the end
				self.cursor = self.cursor.right(1)
			else:
				self.press_key(readchar.key.DOWN, root, skip_empty=False)
		
		if key == readchar.key.UP:
			bfs_line = root.bfs_children()
			for expr in reversed(bfs_line[:obj_index(bfs_line, self)]):
				if isinstance(expr, Text):  # where we can jump to
					if skip_empty and not expr.text: continue
					eprint("target:", expr.__class__.__name__, ansi.green(f"'{expr}'"))
					self.cursor = None
					# expr.cursor = ScreenOffset(0, 0)  # start of the text field
					expr.cursor = ScreenOffset(0, expr.width())  # end of the text field
					break
			else:  # no break happened before
				eprint(ansi.red("WARNING:"), "ran out of targets (DOWN)")
		
		if key == readchar.key.DOWN:
			bfs_line = root.bfs_children()
			for expr in bfs_line[obj_index(bfs_line, self) + 1:]:
				if isinstance(expr, Text):  # where we can jump to
					if skip_empty and not expr.text: continue
					eprint("target:", expr.__class__.__name__, ansi.green(f"'{expr}'"))
					self.cursor = None
					expr.cursor = ScreenOffset(0, 0)  # start of the text field
					break
			else:  # no break happened before
				eprint(ansi.red("WARNING:"), "ran out of targets (DOWN)")
		
		return True  # keystroke accepted
	
	def __str__(self):
		return self.text



class Row(Expression):
	def __init__(self, items: List[Expression]):
		self.items = items
	
	def children(self) -> List[Expression]:
		return self.items
	
	def render(self) -> RenderOutput:
		rr = [x.render() for x in self.items]
		baseline = max(r.baseline for r in rr)
		
		for r in rr:
			for _ in range(baseline - r.baseline):  # todo: extend
				r.lines.insert(0, " " * r.width)  # baseline top padding
				r.colors.insert(0, list_align([""], r.width))  # baseline top padding
		
		width_so_far = 0
		for r in rr:
			if r.cursor:
				cursor = r.cursor.down(baseline - r.baseline).right(width_so_far)
				break
			width_so_far += r.width
		else:  # no break happened before
			cursor = None
		
		lines = []
		colors = []
		for line_index in range(max(len(r.lines) for r in rr)):
			l = [str_align(r.lines[line_index] if len(r.lines) > line_index else "", r.width) for r in rr]
			c = [list_align(r.colors[line_index] if len(r.colors) > line_index else "", r.width) for r in rr]
			lines.append("".join(l))
			colors.append(flatten(c))
		
		return RenderOutput(lines, colors, baseline, sum(r.width for r in rr), cursor)
	
	def simplify(self):
		output = []
		
		# flatten rows
		for child in self.children():
			if isinstance(child, Row):
				output.extend(child.items)
			else:
				output.append(child)
		
		# join adjacent texts
		while True:
			for idx, (a, b) in enumerate(zip(output, output[1:])):
				if isinstance(a, Text) and isinstance(b, Text):
					if b.cursor:
						a.cursor = ScreenOffset(0, a.width()).right(b.cursor.col)
					a.text = f"{a.text}{b.text}"
					output.pop(idx + 1)
					break
			else:
				break
		
		# continue the recursion
		for child in output:
			child.simplify()  # fractions only, of course
		
		# todo: insert space into the text between adjacent fractions
		
		self.items = output
	
	
	def __str__(self):
		return "".join([str(x) for x in self.items])



class Fraction(Expression):
	def __init__(self, numerator: Row, denominator: Row):
		assert isinstance(numerator, Row)
		assert isinstance(denominator, Row)
		self.numerator = numerator
		self.denominator = denominator
	
	
	def children(self) -> List[Expression]:
		return [self.numerator, self.denominator]
	
	def render(self) -> RenderOutput:
		n = self.numerator.render()
		d = self.denominator.render()
		w = 2 * FRAC_PADDING + max(n.width, d.width)
		
		baseline = len(n.lines)
		assert n.cursor is None or d.cursor is None, "At least one of cursors must be None"
		
		cursor = None
		if n.cursor:
			cursor = n.cursor.right(align_space(n.width, w))
		
		if d.cursor:
			cursor = d.cursor.right(align_space(d.width, w)).down(baseline + 1)
		
		output = []
		output.extend([str_align(l, w) for l in n.lines])
		output.append("─" * w)
		output.extend([str_align(l, w) for l in d.lines])
		
		colors = []
		colors.extend([list_align(c, w) for c in n.colors])
		colors.append([FRAC_COLOR] * w)
		colors.extend([list_align(c, w) for c in d.colors])
		
		return RenderOutput(output, colors, baseline, w, cursor)
	
	
	def __str__(self):
		return f"(({self.numerator}) / ({self.denominator}))"



class Parenthesis(Expression):
	def __init__(self, expr: Expression):
		self.expr: Expression = expr
	
	def children(self) -> List[Expression]:
		return [self.expr]
	
	def render(self) -> RenderOutput:
		r = self.expr.render()
		
		cursor = r.cursor.right(1) if r.cursor else None
		
		if len(r.lines) == 1:
			return RenderOutput([f"({r.lines[0]})"], [[PAREN_COLOR] + r.colors[0] + [PAREN_COLOR]], 0, r.width + 2, cursor)
		else:
			output = []
			colors = []
			for index, (line, color) in enumerate(zip(r.lines, r.colors)):
				if index == 0:
					lparen, rparen = "⎛", "⎞"
				elif index < len(r.lines) - 1:
					lparen, rparen = "⎜", "⎟"
				else:
					lparen, rparen = "⎝", "⎠"
				
				output.append(f"{lparen}{line}{rparen}")
				colors.append([PAREN_COLOR] + list_align(color, r.width) + [PAREN_COLOR])
			
			return RenderOutput(output, colors, r.baseline, r.width + 2, cursor)
	
	def __str__(self):
		return f"({self.expr})"



def row(*items: Expression) -> Row:
	return Row(list(items))



def text(txt: str = "", cursor: Optional[ScreenOffset] = None) -> Row:
	return row(Text(txt, cursor))



def fraction(numerator: Row, denominator: Row) -> Row:
	assert isinstance(numerator, Row)
	assert isinstance(denominator, Row)
	return row(
		text(),  # jump target
		Fraction(
			numerator=numerator,
			denominator=denominator,
		),
		text(),  # jump target
	)



def parenthesis(expr: Row) -> Row:
	assert isinstance(expr, Row)
	return row(
		text(),  # jump target
		Parenthesis(expr),
		text(),  # jump target
	)



expression = row(
	parenthesis(
		fraction(
			text("1"),
			text("2"),
		),
	),
	text(" + var * "),
	fraction(
		fraction(
			text("444444444444"),
			row(text("999"), text("5555555555555", cursor=ScreenOffset(0, 1))),
		),
		text("666666666666"),
	),
)

# expression = row(
# 	fraction(
# 		text("11111"),
# 		text("555", cursor=ScreenOffset(0, 1)),
# 	),
# 	text(" + var"),
# )

# expression = text("123456789", cursor=ScreenOffset(0, 1))

while True:
	expression.simplify()
	expression.display()
	
	key = readchar.readkey()
	eprint(f"\nkey pressed: {ansi.blue}0x{key.encode('utf8').hex()}{ansi.reset} ({list(readchar.key.__dict__.keys())[list(readchar.key.__dict__.values()).index(key)] if key in readchar.key.__dict__.values() else key})")
	
	if key == readchar.key.CTRL_C:
		break
	
	expression.press_key(key)

expression.display(cursor=False)
