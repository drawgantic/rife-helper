import os, json, subprocess, shutil, easing as eas
from typing import Any, Self, Type
from threading import Thread, active_count
from wand.image import Image
from sys import argv

cwd = os.path.dirname(os.path.realpath(argv[0]))

def float_or(s: str, fallback: float) -> float:
	try:
		return float(s)
	except:
		return fallback

class Path(str):
	def __new__(cls: Type[Self], s: str) -> Self:
		return super().__new__(cls, s + ('/' if s[-1] != '/' else ''))

class Ext(str):
	def __new__(cls: Type[Self], s: str) -> Self:
		return super().__new__(cls, ('.' if s[0] != '.' else '') + s)

class Frame:
	img = Ext('.png')
	fmt = '%09.3f' + img
	def __init__(self: Self, f: float, head: Path, **kwargs) -> None:
		self.idx = f
		self.head = head
		self.pct = float(kwargs.get('pct', 1.0))
		self.key = bool(kwargs.get('key', True))
		self.tail = str(kwargs.get('tail', Frame.fmt % f))

	def __lt__(self: Self, other: Self) -> bool:
		return (self.idx < other.idx)

	def rename(self: Self, f: float, temp = False) -> None:
		self.idx = f
		s = (Frame.fmt % f) + ('.' if temp else '')
		try:
			os.rename(self.head + self.tail, self.head + s)
		except Exception as e:
			print('rename: ' + str(e))
		self.tail = s

	def copy(self: Self, arg: Path | float) -> None:
		new = arg + self.tail if type(arg) == Path else self.head + (Frame.fmt % arg)
		try:
			shutil.copyfile(self.head + self.tail, new)
		except Exception as e:
			print('copy: ' + str(e))

	def remove(self: Self) -> None:
		try:
			os.remove(self.head + self.tail)
		except Exception as e:
			print('remove: ' + str(e))

	def prune(self: Self) -> None:
		if not self.key:
			self.remove()

Range = tuple[float|None, float|None]

class Frames(list[Frame]):
	def __init__(self: Self, head: Path, r: Range | None = None) -> None:
		frames: list[Frame] = []
		self.range = r
		self.wrap = None
		if not os.path.exists(head):
			return super().__init__(frames)
		for i, tail in enumerate(sorted(os.listdir(head))):
			name, ext = os.path.splitext(tail)
			if ext == Frame.img:
				frames.append(Frame(float_or(name, i), head, tail=tail))
		if len(frames) < 2:
			return super().__init__(frames)
		if r:
			r = (r[0] or frames[0].idx, r[1] or frames[-1].idx)
			if r[0] >= r[1]:
				end = [x for x in frames if x.idx >= r[0]]
				beg = [x for x in frames if x.idx <= r[1]]
				self.wrap = len(end)
				frames = end + beg
			else:
				frames = [x for x in frames if r[0] <= x.idx and x.idx <= r[1]]
		super().__init__(frames)

	def copy_to(self: Self, to: Path, lazy: bool = False) -> None:
		if not os.path.exists(to):
			os.mkdir(to, 0o755)
		elif not lazy:
			for x in Frames(to, self.range):
				x.remove()
		for x in self:
			x.copy(to)

	def mark_for_pruning(self: Self, threshold: float) -> int:
		min_gap = 5000 # just an arbitrary large number to start with
		k = 0 # current keyframe index
		key = Image(filename = self[k].head + self[k].tail)
		for i in range(1, len(self)):
			img = Image(filename = self[i].head + self[i].tail)
			diff = key.get_image_distortion(img, metric = 'root_mean_square')
			s = f'{int(self[k].idx)},%s{int(self[i].idx)}: {diff}\033[0m'
			if diff >= threshold:
				color = '\033[0m'
				if (gap := i - k) < min_gap:
					min_gap = gap
				key.close()
				key = img
				k = i
			else:
				color = '\033[92m'
				self[i].key = False
				img.close()
			print(s % color)
		key.close()
		return min_gap

class Interpolator:
	def __init__(self: Self,
		ease: dict[str, Any]|None, jobs: int|None, model: str|None, approx: float|None
	) -> None:
		self.ease = eas.Easing(**(ease if ease is not None else {'flex': 0}))
		self.jobs = jobs or 1
		self.model = model or 'rife-v4.18'
		if not os.path.exists(f'{cwd}/rife/models/{self.model}'):
			raise ValueError('Flow model does not exist')
		self.approx = approx or 0.125
		self.margin = 1 + self.approx * 2

	def gen_frame(self: Self, lo: Frame, hi: Frame) -> Frame:
		pct = (lo.pct + hi.pct) / 2
		f = self.ease.to_idx(pct)
		mid = Frame(f, lo.head, pct=pct)
		mid.key = (abs(f - round(f)) <= self.approx)
		def fmt(num):
			return f'%.{ 6 - len(str(int(num))) }f' % num
		print(f'{fmt(lo.idx)}\033[92m {fmt(mid.idx)}\033[0m {fmt(hi.idx)}')
		subprocess.run([ f'{cwd}/rife/build/rife-ncnn-vulkan',
			'-m', f'{cwd}/rife/models/{self.model}',
			'-0', lo.head + lo.tail,
			'-1', hi.head + hi.tail,
			'-o', mid.head + mid.tail,
		])
		return mid

	def gen_frames(self: Self, lo: Frame, hi: Frame) -> None:
		dif = abs(hi.idx - lo.idx)
		if ( int(lo.idx) == int(hi.idx) # ex: 2 and 2.9 (no new keyframes)
			or (lo.key and hi.key and dif <= self.margin) # ex: 1.9 and 3.1
			or (lo.key != hi.key and dif < 1) # ex: 1.9 (skip) 2.5 (3) 3.5
		): return
		mid = self.gen_frame(lo, hi)
		t = None
		if active_count() < self.jobs:
			t = Thread(target=Interpolator.gen_frames, args=(self, lo, mid))
			t.start()
		else:
			self.gen_frames(lo, mid)
		self.gen_frames(mid, hi)
		if t:
			t.join()
		mid.prune()

def ffprobe(file: str) -> dict[str, Any]:
	probe = subprocess.run([ 'ffprobe', '-print_format', 'json',
		'-show_streams', '-show_format', file ], capture_output=True)
	if probe.returncode != 0:
		raise RuntimeError(f'An error occurred while probing {file}')
	return json.loads(probe.stdout)

def render(head: Path, fps: float, video: str, audio: str | None = None) -> None:
	cmd = [ 'ffmpeg', '-framerate', str(fps), '-pattern_type', 'glob',
		'-i', f'{head}*{Frame.img}' ]
	if audio: cmd += ['-i', audio]

	# https://academysoftwarefoundation.github.io/EncodingGuidelines/Quickstart.html
	cmd += [
		'-pix_fmt', 'yuv420p',
		'-c:v', 'libx264',
		'-preset', 'slower',
		# this filter causes problems for some videos, and fixes problems for others
		# '-vf', 'scale=in_color_matrix=bt709:out_color_matrix=bt709',
		# '-color_range', 'tv',
		# '-colorspace', 'bt709',
		# '-color_primaries', 'bt709',
		# '-color_trc', 'iec61966-2-1',
		'-movflags', 'faststart',
		video,
	]
	subprocess.run(cmd)
