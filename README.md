# rife-helper
Python commandline script for automating motion interpolation tasks

## Sub-commands
All sub-commands accept the argument `-d X, --dir X` for specifying the path of to the project folder, relative to the working directory. The default project folder is `./frames/`

Many sub-commands also accept the argument `-r 1:2, --range 1:2`, which specifies a closed interval of frame indexes.

--------------------------------------------------------------------------------
### `ext [-l] name`
### Extract frames from a video
- `name` Video file name
- `-l, --loop` End with duplicate of first frame

--------------------------------------------------------------------------------
### `x [-r 1:2] [num]`
### Perform multiplication on frame indexes
- `num` Factor

--------------------------------------------------------------------------------
### `+ [-r 1:2] [num]`
### Perform addition on frame indexes
- `num` Addend

--------------------------------------------------------------------------------
### `rm nums [nums ...]`
### Remove specific frames
- `nums` Index or closed interval of indexes in `low:high` form

--------------------------------------------------------------------------------
### `mv [-c] nums [nums ...]`
### Rename specific frames
- `nums` Number pairs in `from:to` form
- `-c, --copy` Copy files instead of moving them

--------------------------------------------------------------------------------
### `sort [-r 1:2]`
### Reindex frames in alphabetical order

--------------------------------------------------------------------------------
### `save [-r 1:2] [-s] [backup]`
### Save the state of frames to a backup folder
- `backup` Backup folder (default: `./backup/`)
- `-s, --skip` Skip the removal step and copy only

--------------------------------------------------------------------------------
### `load [-r 1:2] [-s] [backup]`
### Load a state of frames from a backup folder
- `backup` Backup folder (default: `./backup/`)
- `-s, --skip` Skip the removal step and copy only

--------------------------------------------------------------------------------
### `clean [-r 1:2] [-i] [div] [rem]`
### Remove frames with modulo
- `div` Remove if (index % div) != rem
- `rem` Remainder to compare against
- `-i, --invert` Remove if (index % div) == rem

--------------------------------------------------------------------------------
### `prune [-r 1:2] [-t 0] [-n] [-p]`
### Remove duplicate neighboring frames
- `-t 0, --threshold 0` Image distortion threshold
- `-n, --dryrun` Perform a dry run
- `-p, --preserve` Preserve the last frame

--------------------------------------------------------------------------------
### `gen [-r 1:2] [-j 0] [-l [X]] [-m X] [-e [X]] [-z] [-a 0] [-p] [-s]`
### Interpolate between existing frames
- `-j 0, --jobs 0` Max number of concurrent processes
- `-l [X], --load [X]` Reset frames from backup before starting
- `-m X, --model X` Flow model
- `-e [X], --ease [X]` Easing parameters. Use ":" for arg separation
  - `{quad, root, sin.[in, out, inout]}` Algorithms (default: quad)
  - `seg` Segmented, separate easings between keyframes
  - `f=0` Flex, 1.0=in-out, 0.0=linear, -1.0=out-in (default: 1.0)
  - `t=0` Tangency, Ease-in to ease-out bias (default: 0.5)
- `-z, --zoh` Use zero-order hold interpolation
- `-a 0, --approx 0` Frame approximation threshold
- `-p, --pause` Pause before certain events
- `-s, --single` Generate a single frame

--------------------------------------------------------------------------------
### `ren [-f 0] [-t 0] [-l] [name]`
### Render a video from frames
- `name` Video file name
- `-f 0, --fps 0` Frames per second
- `-t 0, --time 0` Time in seconds (supersedes fps)
- `-l, --loop` Leave out the last frame

--------------------------------------------------------------------------------
### `run [-r 1:2] [-b X] [-j 0] [-l] [-m X] [-e X] [-x 0] [-p] text [slice]`
### Run a set of commands from a text file
- `text` Text file name
- `slice` Text line range
- `-b X, --backup X` Backup folder
- `-j 0, --jobs 0` Max number of concurrent processes
- `-l, --load` Reset frames on gen calls
- `-m X, --model X` Flow model
- `-e X, --ease X` Easing parameters
- `-x 0, --num 0` Math operand
- `-p, --pause` Pause after each command

### run-script args:
- `ease [X]` Set the default ease parameters
- `model X` Set the default flow model
- `pause` Pause at a specific point in the run-script

Comments can be added to run-scripts with `#'.

The `run` command works by updating each sub-command's dictionary with its own dictionary, but only if no arg was already specified. So if the `run` command and some other command share an arg with the same name, then that arg can have a default value set for it.

The order of precedence from lowest to highest priority is:
- commandline args
- run-script args
- sub-command args

Example:`frames.py run -b bar -j4 -x3 -e f=7/8:t=1/3 foo.rife`

`foo.rife`:
```bash
clean # clean leftover frames from any previous runs

ext -l foo.mp4
prune

x # factor will be set to 3
save # will save to './bar'

ease f=3/4 # default params are now f=3/4:t=1/3

# ranges in 'gen' get multiplied by -x
gen -r 2:12 -e f=2/3 # -r 6:36 -e f=2/3:t=1/3
gen -r 12:2 # wraps back around to the beginning

# wrap-around removes the loop frame, so -l isn't needed
ren foo.mp4
```
