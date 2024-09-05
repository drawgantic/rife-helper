#!/usr/bin/env python3

import os, argparse, subprocess, common as cmn, easing as eas
from datetime import datetime

################################################################################
# Command Functions

def cmd_multiply(args: argparse.Namespace) -> None:
	f = cmn.Frames(args.dir, args.range)
	for x in (f if (a := args.num or 1) < 1 else reversed(f)):
		x.rename(x.idx * a)

def cmd_add(args: argparse.Namespace) -> None:
	f = cmn.Frames(args.dir, args.range)
	for x in (f if (a := args.num or 0) < 0 else reversed(f)):
		x.rename(x.idx + a)

def cmd_sort(args: argparse.Namespace) -> None:
	for i, x in enumerate(cmn.Frames(args.dir, args.range)):
		x.rename(i)

def cmd_clean(args: argparse.Namespace) -> None:
	d, r = args.div, args.rem or 0
	fn = ( (lambda _, x: x.remove()) if not d
		else (lambda i, x: x.remove() if i % d == r else None) if args.invert
		else (lambda i, x: x.remove() if i % d != r else None) )
	for i, x in enumerate(cmn.Frames(args.dir, args.range)):
		fn(i, x)

def cmd_save(args: argparse.Namespace) -> None:
	cmn.Frames(args.dir, args.range).copy_to(args.backup, args.skip)

def cmd_load(args: argparse.Namespace) -> None:
	cmn.Frames(args.backup, args.range).copy_to(args.dir, args.skip)

def cmd_prune(args: argparse.Namespace) -> None:
	frames = cmn.Frames(args.dir, args.range)
	frames.mark_for_pruning(args.threshold or 0.015)
	if args.dryrun:
		return
	if args.preserve:
		frames[-1].key = True
	for x in frames:
		x.prune()

def cmd_generate(args: argparse.Namespace) -> None:
	if args.load:
		backup = args.load if type(args.load) == cmn.Path else args.backup
		cmn.Frames(backup, args.range).copy_to(args.dir)
		if args.pause:
			input(f'\nBackup loaded. Press a key to continue\n')
	frames = cmn.Frames(args.dir, args.range)
	if len(frames) < 2:
		raise ValueError('Directory must contain at least 2 images')

	wrap: float | None = None
	if type(frames.wrap) == int:
		last = frames.wrap - 1
		wrap = frames[last].idx
		frames[last].remove() # should be a duplicate of the first frame
		for x in frames[frames.wrap:]:
			x.rename(x.idx + wrap)
		if args.pause:
			input(f'\nOffset of {wrap} applied. Press a key to continue\n')
		frames = cmn.Frames(args.dir, args.range)

	erp = cmn.Interpolator(args.ease, args.jobs, args.model, args.approx)
	ease = erp.ease
	s_range = f'Range: {args.range}\n' if args.range else ''
	if args.zoh:
		print(f'\n{s_range}Zero-order hold\n')
		for i in range(len(frames) - 1):
			lo, hi = frames[i], frames[i + 1]
			for i in range(int(lo.idx + 1), int(hi.idx)):
				lo.copy(i)
	else:
		print(f'\n{s_range}Model: {erp.model}, Jobs: {erp.jobs}\n{ease.info()}\n')
		if ease.segmented:
			for i in range(len(frames) - 1):
				lo, hi = frames[i], frames[i + 1]
				lo.pct, hi.pct = 0.0, 1.0
				ease.set_idx_range(lo.idx, hi.idx)
				erp.gen_frame(lo, hi) if args.single else erp.gen_frames(lo, hi)
				lo.prune()
		else:
			lo, hi = frames[0], frames[-1]
			lo.pct, hi.pct = 0.0, 1.0
			ease.set_idx_range(lo.idx, hi.idx)

			# reindex keyframes to conform to the overarching easing
			# give them temporary names first to avoid naming collisions
			for x in frames[1:-1]:
				x.pct = ease.to_pct(x.idx)
				f = ease.to_idx(x.pct)
				x.rename(f, temp=True)
				x.key = (abs(f - round(f)) <= erp.approx)
			for x in frames[1:-1]:
				x.rename(x.idx, temp=False)
			if args.pause:
				input('\nReindexed for easing. Press a key to continue\n')

			for i in range(len(frames) - 1):
				lo, hi = frames[i], frames[i + 1]
				erp.gen_frame(lo, hi) if args.single else erp.gen_frames(lo, hi)
				lo.prune()

	if wrap != None and frames.range and (hi := frames.range[1]):
		if args.pause:
			input('\nPress a key to begin offset removal\n')
		for x in cmn.Frames(args.dir, args.range)[-(int(hi) + 1):]:
			x.rename(max(0, x.idx - wrap))

def cmd_extract(args: argparse.Namespace) -> None:
	vid = args.name
	vname, _ = os.path.splitext(vid)
	probe = cmn.ffprobe(vid)
	# extract audio if it exists
	if ainfo := next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None):
		subprocess.call([ 'ffmpeg', '-i', vid, '-vn', '-acodec', 'copy', '-y',
			f'{vname}.{ainfo["codec_name"]}' ])
	# extract frames
	if not os.path.exists(args.dir):
		os.mkdir(args.dir, 0o755)
	subprocess.call([ 'ffmpeg', '-i', vid, '-start_number', '0',
		args.dir + f'%05d.000{cmn.Frame.img}' ])
	if args.loop:
		frames = cmn.Frames(args.dir)
		frames[0].copy(frames[-1].idx + 1)

def cmd_render(args: argparse.Namespace) -> None:
	frames = cmn.Frames(args.dir)
	fps = (len(frames) / args.time) if args.time else args.fps
	ainfo = None
	if os.path.isfile(args.name):
		probe = cmn.ffprobe(args.name)
		vinfo = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
		ainfo = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
		if not vinfo:
			exit('file exists but is not a video')
		fps = fps or (len(frames) / float(vinfo['duration']))
	fps = fps or 10

	if args.loop: # leave out last frame, assuming it's a duplicate of first frame
		frames[-1].rename(frames[-1].idx, temp=True)
	# render video
	name, ext = os.path.splitext(args.name)
	dt_string = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
	video = f'{name}_{round(fps)}fps_{dt_string}{ext or '.mp4'}'
	audio = f'{name}.{ainfo["codec_name"]}' if ainfo else None
	cmn.render(args.dir, fps, video, audio)
	print(f'\nWritten to {video}\n')
	if args.loop:
		frames[-1].rename(frames[-1].idx, temp=False)

def cmd_rm(args: argparse.Namespace) -> None:
	for a in [s.split(':') for s in args.nums]:
		if len(a) >= 2:
			for x in cmn.Frames(args.dir, (float(a[0]), float(a[1]))):
				x.remove()
		elif len(a) >= 1:
			cmn.Frame(float(a[0]), args.dir).remove()

def cmd_mv(args: argparse.Namespace) -> None:
	do = cmn.Frame.copy if args.copy else cmn.Frame.rename
	for arg in args.nums:
		do(cmn.Frame(arg[0], args.dir), arg[1])

def cmd_run(args: argparse.Namespace) -> None:
	# text commands are just like normal commands, minus the call to this file
	with open(args.text, 'r') as f:
		lines = f.read().splitlines()
		for line in lines[args.slice or slice(None)]:
			c = line.find('#')
			if len(words := line[:c if c >= 0 else None].strip().split(' ')) <= 0:
				continue
			if words[0] == 'ease':
				args.ease = args.ease or {}
				if len(words) == 2:
					args.ease.update(eas.Dict(words[1]))
			elif words[0] == 'model' and len(words) == 2:
				args.model = words[1]
			elif words[0] == 'pause':
				input(f'Press a key to continue')
			else:
				sub = parser.parse_args(words)
				if sub.func == cmd_generate:
					sub.backup = args.backup
					if args.ease != None:
						sub.ease = sub.ease or {}
						sub.ease.update({ k:v for k,v in args.ease.items()
							if k not in sub.ease })
					if (r := sub.range) and (x := args.num):
						sub.range = tuple(l * x if l != None else None for l in r)
				elif sub.func == cmd_render and sub.fps and args.num:
					sub.fps *= args.num
				kw = vars(sub)
				kw.update({ k:v for k,v in vars(args).items()
					if k in kw and kw[k] == None })
				if args.pause:
					input(f'Next: `{line}` Press a key to continue')
				sub.func(sub)

################################################################################
# Argparse Setup

def Pair(s: str) -> tuple[float, float]:
	t = tuple(map(float, s.split(':')))
	if len(t) != 2:
		raise ValueError('Pair must be exactly 2 values')
	return t

def Range(s: str) -> tuple[float|None, float|None]:
	t = [float(x) if x else None for x in s.split(':')]
	if len(t) != 2:
		raise ValueError('Range cannot exceed 2 values')
	return (t[0], t[1])

def Slice(s: str) -> slice:
	return slice(*(int(x) if x else None for x in s.split(':')))

def opt(p: argparse.ArgumentParser, s: str, l: str, h: str, **kwargs) -> None:
	p.add_argument(s, l, help=h, **kwargs)

def subcommand(name, fn, hlp, rnge=False, **kwargs) -> argparse.ArgumentParser:
	cmd = subparsers.add_parser(name, help=hlp, description=hlp, **kwargs)
	cmd.set_defaults(func=fn)
	opt(cmd, '-d', '--dir', 'Project folder', metavar='X', type=cmn.Path)
	if rnge:
		opt(cmd, '-r', '--range', 'Frame index range (closed interval)',
			metavar='1:2', type=Range)
	return cmd

parser = argparse.ArgumentParser(description='Motion interpolation helper')
subparsers = parser.add_subparsers(required=True)

cmd = subcommand('ext', cmd_extract, 'Extract frames from a video')
cmd.add_argument('name', help='Video file name')
opt(cmd, '-l', '--loop', 'End with duplicate of first frame', action='store_true')

cmd = subcommand('x', cmd_multiply, 'Perform multiplication on frame indexes', True)
cmd.add_argument('num', help='Factor', type=float, nargs='?')

cmd = subcommand('+', cmd_add, 'Perform addition on frame indexes', True)
cmd.add_argument('num', help='Addend', type=float, nargs='?')

cmd = subcommand('rm', cmd_rm, 'Remove specific frames')
cmd.add_argument('nums', help='Index or range of indexes in low:high form', nargs='+')

cmd = subcommand('mv', cmd_mv, 'Rename specific frames')
cmd.add_argument('nums', help='Number pairs in `from:to` form', nargs='+', type=Pair)
opt(cmd, '-c', '--copy', 'Copy files instead of moving them', action='store_true')

cmd = subcommand('sort', cmd_sort, 'Reindex frames in alphabetical order', True)

cmd = subcommand('save', cmd_save, 'Save the state of frames to a backup folder', True)
cmd.add_argument('backup', help='Backup folder', type=cmn.Path, nargs='?')
opt(cmd, '-s', '--skip', 'Skip the removal step and copy only', action='store_true')

cmd = subcommand('load', cmd_load, 'Load a state of frames from a backup folder', True)
cmd.add_argument('backup', help='Backup folder', type=cmn.Path, nargs='?')
opt(cmd, '-s', '--skip', 'Skip the removal step and copy only', action='store_true')

cmd = subcommand('clean', cmd_clean, 'Remove frames with modulo', True)
cmd.add_argument('div', help='Remove if (index %% div) != rem', type=int, nargs='?')
cmd.add_argument('rem', help='Remainder to compare against', type=int, nargs='?')
opt(cmd, '-i', '--invert', 'Remove if (index %% div) == rem', action='store_true')

cmd = subcommand('prune', cmd_prune, 'Remove duplicate neighboring frames', True)
opt(cmd, '-t', '--threshold', 'Image distortion threshold', metavar='0', type=float)
opt(cmd, '-n', '--dryrun', 'Perform a dry run', action='store_true')
opt(cmd, '-p', '--preserve', 'Preserve the last frame', action='store_true')

cmd = subcommand('gen', cmd_generate, 'Interpolate between existing frames', True,
	formatter_class=argparse.RawTextHelpFormatter)
opt(cmd, '-j', '--jobs', 'Max number of concurrent processes', metavar='0', type=int)
opt(cmd, '-l', '--load', 'Reset frames from backup before starting', type=cmn.Path,
	metavar='X', nargs='?', const=True)
opt(cmd, '-m', '--model', 'Flow model', metavar='X')
opt(cmd, '-e', '--ease', 'Easing parameters. Use ":" for arg separation\n'
	'{quad, root, sin.[in, out, inout]}  Algorithms (default: quad)\n'
	'seg  Segmented, separate easings between keyframes\n'
	'f=0  Flex, 1.0=in-out, 0.0=linear, -1.0=out-in (default: 1.0)\n'
	't=0  Tangency, Ease-in to ease-out bias (default: 0.5)',
	metavar='X', nargs='?', type=eas.Dict, const={})
opt(cmd, '-z', '--zoh', 'Use zero-order hold interpolation', action='store_true')
opt(cmd, '-a', '--approx', 'Frame approximation threshold', metavar='0', type=float)
opt(cmd, '-p', '--pause', 'Pause before certain events', action='store_const', const=True)
opt(cmd, '-s', '--single', 'Generate a single frame', action='store_true')

cmd = subcommand('ren', cmd_render, 'Render a video from frames')
cmd.add_argument('name', help='Video file name', nargs='?')
opt(cmd, '-f', '--fps', 'Frames per second', metavar='0', type=float)
opt(cmd, '-t', '--time', 'Time in seconds (supersedes fps)', metavar='0', type=float)
opt(cmd, '-l', '--loop', 'Leave out the last frame', action='store_true')

cmd = subcommand('run', cmd_run, 'Run a set of commands from a text file', True)
cmd.add_argument('text', help='Text file name')
cmd.add_argument('slice', help='Text line range', nargs='?', type=Slice)
opt(cmd, '-b', '--backup', 'Backup folder', metavar='X', type=cmn.Path)
opt(cmd, '-j', '--jobs', 'Max number of concurrent processes', metavar='0', type=int)
opt(cmd, '-l', '--load', 'Reset frames on gen calls', action='store_true')
opt(cmd, '-m', '--model', 'Flow model', metavar='X')
opt(cmd, '-e', '--ease', 'Easing parameters', metavar='X', type=eas.Dict)
opt(cmd, '-x', '--num', 'Math operand', metavar='0', type=float)
opt(cmd, '-p', '--pause', 'Pause after each command', action='store_true')
if __name__ == '__main__':
	args = parser.parse_args()
	# for cmd_run to work, defaults need to be set outside of argparse
	kw = vars(args)
	args.dir = kw.get('dir', None) or cmn.Path('frames/')
	args.backup = kw.get('backup', None) or cmn.Path('backup/')
	args.func(args)