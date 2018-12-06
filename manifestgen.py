#!/usr/bin/python3
import sys
from argparse import ArgumentParser

from bytereader import FileByteReader
from matroska import MatroskaParser
from mp4 import MP4Parser
from mseparser import jsonify

parser = ArgumentParser(description="Generates manifests for MP4 and WebM MSE Bytestream files.")
parser.add_argument("FILES", nargs="+")
args = parser.parse_args()


def generate_manifest(file_path):
    if file_path.endswith(".mp4"):
        parser = MP4Parser()
    elif file_path.endswith(".webm"):
        parser = MatroskaParser()
    else:
        print(f"Unsupported extension: {file_path}", file=sys.stderr)
        return

    media_segments = parser.find_media_segments(FileByteReader(open(file_path, "rb")))
    manifest = {
        "url": file_path,
        "init_segment_size": media_segments[0].offset,
        "media_segments": media_segments,
    }

    manifest_path = file_path + "-manifest.json"
    with open(manifest_path, "w") as f:
        f.write(jsonify(manifest))


for file_path in args.FILES:
    generate_manifest(file_path)
