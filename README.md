# QUIZ

This is a set of tools to conduct a musical quiz.

## Prerequisites

Install the required packages:
```
pip3 install -r requirements.txt
```
Also, `ffmpeg` may be needed (use apt, brew, whatever).

## Generating audio snippets from YouTube links

1. Create track list json like this:
```jsonc
[
    {
        "url": "https://youtu.be/IxcxyGDD38E", // Youtube url
        "time": "3:14" // from this time subtracks will be created
    },
    {
        "url": "https://youtu.be/WdJZlmhQXug",
        "time": "0:31"
    }
]
```
2. Use cli quiz:
```
python3 quiz.py -tl output/track_list.json -o tmp
```

- `-tl --track_list_path` is path to json with track list, **default**: `"track_list.json"`
- `-o --output` is output folder, **default**: `"output"`
- `-rn --reveal_names` Flag to reveal track names for saving cut folders
- `-rc --reset_cache` Flag to not use existing cache until processing

## Running the Telegram bot to conduct the quiz

The Telegram bot allows participants to use buzzers.
This way, the quiz host will always know which participant was the first to come up with an answer.

Run this line replacing `<BOT_TOKEN>` with the actual token of your bot.
```
python3 telegram_bot.py -t <BOT_TOKEN>
```
