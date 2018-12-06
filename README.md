# mse-manifest-gen

Receives MP4 and WebM files and generates a simple JSON file for each (manifest) with a list of the media segments they contain, including their offsets and start times.

For use mostly in tests, where using a more complex manifest format is undesirable. Notably there is no support for multi-track files.  

Usage:

```bash
./manifestgen.py media.webm media.mp4
```

Example of generated manifest:

```bash
{
  "init_segment_size": 635,
  "media_segments": [
    {
      "offset": 635,
      "size": 125412,
      "time": 0.0
    },
    {
      "offset": 126047,
      "size": 129504,
      "time": 5.005
    },
    {
      "offset": 255551,
      "size": 137000,
      "time": 10.01
    },
    {
      "offset": 392551,
      "size": 137099,
      "time": 15.015
    }
  ]
}
```