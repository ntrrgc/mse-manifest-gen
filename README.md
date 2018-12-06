# mse-manifest-gen

Receives MP4 and WebM files and generates a simple JSON file for each (manifest) with a list of the media segments they contain, including their offsets and start times.

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