import json
from argparse import ArgumentParser
from pathlib import Path

from pytube import YouTube
from pytube.cli import on_progress
from moviepy.editor import AudioFileClip


CUT_DELTAS = [2, 10, 30]


def load_track_list(track_list_path: str) -> list:
    with open(track_list_path) as tl_file:
        return json.load(tl_file)


def download(track_list: list, output_folder: str):
    originals_folder = f'{output_folder}/originals'
    Path(originals_folder).mkdir(parents=True, exist_ok=True)
    for track in track_list:
        audio_stream = YouTube(
            track['url'],
            on_progress_callback=on_progress
        ).streams.filter(
            only_audio=True,
        ).last()
        track.update({
            'name': audio_stream.title,
            'path': f'{originals_folder}/{audio_stream.title}.webm'
        })
        print(f"Download - {audio_stream.title}")
        audio_stream.download(
            filename=track['path']
        )
        print(f"Download - {audio_stream.title} done")


def cut(track_list: str, output_folder: str):
    for track in track_list:
        track_output = f'{output_folder}/cut/{track["name"]}'
        Path(track_output).mkdir(parents=True, exist_ok=True)
        min, sec = track['time'].split(':')
        start_sec = int(min) * 60 + float(sec)
        clip = AudioFileClip(track['path'])
        for delta_sec in CUT_DELTAS:
            subclip = clip.subclip(start_sec, start_sec + delta_sec)
            subclip.write_audiofile(
                f'{track_output}/{delta_sec}.wav',
                codec='pcm_s16le'
            )


def main(track_list_path: str, output: str):
    track_list = load_track_list(track_list_path)
    download(track_list, output)
    cut(track_list, output)


if __name__ == "__main__":
    parser = ArgumentParser(description='Make quiz music.')
    parser.add_argument('-tl', '--track_list_path',
                        help="Track list file", type=str,
                        default='track_list.json')
    parser.add_argument('-o', '--output',
                        help="Output folder", type=str,
                        default='output')

    args = parser.parse_args()
    main(**vars(args))
