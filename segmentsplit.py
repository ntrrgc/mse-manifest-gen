#!/usr/bin/python3
import os
import sys
from argparse import ArgumentParser

from bytereader import FileByteReader
from matroska import MatroskaParser
from mp4 import MP4Parser


def split_segments(file_path, base_dir):
    if file_path.endswith(".mp4"):
        parser = MP4Parser()
    elif file_path.endswith(".webm"):
        parser = MatroskaParser()
    else:
        print(f"Unsupported extension: {file_path}", file=sys.stderr)
        return

    directory = os.path.join(base_dir, os.path.basename(file_path))
    try:
        os.mkdir(directory)
    except FileExistsError:
        pass

    media_segments = parser.find_media_segments(FileByteReader(open(file_path, "rb")))

    extension = os.path.splitext(file_path)[1]
    with open(file_path, "rb") as srcfile:
        with open(os.path.join(directory, f"init{extension}"), "wb") as dst_file:
            dst_file.write(srcfile.read(media_segments[0].offset))
        for i, segment in enumerate(media_segments, 1):
            if i > 1:
                assert segment.offset == media_segments[i - 2].offset + media_segments[i - 2].size
            with open(os.path.join(directory, f"media{i}{extension}"), "wb") as dst_file:
                dst_file.write(srcfile.read(segment.size))


if __name__ == '__main__':
    parser = ArgumentParser(description="Splits MP4 and WebM MSE Bytestream files into one file per segment.")
    parser.add_argument("--basedir", "-b", help="Base directory where the segments will be extracted to.")
    parser.add_argument("FILES", nargs="+")
    args = parser.parse_args()

    if not os.path.exists(args.basedir):
        os.mkdir(args.basedir)

    for file_path in args.FILES:
        split_segments(file_path, args.basedir)
