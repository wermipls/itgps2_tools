from collections import namedtuple
import sys, subprocess, argparse, os, logging
from logging import debug, info, warning, error
import simfile
from simfile.notes import Note, NoteType, NoteData
from PIL import Image

SongFiles = namedtuple('SongFiles', ['simfile', 'music', 'background', 'banner'])

default_out_files = SongFiles(
    'steps.sm',
    'audio.ogg',
    'bg.png',
    'bn.png',
)

def listdir_abs(dir='.') -> list[str]:
    list = []

    for i in os.listdir(dir):
        abspath = os.path.join(dir, i)
        list.append(abspath)

    return list

def file_exists_info(path: str):
    if os.path.exists(path):
        info(f'Output file "{path}" already exists')

def scale_crop_image(in_path: str, out_path: str, size: tuple[int, int]):
    im = Image.open(in_path)
    ratio = im.width / im.height
    target_ratio = size[0] / size[1]

    box = None

    if ratio > target_ratio:
        width = im.height * target_ratio
        height = im.height
        x = (im.width - width) / 2 
        y = 0
        box = (x, y, x + width, y + height)
    else:
        width = im.width 
        height = im.width / target_ratio
        x = 0
        y = (im.height - height) / 2 
        box = (x, y, x + width, y + height)
    
    im = im.resize(size, Image.Resampling.BILINEAR, box)
    im.save(out_path)

def convert_banner(in_path: str, out_path: str):
    size = (256, 80)
    scale_crop_image(in_path, out_path, size)

def convert_background(in_path: str, out_path: str):
    size = (320, 240)
    scale_crop_image(in_path, out_path, size)

def convert_audio(in_path: str, out_path: str) -> int:
    # TODO: this really should be replaced with a proper procedure
    # that takes how stepmania handles mp3 files into account...
    # current "solution" results in the files being 40-50ms offsync

    cmd = [
        'ffmpeg', 
        '-i', in_path,
        '-map_metadata', '-1',
        '-map', '0:a', 
        '-ar', '48000',
        '-c:a', 'libvorbis',
        '-qscale:a', '4',
        '-y', out_path,
        ]
    
    file = os.path.basename(in_path)
    info(f'Converting audio file "{file}"...')
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode

def roll_to_hold(note: Note) -> Note:
    if note.note_type == NoteType.ROLL_HEAD:
        return Note(note.beat, note.column, NoteType.HOLD_HEAD, note.player, note.keysound_index)
    else:
        return note

def convert_simfile(in_path: str, out_path: str, files: SongFiles, rolls_to_holds=True) -> int:
    sim = simfile.open(in_path)

    if type(sim) != simfile.sm.SMSimfile:
        error('.ssc simfiles are currently unsupported!')
        return 1

    if rolls_to_holds:
        for chart in sim.charts:
            note_data = NoteData(chart)
            cols = note_data.columns
            adjusted_notes = (roll_to_hold(note) for note in note_data)
            adjusted_note_data = NoteData.from_notes(adjusted_notes, cols)
            chart.notes = str(adjusted_note_data)

    sim.background = files.background
    sim.banner = files.banner
    sim.music = files.music

    with open(out_path, 'w', encoding='utf-8') as outfile:
        sim.serialize(outfile)

    return 0

def find_simfile(dir: str) -> str:
    ssc = None

    for i in listdir_abs(dir):
        if i.endswith('.sm'):
            return i
        elif i.endswith('.ssc'):
            ssc = i

    # ssc should only be used as fallback if no proper .sm is found
    return ssc

def find_song_files(dir: str) -> SongFiles:
    sim_path = find_simfile(dir)

    sim = simfile.open(sim_path)

    return SongFiles(
        os.path.basename(sim_path), sim.music, sim.background, sim.banner
    )

def is_valid_songdir(dir: str) -> bool:
    try:
        s = find_simfile(dir)
        simfile.open(s)
        return True
    except:
        return False

def get_songdir_list(basedir: str) -> list[str]:
    dirlist = []

    for i in listdir_abs(basedir):
        if os.path.isdir(i) and is_valid_songdir(i):
            dirlist.append(i)

    return dirlist

def convert_song(in_dir: str, out_dir: str, force_overwrite: bool) -> int:
    if os.path.isdir(out_dir):
        info(f'song output directory "{out_dir}" already exists')
    else:
        os.makedirs(out_dir)

    files = find_song_files(in_dir)

    # not sure how to do this better >_<

    files_abs = SongFiles(
        os.path.join(in_dir, files[0]),
        os.path.join(in_dir, files[1]),
        os.path.join(in_dir, files[2]),
        os.path.join(in_dir, files[3]),
    )

    files_out_abs = SongFiles(
        os.path.join(out_dir, default_out_files[0]),
        os.path.join(out_dir, default_out_files[1]),
        os.path.join(out_dir, default_out_files[2]),
        os.path.join(out_dir, default_out_files[3]),
    )

    file_exists_info(files_out_abs.simfile)
    convert_simfile(files_abs.simfile, files_out_abs.simfile, default_out_files)

    if not force_overwrite and os.path.exists(files_out_abs.music):
        warning(f'Output file "{files_out_abs.music}" already exists, skipping')
    else:
        err = convert_audio(files_abs.music, files_out_abs.music)
        if err:
            error(f'Failed to convert audio file "{files_abs.music}"')
            return 1

    try:
        file_exists_info(files_out_abs.banner)
        convert_banner(files_abs.banner, files_out_abs.banner)
    except Exception as e:
        error(f'Failed to convert banner image: {str(e)}')

    try:
        file_exists_info(files_out_abs.background)
        convert_background(files_abs.background, files_out_abs.background)
    except Exception as e:
        error(f'Failed to convert banner image: {str(e)}')

    return 0



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input',
                        help='song pack source directory')
    parser.add_argument('output',
                        help='song pack destination directory')
    parser.add_argument('-v', action='store_true',
                        help='enable verbose console output')
    parser.add_argument('-f', action='store_true',
                        help='force overwrite of existing audio files')
    
    args = parser.parse_args()

    log_level = logging.INFO if args.v else logging.WARNING
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    if not os.path.isdir(args.input):
        error('Input path is not a valid directory')
        return 1

    if not os.path.isdir(args.output):
        info('Output directory does not exist, attempting to create it')
        os.makedirs(args.output)

    list = get_songdir_list(args.input)

    for songdir in list:
        reldir = os.path.basename(songdir)
        outdir = os.path.join(args.output, reldir)
        print(f'Converting song {reldir}...')
        convert_song(songdir, outdir, args.f)

    return 0



if __name__ == '__main__':
    sys.exit(main())
