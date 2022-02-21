# QUIZ

Usage: 

1. Install required packages:
```
pip3 install requirements.txt
```
Also `ffmpeg` may need (apt, brew, whatever)

2. Create track list json like this:
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
3. Use cli quiz: 
```
python3 quiz.py -tl output/track_list.json -o tmp
```

- `-tl --track_list_path` is path to json with track list, **default**: `"track_list.json"`
- `-o --output` is output folder, **default**: `"output"`
