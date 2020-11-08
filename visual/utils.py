import contextlib
import sys
from io import StringIO



def run(code: str) -> str:
	@contextlib.contextmanager
	def wrapper(stdout=None):
		old = sys.stdout
		if stdout is None:
			stdout = StringIO()
		sys.stdout = stdout
		yield stdout
		sys.stdout = old
	
	
	with wrapper() as s:
		try:
			compiled = compile(code, "<string>", "single", dont_inherit=True)
			eval(compiled, {}, {})
		except Exception as e:
			print(str(e))
	
	return str(s.getvalue())
