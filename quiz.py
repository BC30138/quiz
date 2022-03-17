
import sys
import json
import logging
from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path
from typing import List, Dict, DefaultDict
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


@dataclass
class QuizModel:
    track_list: List[Dict[str, str]]
    output_path: str
    download_cache: DefaultDict[str, Dict[str, str]] = field(
        default_factory=lambda: defaultdict(dict),
    )
    cut_cache: DefaultDict[str, Dict[str, str]] = field(
        default_factory=lambda: defaultdict(dict),
    )
    cut_deltas: List[int] = field(
        default_factory=lambda: [2, 10, 30],
    )

    def load_cache(self):
        originals_cache_path = Path(
            f'{self.output_path}/originals/cache_info.json'
        )
        cache = self._load_defaultdict(originals_cache_path)
        if cache: self.download_cache = cache  # noqa: E701

        cut_cache_path = Path(f'{self.output_path}/cut/cache_info.json')
        cache = self._load_defaultdict(cut_cache_path)
        if cache: self.cut_cache = cache  # noqa: E701

    @staticmethod
    def _load_defaultdict(path: Path):
        if path.is_file():
            logger.debug(f'Found cache file in {path}')
            with path.open() as cf:
                return defaultdict(dict, json.load(cf))


def adapt_name_to_all_filesystems(name: str):
    for no_no_symbol in WINDOWS_PATH_CONFLICTING_SYMBOLS:
        name = ''.join(name.split(no_no_symbol))
    return name


def adapt_time_to_path(time_str: str):
    for symbol in [':', '.']:
        time_str = time_str.replace(symbol, '_')
    return time_str


def load_track_list(track_list_path: str) -> list:
    logger.info(f'Loading playlist from {track_list_path}')
    with open(track_list_path) as tl_file:
        return json.load(tl_file)


def download(quiz: QuizModel):
    originals_folder = f'{quiz.output_path}/originals'
    Path(originals_folder).mkdir(parents=True, exist_ok=True)
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
        original_path = f'{originals_folder}/{adapted_title}.webm'
        logger.info(f'Download {audio_stream.title}')
        audio_stream.download(
            filename=original_path
        )
        quiz.download_cache[track['url']] = {
            'path': original_path,
            'name': adapted_title,
        }
        logger.info(f'Download {audio_stream.title} done')


def cut(quiz: QuizModel):
    for track in quiz.track_list:
        track_name = quiz.download_cache[track['url']]['name']
        time_for_path = adapt_time_to_path(track['time'])
        folder_name = f'{track_name} {time_for_path}'
        if track['url'] in quiz.cut_cache and \
           track['time'] in quiz.cut_cache[track['url']]:
            logger.info(f'Found cache for {folder_name}')
            continue
        logger.info(f'Extracting subclip for {folder_name}')
        cut_path = f'{quiz.output_path}/cut/{folder_name}'
        Path(cut_path).mkdir(parents=True, exist_ok=True)
        min, sec = track['time'].split(':')
        start_sec = int(min) * 60 + float(sec)
        clip = AudioFileClip(quiz.download_cache[track['url']]['path'])
        for delta_sec in quiz.cut_deltas:
            subclip = clip.subclip(start_sec, start_sec + delta_sec)
            subclip.write_audiofile(
                f'{cut_path}/{delta_sec}.wav',
                codec='pcm_s16le',
                verbose=False,
                logger=None,
            )
        quiz.cut_cache[track['url']][track['time']] = cut_path
        logger.info(f'Extracting subclip for {folder_name} done')


def save_cache_info(quiz: QuizModel):
    with open(f'{quiz.output_path}/originals/cache_info.json', 'w') as cf:
        json.dump(quiz.download_cache, cf, indent=4)
    with open(f'{quiz.output_path}/cut/cache_info.json', 'w') as cf:
        json.dump(quiz.cut_cache, cf, indent=4)


def main(track_list_path: str, output: str, reset_cache: bool):
    quiz = QuizModel(
        output_path=output,
        track_list=load_track_list(track_list_path),
    )
    if not reset_cache:
        quiz.load_cache()
    download(quiz)
    cut(quiz)
    save_cache_info(quiz)


if __name__ == "__main__":
    parser = ArgumentParser(description='Make quiz music.')
    parser.add_argument('-tl', '--track_list_path',
                        help="Track list file", type=str,
                        default='track_list.json')
    parser.add_argument('-o', '--output',
                        help="Output folder", type=str,
                        default='output')
    parser.add_argument('-rc', '--reset_cache', action=BooleanOptionalAction)
    args = parser.parse_args()
    main(**vars(args))
