from math import cos, sin, acos, asin, sqrt, floor, pi
from typing import Any, Self, Callable

acc = float.fromhex('0x1p48') # for rounding off small inaccuracies

def Float(s: str) -> float:
	x = s.split('/')
	return float(x[0]) / float(x[1]) if len(x) == 2 else float(s)

def Dict(s: str|None) -> dict[str, Any]:
	kwargs: dict[str, Any] = {}
	if not s: return kwargs
	for arg in [x.split('=') for x in s.split(':')]:
		if len(arg) == 1:
			if arg[0] == 'seg':
				kwargs['segmented'] = True
			elif arg[0] in Easing.funcs:
				kwargs['func'] = Easing.funcs[arg[0]]
		elif len(arg) == 2:
			if arg[0] == 'f':
				kwargs['flex'] = Float(arg[1])
			elif arg[0] == 't':
				kwargs['tan'] = Float(arg[1])
	return kwargs

class Easing:
	def __init__(self: Self, **kwargs) -> None:
		flex = float(kwargs.get('flex', 1))
		tan = float(kwargs.get('tan', 0.5))
		self.func = Easing.linear if flex == 0 else kwargs.get('func', Easing.quad)

		self.segmented = bool(kwargs.get('segmented', False))
		'''False = one overarching easing, True = easings between all keyframes'''
		self.flex = min(max(-1, flex), 1)
		'''-1 = out-in, 0 = linear, 1 = in-out'''
		self.tan = min(max(0, tan), 1)
		'''Point of tangency, or ease-in to ease-out ratio'''
		if self.tan > 0:
			self.amp1 = floor((self.flex / self.tan) * acc + 0.5) / acc
			'''Amplitude of first parabola'''
		if self.tan < 1:
			self.amp2 = floor((self.flex / (self.tan - 1)) * acc + 0.5) / acc
			'''Amplitude of second parabola'''

	def set_idx_range(self: Self, lo: float, hi: float) -> None:
		self.slope = hi - lo
		self.intercept = lo

	def idx_from_pct(self: Self, pct: float) -> float:
		return self.slope * self.func(self, pct) + self.intercept

	def pct_from_idx(self: Self, idx: float) -> float:
		inverse = Easing.invs[self.func.__name__]
		idx = self.pct_from_lin(idx)
		if idx <= 0:
			return 0
		if idx >= 1:
			return 1
		return inverse(self, idx)

	def pct_from_lin(self: Self, idx: float) -> float:
		'''Get the percentage from a linear index'''
		return (idx - self.intercept) / self.slope

	def info(self: Self) -> str:
		name = self.func.__name__
		s = 'Easing: ' + name
		if name != 'linear':
			s += (', segmented' if self.segmented else '')
			if not name.startswith('sine'):
				s += f', flex: {self.flex:.6g}, tangency: {self.tan:.6g}'
		return s

	# These easing functions use the inverse of what the function would normally be.
	# We're given the frame's percentage of completed motion, so we need to solve
	# for the time and index associated with that percentage.

	def quad(self: Self, x: float) -> float:
		a = self.amp1 if x < self.tan else self.amp2
		b = self.flex + 1
		x -= self.tan
		return (-b + sqrt(b*b + 4*a*x)) / (2*a) + self.tan

	def root(self: Self, x: float) -> float:
		a = self.amp1 if x < self.tan else self.amp2
		b = self.flex + 1
		x -= self.tan
		return a*x*x + b*x + self.tan

	def sine_in(self: Self, x: float) -> float:
		return 2 * acos(1 - x) / pi

	def inv_sine_in(self: Self, x: float) -> float:
		return 1 - cos((x * pi) / 2)

	def sine_out(self: Self, x: float) -> float:
		return 2 * asin(x) / pi

	def inv_sine_out(self: Self, x: float) -> float:
		return sin((x * pi) / 2)

	def sine_in_out(self: Self, x: float) -> float:
		return acos(1 - (2 * x)) / pi

	def inv_sine_in_out(self: Self, x: float) -> float:
		return -(cos(pi * x) - 1) / 2

	def linear(self: Self, x: float) -> float:
		return x

	funcs: dict[str, Callable[[Self, float], float]] = {
		'quad': quad,
		'inv.quad': root,
		'root': root,
		'inv.root': quad,
		'sin': sine_in_out,
		'inv.sin': inv_sine_in_out,
		'sin.in': sine_in,
		'inv.sin.in': inv_sine_in,
		'sin.out': sine_out,
		'inv.sin.out': inv_sine_out,
		'sin.inout': sine_in_out,
		'inv.sin.inout': inv_sine_in_out,
		'lin': linear,
	}

	invs: dict[str, Callable[[Self, float], float]] = {
		'quad': root,
		'root': quad,
		'sine_in': inv_sine_in,
		'inv_sine_in': sine_in,
		'sine_out': inv_sine_out,
		'inv_sine_out': sine_out,
		'sine_in_out': inv_sine_in_out,
		'inv_sine_in_out': sine_in_out,
		'linear': linear,
	}
