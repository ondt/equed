from __future__ import annotations

import atexit
import itertools
import sys
import termios
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, TypeVar

import readchar

from visual import ansi, utils

# editing
SKIP_DENOMINATOR = False  # maple, mathquill: True
MAPLE_FRAC_DEL = False  # maple removes last char from denominator if backspace is pressed right after the fraction
FRAC_INS_METHOD = "maple"  # possible values: maple, split, empty

# rendering
FRAC_PADDING = 1
FRAC_SHORTER_ENDS = True

# syntax highlighting colors
NUM_COLOR = ansi.red
TXT_COLOR = ansi.yellow | ansi.italic
OP_COLOR = ansi.green
FUNC_COLOR = ansi.blue
FRAC_COLOR = ansi.reset
PAREN_COLOR = ansi.reset
XPEREN_COLOR = ansi.blue  # unmatched paren

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
		assert sum(ch is child for ch in self.bfs_children()) == 1
		for parent in self.bfs_children():
			for c in parent.children():
				if c is child:  # `child in parent.children()` uses `==` as well as `is`
					return parent
		return None
	
	def replace(self, old: Expression, new: Expression) -> bool:
		assert isinstance(old, Expression)
		assert isinstance(new, Expression)
		assert sum(ch is old for ch in self.bfs_children()) == 1
		for parent in self.bfs_children():
			for child in parent.children():
				if child is old:
					assert isinstance(parent, Row)
					parent.items[obj_index(parent.items, old)] = new
					return True
		return False
	
	def delete(self, old: Expression) -> bool:
		assert isinstance(old, Expression)
		assert sum(ch is old for ch in self.bfs_children()) == 1
		for parent in self.bfs_children():
			for child in parent.children():
				if child is old:
					assert isinstance(parent, Row)
					parent.items.pop(obj_index(parent.items, old))
					return True
		return False
	
	def neighbor_left(self, node: Expression, skip: int = 1) -> Optional[Expression]:
		assert sum(ch is node for ch in self.bfs_children()) == 1
		parent = self.parentof(node)
		assert isinstance(parent, Row)
		index = obj_index(parent.items, node) - skip
		return parent.items[index] if index in range(len(parent.items)) else None
	
	def neighbor_right(self, node: Expression, skip: int = 1) -> Optional[Expression]:
		assert sum(ch is node for ch in self.bfs_children()) == 1
		parent = self.parentof(node)
		assert isinstance(parent, Row)
		index = obj_index(parent.items, node) + skip
		return parent.items[index] if index in range(len(parent.items)) else None
	
	def all_neighbors_left(self, node: Expression, skip: int = 1) -> List[Expression]:
		assert sum(ch is node for ch in self.bfs_children()) == 1
		parent = self.parentof(node)
		assert isinstance(parent, Row)
		index = obj_index(parent.items, node) - skip
		return parent.items[:index]
	
	def all_neighbors_right(self, node: Expression, skip: int = 1) -> List[Expression]:
		assert sum(ch is node for ch in self.bfs_children()) == 1
		parent = self.parentof(node)
		assert isinstance(parent, Row)
		index = obj_index(parent.items, node) + skip
		return parent.items[index:]
	
	def width(self, root: Row = None, rparent: Row = None, parent: Expression = None):  # SLOW!
		return len(self.render(root=root, rparent=rparent, parent=parent).lines[0])
	
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		raise NotImplementedError
	
	def simplify(self, root: Row = None, rparent: Row = None, parent: Expression = None):
		for child in self.children():
			child.simplify(root, rparent, self)
	
	def display(self, cursor: bool = True, colormap: bool = True, code: bool = True, dump: bool = True):  # todo: curses
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
			output.append(f"{ansi.blue('code:')} {self}")
			output.append(f"{eval_result}")
		
		if dump:
			output.append("")
			output.append(f"{ansi.blue('repr:')} {repr(expression)}")
		
		output.append("")  # newline at the end of the output
		
		if cursor:
			output.append(cursor_string(r.cursor))
		
		# clear, home, content
		print("\033[2J\033[H" + "\n".join(output), end="", flush=True)
	
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		raise NotImplementedError
	
	
	def __str__(self):
		raise NotImplementedError
	
	def __repr__(self):
		raise NotImplementedError



class Text(Expression):
	def __init__(self, text: str = "", cursor: Optional[ScreenOffset] = None):
		self.text: str = text
		self.cursor: Optional[ScreenOffset] = cursor
	
	def children(self) -> List[Expression]:
		return []
	
	def colorize(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> List[str]:  # list of colors
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
	
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		return RenderOutput([self.text], [self.colorize(root, rparent, parent)], 0, len(self.text), self.cursor)
	
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		assert root is not None, "Text must always be inside a Row."
		
		if not self.cursor:
			return False  # we don't have the cursor, move on
		
		if key.isprintable():
			before_cursor, after_cursor = self.text[:self.cursor.col], self.text[self.cursor.col:]
			sequence = before_cursor + key
			
			# todo: expanders (run always for all texts?)
			if sequence.endswith("\\frac"):
				self.text = before_cursor[:-4] + after_cursor
				self.cursor = self.cursor.left(4)
				root.press_key("/")
			
			elif sequence.endswith("sqrt("):
				# todo
				pass
			
			elif key == "/":  # todo: shift-/ to split?
				eprint(ansi.yellow("INSERTING FRACTION"))
				if FRAC_INS_METHOD == "maple":
					root.replace(self, row(fraction(text(before_cursor), text(cursor=ScreenOffset(0, 0))), text(after_cursor)))
				elif FRAC_INS_METHOD == "split":
					root.replace(self, fraction(text(before_cursor), text(after_cursor, cursor=ScreenOffset(0, 0))))
				elif FRAC_INS_METHOD == "empty":
					root.replace(self, row(text(before_cursor), fraction(text(cursor=ScreenOffset(0, 0)), text()), text(after_cursor)))
				else:
					eprint(ansi.red("FRAC_INS_METHOD contains invalid value"))
					exit(1)
			
			
			elif key == "(":
				eprint(ansi.yellow("INSERTING LPAREN"))
				parent = root.parentof(self)
				assert isinstance(parent, Row)
				root.replace(self, row(text(before_cursor), lparen(), text(after_cursor, cursor=ScreenOffset(0, 0))))
			
			elif key == ")":
				eprint(ansi.yellow("INSERTING RPAREN"))
				parent = root.parentof(self)
				assert isinstance(parent, Row)
				root.replace(self, row(text(before_cursor), rparen(), text(after_cursor, cursor=ScreenOffset(0, 0))))
			
			else:
				eprint(ansi.yellow(f"INSERTING TEXT: '{key}'"))
				self.text: str = before_cursor + key + after_cursor
				self.cursor = self.cursor.right(1)
		
		if key == readchar.key.BACKSPACE:
			# cursor at the beginning of the text field means some special del procedure is to be executed
			if self.cursor.col == 0:
				# try to remove lparen or rparen
				neighbor_left = root.neighbor_left(self)
				if isinstance(neighbor_left, Paren):
					eprint(ansi.yellow("REMOVING PAREN"))
					root.delete(neighbor_left)
					return True  # keystroke accepted
				
				# next to a fraction --> jump to the denominator and press BACKSPACE
				if isinstance(neighbor_left, Fraction):
					root.press_key(readchar.key.LEFT, root)
					if MAPLE_FRAC_DEL:
						root.press_key(readchar.key.BACKSPACE, root)
					return True  # keystroke accepted
				
				# try to remove fraction
				parent1 = root.parentof(self)
				parent2 = root.parentof(parent1)
				if isinstance(parent1, Row) and isinstance(parent2, Fraction) and neighbor_left is None:
					if parent1 is parent2.denominator:
						eprint(ansi.yellow("REMOVING FRACTION"))
						frac_contents = parent2.numerator.items + parent2.denominator.items
						root.replace(parent2, row(*frac_contents))
					else:  # fraction will not get deleted if backspace was pressed inside the numerator
						root.press_key(readchar.key.LEFT, root)
					return True  # keystroke accepted
			
			else:
				eprint(ansi.yellow(f"REMOVE: '{self.text[self.cursor.col - 1]}'"))
				self.text: str = self.text[:self.cursor.col - 1] + self.text[self.cursor.col:]
				self.cursor = self.cursor.left(1)
				assert self.cursor.col >= 0
		
		if key == readchar.key.LEFT:
			if self.cursor.col > 0:
				self.cursor = self.cursor.left(1)
			else:
				root.press_key(readchar.key.UP, root, skip_empty=False)
		
		if key == readchar.key.RIGHT:
			if self.cursor.col < self.width(root, rparent, parent):  # + one space at the end
				self.cursor = self.cursor.right(1)
			else:
				if SKIP_DENOMINATOR:  # maple, mathquill: RIGHT inside numerator causes the cursor to jump right after the fraction
					parent = root.parentof(root.parentof(self))
					if isinstance(parent, Fraction) and root.neighbor_right(self) is None:  # if inside fraction and next to me is nothing (cursor is at the end of numerator)
						self.cursor = None
						root.neighbor_right(parent).cursor = ScreenOffset(0, 0)  # start of the text field
					else:
						root.press_key(readchar.key.DOWN, root, skip_empty=False)
				else:
					root.press_key(readchar.key.DOWN, root, skip_empty=False)
		
		if key == readchar.key.UP:
			bfs_line = root.bfs_children()
			for expr in reversed(bfs_line[:obj_index(bfs_line, self)]):
				if isinstance(expr, Text):  # where we can jump to
					if skip_empty and not expr.text: continue
					eprint("target:", expr.__class__.__name__, ansi.green(f"'{expr}'"))
					self.cursor = None
					# expr.cursor = ScreenOffset(0, 0)  # start of the text field
					expr.cursor = ScreenOffset(0, expr.width(root, rparent, parent))  # end of the text field
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
	
	def __repr__(self):
		cur = ""
		if self.cursor:
			cur = (", " if self.text else "") + f"cursor=ScreenOffset({self.cursor.row}, {self.cursor.col})"
		
		return f'text("{self.text}"{cur})' if self.text else f"text({cur})"



class Row(Expression):
	def __init__(self, items: List[Expression]):
		self.items = items
		self.simplify()
	
	def children(self) -> List[Expression]:
		return self.items
	
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		root = root or self
		
		# reset the paren pairing
		for child in self.children():
			if isinstance(child, Paren):
				child.paired = False
		
		# sync/pair parenthesis
		for child in reversed(self.children()):
			if isinstance(child, LParen):
				child.sync(root=root, rparent=self, parent=parent)
		
		for child in self.children():
			if isinstance(child, RParen) and not child.paired:
				child.sync(root=root, rparent=self, parent=parent, give_up=True)
		
		###############################################################################################
		
		rr = [x.render(root=root, rparent=self, parent=parent) for x in self.items]
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
	
	def simplify(self, root: Row = None, rparent: Row = None, parent: Expression = None):  # todo: remove the abstract method?
		root = root or self
		
		output = []
		
		# flatten rows todo: manage nested rows
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
						a.cursor = ScreenOffset(0, a.width(root=root, rparent=self, parent=parent)).right(b.cursor.col)
					a.text = f"{a.text}{b.text}"
					output.pop(idx + 1)
					break
			else:
				break
		
		# continue the recursion
		for child in output:
			child.simplify(root=root, rparent=self, parent=parent)  # fractions only, of course
		
		# todo: insert space into the text between adjacent fractions
		
		self.items = output
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		root = root or self
		for child in self.children():
			if child.press_key(key, root=root, rparent=self, parent=parent, skip_empty=skip_empty):
				return True  # cursor could be moved multiple times if we wouldn't stop right there
		return False  # not accepted yet... (dead end)
	
	
	
	def __str__(self):
		return "".join([str(x) for x in self.items])
	
	def __repr__(self):
		r = [x for x in [repr(x) for x in self.items] if x != 'text()']
		if len(r) == 1:
			return r[0]
		else:
			return f"row({', '.join(r)})"



class Fraction(Expression):
	def __init__(self, numerator: Row, denominator: Row):
		assert isinstance(numerator, Row)
		assert isinstance(denominator, Row)
		self.numerator = numerator
		self.denominator = denominator
	
	
	def children(self) -> List[Expression]:
		return [self.numerator, self.denominator]
	
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		
		n = self.numerator.render(root=root, rparent=rparent, parent=self)
		d = self.denominator.render(root=root, rparent=rparent, parent=self)
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
		output.append(f"╶{'─' * (w - 2)}╴" if FRAC_SHORTER_ENDS else '─' * w)
		output.extend([str_align(l, w) for l in d.lines])
		
		colors = []
		colors.extend([list_align(c, w) for c in n.colors])
		colors.append([FRAC_COLOR] * w)
		colors.extend([list_align(c, w) for c in d.colors])
		
		return RenderOutput(output, colors, baseline, w, cursor)
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		if self.numerator.press_key(key, root, rparent, self, skip_empty): return True  # keystroke accepted
		if self.denominator.press_key(key, root, rparent, self, skip_empty): return True  # keystroke accepted
		return False  # not accepted yet... (dead end)
	
	
	def __str__(self):
		return f"(({str(self.numerator) or 'None'}) / ({str(self.denominator) or 'None'}))"
	
	def __repr__(self):
		return f"fraction({repr(self.numerator)}, {repr(self.denominator)})"



class Paren(Expression):
	def __init__(self):
		self.paired = False
		self.height = 1
		self.baseline = 0
	
	def children(self) -> List[Expression]:
		return []



# todo: merge LParen and RParen, add [], {}

class LParen(Paren):
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		
		if self.height == 1:
			return RenderOutput(["("], [[PAREN_COLOR if self.paired else XPEREN_COLOR]], self.baseline, width=1, cursor=None)
		else:
			output = flatten([
				"⎛",
				["⎜"] * (self.height - 2),
				"⎝",
			])
			
			return RenderOutput(output, [[PAREN_COLOR if self.paired else XPEREN_COLOR]] * self.height, self.baseline, width=1, cursor=None)
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		return False
	
	
	def sync(self, root: Row = None, rparent: Row = None, parent: Expression = None, give_up: bool = False):
		assert isinstance(root, Row) and isinstance(rparent, Row)
		assert root is not None, "Paren must always be inside a Row."
		
		neighbors = root.all_neighbors_right(self)
		
		self.baseline = 0
		self.height = 1
		
		if not neighbors:
			return
		
		if give_up:
			rr = row(*neighbors).render(root=root, rparent=rparent, parent=parent)
			self.baseline = rr.baseline
			self.height = len(rr.lines)
			return
		
		for expr in neighbors:
			if isinstance(expr, RParen) and not expr.paired:
				expr.height = self.height
				expr.baseline = self.baseline
				expr.paired = True
				self.paired = True
				break
			
			rr = expr.render(root=root, rparent=rparent, parent=parent)
			self.baseline = max(self.baseline, rr.baseline)
			self.height = max(self.height, len(rr.lines) + abs(self.baseline - rr.baseline))
	
	
	def __str__(self):
		return "("
	
	def __repr__(self):
		return "lparen()"



class RParen(Paren):
	def render(self, root: Row = None, rparent: Row = None, parent: Expression = None) -> RenderOutput:
		assert isinstance(root, Row) and isinstance(rparent, Row)
		
		if self.height == 1:
			return RenderOutput([")"], [[PAREN_COLOR if self.paired else XPEREN_COLOR]], self.baseline, width=1, cursor=None)
		else:
			output = flatten([
				"⎞",
				["⎟"] * (self.height - 2),
				"⎠",
			])
			
			return RenderOutput(output, [[PAREN_COLOR if self.paired else XPEREN_COLOR]] * self.height, self.baseline, width=1, cursor=None)
	
	def press_key(self, key: str, root: Row = None, rparent: Row = None, parent: Expression = None, skip_empty: bool = True) -> bool:
		return False
	
	def sync(self, root: Row = None, rparent: Row = None, parent: Expression = None, give_up: bool = False):
		assert isinstance(root, Row) and isinstance(rparent, Row)
		assert root is not None, "Paren must always be inside a Row."
		
		neighbors = root.all_neighbors_left(self)
		
		self.baseline = 0
		self.height = 1
		
		if not neighbors:
			return
		
		if give_up:
			rr = row(*neighbors).render(root=root, rparent=rparent, parent=parent)
			self.baseline = rr.baseline
			self.height = len(rr.lines)
			return
		
		for expr in reversed(neighbors):
			if isinstance(expr, LParen) and not expr.paired:
				expr.height = self.height
				expr.baseline = self.baseline
				expr.paired = True  # should already be paired
				self.paired = True
				break
			
			rr = expr.render(root=root, rparent=rparent, parent=parent)
			self.baseline = max(self.baseline, rr.baseline)
			self.height = max(self.height, len(rr.lines) + abs(self.baseline - rr.baseline))
	
	
	def __str__(self):
		return ")"
	
	def __repr__(self):
		return "rparen()"



def row(*items: Expression) -> Row:
	return Row(list(items))



def text(txt: str = "", cursor: Optional[ScreenOffset] = None) -> Row:
	return row(Text(txt, cursor))



def lparen() -> Row:
	return row(LParen())



def rparen() -> Row:
	return row(RParen())



def fraction(numerator: Row, denominator: Row) -> Row:
	assert isinstance(numerator, Row)
	assert isinstance(denominator, Row)
	return row(
		text(),  # jump target
		Fraction(numerator, denominator),
		text(),  # jump target
	)



def parenthesis(expr: Row) -> Row:
	assert isinstance(expr, Row)
	return row(
		text(),  # jump target
		lparen(),
		expr,
		rparen(),
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
			row(
				text("5555555555555", cursor=ScreenOffset(0, 1)),
				fraction(
					fraction(
						fraction(
							text("a"),
							text("a")
						),
						text("a")
					),
					text("a")
				),
				text("+"),
				parenthesis(
					fraction(
						text("a"),
						fraction(
							text("a"),
							text("a")
						)
					),
				),
				rparen(),
				text("aaa"),
			),
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

# expression = text(cursor=ScreenOffset(0, 0))

while True:
	# expression.sync()
	# expression.simplify()  # redundant
	expression.display()
	
	key = readchar.readkey()
	eprint(f"\nkey pressed: {ansi.blue}0x{key.encode('utf8').hex()}{ansi.reset} ({list(readchar.key.__dict__.keys())[list(readchar.key.__dict__.values()).index(key)] if key in readchar.key.__dict__.values() else key})")
	
	if key == readchar.key.CTRL_C:
		break
	
	expression.press_key(key)
	expression.simplify()

expression.display(cursor=False)
