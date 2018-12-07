## manifestgen.py

Receives MP4 and WebM MediaSource Extensions ByteStream files and generates a simple JSON file for each (manifest) with a list of the media segments they contain, including their offsets and start times.

For use mostly in tests, where using a more complex manifest format is undesirable. Notably there is no support for multi-track files.  

Usage:

```bash
./manifestgen.py media.webm media.mp4
```

Example of generated manifest:

```json
{
    "url": "webm/golf-v-500k-320x180.webm",
    "type": "video/webm; codecs=\"vp9\"",
    "init_segment_size": 636,
    "media_segments": [
        {
            "offset": 636,
            "size": 282297,
            "time": 0.0
        },
        {
            "offset": 282933,
            "size": 320201,
            "time": 5.005
        },
        {
            "offset": 603134,
            "size": 333700,
            "time": 10.01
        },
        {
            "offset": 936834,
            "size": 316274,
            "time": 15.015
        }
    ]
}
```

## segmentsplit.py

Receives MP4 and WebM MediaSource Extensions ByteStream files and extracts them into little segment files. The concatenation of these files gives back the original file.

These files are very useful when doing tests in the command line, for instance:

```bash
$ ./segmentsplit.py --basedir segments high.webm low.webm
$ tree segments
segments/
├── high.webm
│   ├── init.webm
│   ├── media1.webm
│   ├── media2.webm
│   ├── media3.webm
│   ├── media4.webm
│   └── media5.webm
├── low.webm
│   ├── init.webm
│   ├── media1.webm
│   ├── media2.webm
│   ├── media3.webm
│   ├── media4.webm
│   └── media5.webm
└── golf-v-*.webm

2 directories, 12 files
$ gst-play-1.0 <(cat segments/low.webm/{init,media{1,2}}.webm segments/high.webm{init,media{3..5}}.webm)
```