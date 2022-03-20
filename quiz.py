"""Util to create subclips for quiz from youtube link"""
import shutil
import sys
import json
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Dict, DefaultDict, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from pytube import YouTube
from moviepy.editor import AudioFileClip


WINDOWS_PATH_CONFLICTING_SYMBOLS = '\\/:*?"<>|'


def get_logger(name: str, level) -> logging.Logger:
    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    log_handler.setFormatter(formatter)
    _logger.addHandler(log_handler)
    return _logger


logger = get_logger('quiz-app', logging.DEBUG)


def create_path(*args) -> Path:
    created_path = Path(*args)
    created_path.mkdir(parents=True, exist_ok=True)
    return created_path


@dataclass
class QuizModel:
    track_list: List[Dict[str, str]]
    output_path: str
    reveal_names: bool
    download_cache: DefaultDict[str, Dict[str, str]] = field(
        default_factory=lambda: defaultdict(dict),
    )
    cut_cache: DefaultDict[str, Dict[str, str]] = field(
        default_factory=lambda: defaultdict(dict),
    )
    info: List[Dict[str, str]] = field(
        default_factory=lambda: [],
    )
    cut_deltas: List[int] = field(
        default_factory=lambda: [2, 10, 30],
    )
    originals_path: Path = Path('originals')
    cut_path: Path = Path('cut')

    def __post_init__(self):
        self.output_path = create_path(self.output_path)
        self.originals_path = create_path(
            self.output_path,
            self.originals_path,
        )
        self.cut_path = create_path(self.output_path, self.cut_path)

    def load_cache(self):
        originals_cache_path = Path(
            self.originals_path,
            'cache_info.json',
        )
        cache = self._load_defaultdict(originals_cache_path)
        if cache: self.download_cache = cache  # noqa: E701

        cut_cache_path = Path(
            self.cut_path,
            'cache_info.json',
        )
        cache = self._load_defaultdict(cut_cache_path)
        if cache: self.cut_cache = cache  # noqa: E701

    def reset_cache(self):
        shutil.rmtree(self.cut_path)
        create_path(self.cut_path)
        shutil.rmtree(self.originals_path)
        create_path(self.originals_path)

    @staticmethod
    def _load_defaultdict(path: Path) -> Optional[defaultdict]:
        if path.is_file():
            logger.debug(f'Found cache file in {path}')
            with path.open() as cf:
                return defaultdict(dict, json.load(cf))
        else:
            return None


def adapt_name_to_all_filesystems(name: str):
    for no_no_symbol in WINDOWS_PATH_CONFLICTING_SYMBOLS:
        name = ''.join(name.split(no_no_symbol))
    name = name.replace(' ', '_')
    return name


def adapt_time_to_path(time_str: str):
    for symbol in [':', '.']:
        time_str = time_str.replace(symbol, '_')
    return time_str


def load_track_list(track_list_path: str) -> list:
    logger.info(f'Loading playlist from {track_list_path}')
    with open(track_list_path) as tl_file:
        return json.load(tl_file)


def delete_from_cuts_obj(
    to_delete: defaultdict,
    quiz: Optional[QuizModel] = None,
):
    for track_url, delete_obj in to_delete.items():
        for track_time, path in delete_obj.items():
            logger.info(f'Removing unused cut - {path}')
            shutil.rmtree(path)
            if quiz: quiz.cut_cache[track_url].pop(track_time)  # noqa: E701
        if quiz and not quiz.cut_cache[track_url]:
            quiz.cut_cache.pop(track_url)


def remove_unused_cuts(
    quiz: QuizModel,
    actual_cuts: defaultdict,
    force_delete: defaultdict
):
    to_delete = defaultdict(dict)
    for track_url in quiz.cut_cache:
        for track_time, path in quiz.cut_cache[track_url].items():
            if track_time not in actual_cuts[track_url] or \
               actual_cuts[track_url][track_time] != path:
                to_delete[track_url][track_time] = path
    delete_from_cuts_obj(to_delete, quiz)
    delete_from_cuts_obj(force_delete)


def download(quiz: QuizModel):
    for track in quiz.track_list:
        if track['url'] in quiz.download_cache:
            track_name = quiz.download_cache[track['url']]['name']
            logger.info(f'Found cache for {track_name}')
            continue
        audio_stream = YouTube(
            track['url'],
        ).streams.filter(
            only_audio=True,
        ).last()
        adapted_title = adapt_name_to_all_filesystems(audio_stream.title)
        original_path = Path(quiz.originals_path, f'{adapted_title}.webm')
        logger.info(f'Download {audio_stream.title}')
        audio_stream.download(
            filename=original_path
        )
        quiz.download_cache[track['url']] = {
            'path': str(original_path),
            'path_name': adapted_title,
            'name': audio_stream.title,
        }
        logger.info(f'Download {audio_stream.title} done')


def cut(quiz: QuizModel):
    actual_cuts = defaultdict(dict)
    force_delete = defaultdict(dict)
    for it, track in enumerate(quiz.track_list):
        track_name = quiz.download_cache[track['url']]['name']
        track_path_name = quiz.download_cache[track['url']]['path_name']
        time_for_path = adapt_time_to_path(track['time'])
        folder_name = f'{track_path_name}_{time_for_path}'

        if quiz.reveal_names:
            cut_path = create_path(quiz.cut_path, folder_name)
        else:
            cut_path = create_path(quiz.cut_path, str(it).zfill(2))
        quiz.info.append(
            {
                'name': track_name,
                'path': str(cut_path),
                'time': track['time'],
                'url': track['url'],
            },
        )

        actual_cuts[track['url']][track['time']] = str(cut_path)
        if track['url'] in quiz.cut_cache and \
           track['time'] in quiz.cut_cache[track['url']]:
            if quiz.cut_cache[track['url']][track['time']] == str(cut_path):
                logger.info(f'Found cache for {track_name} {track["time"]}')
                continue
            else:
                # trouble: when we reveal names cut cache overrides and then
                # not not revealed folders will not be deleted
                # dirty, i know, but i decided that now its ok
                force_delete[track['url']][track['time']] = \
                    quiz.cut_cache[track['url']][track['time']]

        logger.info(f'Extracting subclip for {folder_name}')
        min, sec = track['time'].split(':')
        start_sec = int(min) * 60 + float(sec)
        clip = AudioFileClip(quiz.download_cache[track['url']]['path'])
        for delta_sec in quiz.cut_deltas:
            subclip = clip.subclip(start_sec, start_sec + delta_sec)
            subclip.write_audiofile(
                str(Path(cut_path, f'{delta_sec}.wav')),
                codec='pcm_s16le',
                verbose=False,
                logger=None,
            )
        quiz.cut_cache[track['url']][track['time']] = str(cut_path)
        logger.info(f'Extracting subclip for {folder_name} done')
    remove_unused_cuts(quiz, actual_cuts, force_delete)


def save_info(quiz: QuizModel):
    with open(f'{quiz.output_path}/info.json', 'w') as cf:
        json.dump(quiz.info, cf, indent=4, ensure_ascii=False)


def save_cache_info(quiz: QuizModel):
    with open(Path(quiz.originals_path, 'cache_info.json'), 'w') as cf:
        json.dump(quiz.download_cache, cf, indent=4)
    with open(Path(quiz.cut_path, 'cache_info.json'), 'w') as cf:
        json.dump(quiz.cut_cache, cf, indent=4)


def main(track_list_path: str, output: str,
         reset_cache: bool, reveal_names: bool):
    quiz = QuizModel(
        output_path=output,
        reveal_names=reveal_names,
        track_list=load_track_list(track_list_path),
    )
    if not reset_cache:
        quiz.load_cache()
    else:
        quiz.reset_cache()
    download(quiz)
    cut(quiz)
    save_info(quiz)
    save_cache_info(quiz)


if __name__ == "__main__":
    parser = ArgumentParser(description='Make quiz music.')
    parser.add_argument('-tl', '--track_list_path',
                        help='Track list file', type=str,
                        default='track_list.json')
    parser.add_argument('-o', '--output',
                        help="Output folder", type=str,
                        default='output')
    parser.add_argument(
        '-rn', '--reveal_names', action='store_true',
        help='Flag to reveal track names for saving cut folders',
    )
    parser.add_argument(
        '-rc', '--reset_cache', action='store_true',
        help='Flag to not use existing cache until processing',
    )
    args = parser.parse_args()
    main(**vars(args))
