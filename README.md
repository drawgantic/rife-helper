# rife-helper
Python commandline script for automating motion interpolation tasks

## Sub-commands
All sub-commands accept the argument `-d, --dir X` for specifying the path of to the project folder, relative to the working directory. The default project folder is `./frames/`

Many sub-commands also accept the argument `-r, --range 1:2`, which specifies a closed interval of frame indexes.

--------------------------------------------------------------------------------
### `ext [-h] [-d X] [-o 0] name`
### Extract frames from a video
- `name` Video file name
- `-o, --offset 0` Index offset

--------------------------------------------------------------------------------
### `x [-h] [-d X] [-r 1:2] [num]`
### Perform multiplication on frame indexes
- `num` Factor

--------------------------------------------------------------------------------
### `+ [-h] [-d X] [-r 1:2] [num]`
### Perform addition on frame indexes
- `num` Addend

--------------------------------------------------------------------------------
### `rm [-h] [-d X] [-r 1:2] [-w] nums [nums ...]`
### Remove specific frames
- `nums` Index or closed interval of indexes in `low:high` form
- `-w, --whitelist` Remove all except specified

--------------------------------------------------------------------------------
### `mv [-h] [-d X] [-c] nums [nums ...]`
### Rename specific frames
- `nums` Number pairs in `from:to` form
- `-c, --copy` Copy files instead of moving them

--------------------------------------------------------------------------------
### `sort [-h] [-d X] [-r 1:2]`
### Reindex frames in alphabetical order

--------------------------------------------------------------------------------
### `save [-h] [-d X] [-b X] [-z] [-o 0] [nums ...]`
### Save the state of frames to a backup folder
- `nums` Index or closed interval of indexes in `low:high` form
- `-b, --backup X` Backup folder (default: `./backup/`)
- `-z, --lazy` Copy only, do not clean range beforehand
- `-o, --offset 0` Index offset

--------------------------------------------------------------------------------
### `load [-h] [-d X] [-b X] [-z] [-o 0] [nums ...]`
### Load a state of frames from a backup folder
- `nums` Index or closed interval of indexes in `low:high` form
- `-b, --backup X` Backup folder (default: `./backup/`)
- `-z, --lazy` Copy only, do not clean range beforehand
- `-o, --offset 0` Index offset

--------------------------------------------------------------------------------
### `clean [-h] [-d X] [-r 1:2] [-i] [div] [rem]`
### Remove frames with modulo
- `div` Remove if (index % div) != rem
- `rem` Remainder to compare against
- `-i, --invert` Remove if (index % div) == rem

--------------------------------------------------------------------------------
### `prune [-h] [-d X] [-r 1:2] [-t 0] [-n]`
### Remove duplicate neighboring frames
- `-t, --threshold 0` Image distortion threshold
- `-n, --dryrun` Perform a dry run

--------------------------------------------------------------------------------
### `weigh [-h] [-d X] ranges [ranges ...]`
### Suggest indexes based on neighboring distortion
- `ranges` Frame index ranges

--------------------------------------------------------------------------------
### `gen [-h] [-d X] [-r 1:2] [-j 0] [-l [X]] [-c] [-m X] [-e [X]] [-z] [-a 0] [-p] [-s] [-o] [-x 0]`
### Interpolate between existing frames
- `-j, --jobs 0` Max number of concurrent processes
- `-l, --load [X]` Reset frames from backup before starting
- `-c, --clear` Delete all intermediate frames
- `-m, --model X` Flow model
- `-e [X], --ease [X]` Easing parameters. Use ":" for arg separation
  - `{quad, root, sin.[in, out, inout]}` Algorithms (default: quad)
  - `seg` Segmented, separate easings between keyframes
  - `f=0` Flex, 1.0=in-out, 0.0=linear, -1.0=out-in (default: 1.0)
  - `t=0` Tangency, Ease-in to ease-out bias (default: 0.5)
- `-z, --zoh` Use zero-order hold (duplicate frames)
- `-a, --approx 0` Frame approximation threshold
- `-p, --pause` Pause before certain events
- `-s, --single` Generate a single frame
- `-o, --open` Use a half-open interval
- `-x, --num 0` Range multiplier

--------------------------------------------------------------------------------
### `ren [-h] [-d X] [-f 0] [-t 0] [-l] [-s X] [-x 0] [name]`
### Render a video from frames
- `name` Video file name
- `-f, --fps 0` Frames per second
- `-t, --time 0` Time in seconds (supersedes fps)
- `-l, --loop` Leave out the last frame
- `-s, --source X` Reference video
- `-x, --num 0` FPS multiplier

--------------------------------------------------------------------------------
### `run [-r 1:2] [-b X] [-j 0] [-l] [-m X] [-e X] [-x 0] [-p] text [slice]`
### Run a set of commands from a text file
- `text` Text file name
- `slice` Text line range
- `-b, --backup X` Backup folder
- `-j, --jobs 0` Max number of concurrent processes
- `-l, --load` Reset frames on gen calls
- `-m, --model X` Flow model
- `-e, --ease X` Easing parameters
- `-x, --num 0` Math operand
- `-p, --pause` Pause after each command

### batch args:
- `ease [X]` Set the default ease parameters
- `model X` Set the default flow model
- `pause` Pause at a specific point in the batch

Comments can be added to batches with `#`.

The `run` command works by updating each sub-command's dictionary with its own dictionary, but only if no arg was already specified. So if the `run` command and some other command share an arg with the same name, then that arg can have a default value set for it.

The order of precedence from lowest to highest priority is:
- commandline args
- batch args
- sub-command args

Example:`frames.py run -b bar -j4 -x3 -e f=7/8:t=1/3 foo.rife`

`foo.rife`:
```bash
clean # clean leftover frames from any previous runs

ext foo.mp4
prune

x # factor will be set to 3 from the command line arg `-x3`
save # will save to './bar'

ease f=3/4 # default params are now f=3/4:t=1/3

# ranges in 'gen' get multiplied by -x
gen -r 2:12 -e f=2/3 # -r 6:36 -e f=2/3:t=1/3
gen -r 12:2 # wraps back around to the beginning

# wrap-around removes the loop frame, so -l isn't needed
ren foo.mp4
```
