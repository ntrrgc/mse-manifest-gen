import struct
from collections import namedtuple
from enum import Enum
from fractions import Fraction
from typing import List
from unittest import TestCase

from bytereader import ByteReader, RegionByteReader, FileByteReader
from byteutils import parse_big_endian_number, parse_signed_big_endian_number
from mseparser import MSEParser, MediaSegment, jsonify


class Box:
    def __init__(self, reader: ByteReader):
        self.offset = reader.position
        size = parse_big_endian_number(reader.read(4))
        kind = reader.read(4)
        if size == 1:
            size = parse_big_endian_number(reader.read(8))
        elif size == 0:
            size = reader.end - reader.position
        if kind == b"uuid":
            kind += reader.read(16)
        content_offset = reader.position
        content_size = size - (content_offset - self.offset)

        self.kind = kind
        self.full_size = size
        self.reader = RegionByteReader(reader, content_offset, content_size)
        reader.skip(content_size)


class FullBox:
    def __init__(self, box: Box):
        self.box = box
        self.version = parse_big_endian_number(box.reader.read(1))
        self.flags = parse_big_endian_number(box.reader.read(3))
        self.reader = RegionByteReader(box.reader, box.reader.position, box.reader.size - 4)


class MovieBox:
    def __init__(self, box: Box):
        self.box = box
        self.movie_header = next(
            MovieHeaderBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"mvhd")
        self.tracks = [TrackBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"trak"]
        assert len(self.tracks) == 1  # only one track supported

    def presentation_offset(self) -> Fraction:
        elst = self.tracks[0].elst
        if elst is None:
            return Fraction(0, 1)

        movie_timescale = self.movie_header.timescale
        track_timescale = self.tracks[0].mdia.mdhd.timescale
        offset = Fraction(0, 1)
        for i, edit in enumerate(elst.edits):
            if edit.media_time == -1:
                # Empty edit
                offset += Fraction(edit.segment_duration, movie_timescale)
            else:
                # Media edit
                offset -= Fraction(edit.media_time, track_timescale)
                assert i == len(elst.edits) - 1
        return offset


class MovieHeaderBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        int_size = 8 if self.full_box.version == 1 else 4
        self.full_box.reader.skip(2 * int_size)  # creation_time, modification_time
        self.timescale = parse_big_endian_number(self.full_box.reader.read(4))


class TrackBox:
    def __init__(self, box: Box):
        self.box = box
        self.tkhd = next(TrackHeaderBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"tkhd")
        self.mdia = next(MediaBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"mdia")
        self.edts = next((EditBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"edts"), None)
        self.elst = self.edts.elst if self.edts is not None else None


class TrackHeaderBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        int_size = 8 if self.full_box.version == 1 else 4
        self.full_box.reader.skip(2 * int_size)  # creation_time, modification_time
        self.track_ID = parse_big_endian_number(self.full_box.reader.read(4))


class MediaBox:
    def __init__(self, box: Box):
        self.box = box
        self.mdhd = next((MediaHeaderBox(box) for box in iter_boxes(box.reader) if box.kind == b"mdhd"))


class MediaHeaderBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        int_size = 8 if self.full_box.version == 1 else 4
        self.full_box.reader.skip(2 * int_size)  # creation_time, modification_time
        self.timescale = parse_big_endian_number(self.full_box.reader.read(4))


class EditBox:
    def __init__(self, box: Box):
        self.box = box
        self.elst = next((EditListBox(box) for box in iter_boxes(box.reader) if box.kind == b"elst"), None)


Edit = namedtuple("Edit", ["segment_duration", "media_time"])


class EditListBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        int_size = 8 if self.full_box.version == 1 else 4
        entry_count = parse_big_endian_number(self.full_box.reader.read(4))

        def read_edit():
            segment_duration = parse_big_endian_number(self.full_box.reader.read(int_size))
            media_time, = struct.unpack(">i", self.full_box.reader.read(int_size))
            self.full_box.reader.skip(4)  # media_rate
            return Edit(segment_duration, media_time)

        self.edits = [read_edit() for _ in range(entry_count)]


class MovieFragmentBox:
    def __init__(self, box: Box):
        self.box = box
        self.trafs = [TrackFragmentBox(box) for box in iter_boxes(box.reader) if box.kind == b"traf"]
        assert len(self.trafs) > 0


class TrackFragmentBox:
    def __init__(self, box: Box):
        self.box = box
        self.tfhd = next(
            TrackFragmentHeaderBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"tfhd")
        self.tfdt = next(
            TrackFragmentBaseMediaDecodeTimeBox(box) for box in iter_boxes(box.reader, rewind=True) if
            box.kind == b"tfdt")
        self.truns = [TrackRunBox(box) for box in iter_boxes(box.reader, rewind=True) if box.kind == b"trun"]


class TFFlags:
    BASE_DATA_OFFSET_PRESENT = 0x1
    SAMPLE_DESCRIPTION_INDEX_PRESENT = 0x2
    DEFAULT_SAMPLE_DURATION_PRESENT = 0x8
    DEFAULT_SAMPLE_SIZE_PRESENT = 0x10
    DEFAULT_SAMPLE_FLAGS_PRESENT = 0x20
    DURATION_IS_EMPTY = 0x10000
    DEFAULT_BASE_IS_MOOF = 0x20000

class TRFlags:
    DATA_OFFSET_PRESENT = 0x1
    FIRST_SAMPLE_FLAGS_PRESENT = 0x4
    SAMPLE_DURATION_PRESENT = 0x100
    SAMPLE_SIZE_PRESENT = 0x200
    SAMPLE_FLAGS_PRESENT = 0x400
    SAMPLE_COMPOSITION_TIME_OFFSETS_PRESENT = 0x800


class TrackFragmentHeaderBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        self.tf_flags = self.full_box.flags


class TrackFragmentBaseMediaDecodeTimeBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        int_size = 8 if self.full_box.version == 1 else 4
        self.base_media_decode_time = parse_big_endian_number(self.full_box.reader.read(int_size))


class TrackRunBox:
    def __init__(self, box: Box):
        self.box = box
        self.full_box = FullBox(box)
        tr_flags = self.full_box.flags
        self.sample_count = parse_big_endian_number(self.full_box.reader.read(4))
        if tr_flags & TRFlags.DATA_OFFSET_PRESENT:
            self.full_box.reader.skip(4)
        if tr_flags & TRFlags.FIRST_SAMPLE_FLAGS_PRESENT:
            self.full_box.reader.skip(4)
        if tr_flags & TRFlags.FIRST_SAMPLE_FLAGS_PRESENT:
            self.full_box.reader.skip(4)

        assert self.sample_count > 0
        # First sample
        if tr_flags & TRFlags.SAMPLE_DURATION_PRESENT:
            self.full_box.reader.skip(4)
        if tr_flags & TRFlags.SAMPLE_SIZE_PRESENT:
            self.full_box.reader.skip(4)
        if tr_flags & TRFlags.SAMPLE_FLAGS_PRESENT:
            self.full_box.reader.skip(4)
        if tr_flags & TRFlags.SAMPLE_COMPOSITION_TIME_OFFSETS_PRESENT:
            self.first_sample_composition_time_offset = parse_signed_big_endian_number(self.full_box.reader.read(4))
        else:
            self.first_sample_composition_time_offset = 0


def iter_boxes(reader: ByteReader, rewind: bool = False):
    if rewind:
        reader.position = reader.start
    while not reader.ended:
        yield Box(reader)


def find_boxes(reader: ByteReader, kind: bytes, rewind: bool = False) -> List[Box]:
    return [box for box in iter_boxes(reader, rewind) if box.kind == kind]


def find_box(reader: ByteReader, kind: bytes, rewind: bool = False, required: bool = False) -> Box:
    for box in iter_boxes(reader, rewind):
        if box.kind == kind:
            return box
    if required:
        raise RuntimeError(f"Could not find {kind} box")


class MP4Parser(MSEParser):
    def find_media_segments(self, reader: ByteReader) -> List[MediaSegment]:
        try:
            moov = MovieBox(next(box for box in iter_boxes(reader) if box.kind == b"moov"))
            moofs = [MovieFragmentBox(box) for box in iter_boxes(reader) if box.kind == b"moof"]

            def fragment_size(fragment_index):
                if fragment_index < len(moofs) - 1:
                    return moofs[fragment_index + 1].box.offset - moofs[fragment_index].box.offset
                else:
                    movie_size = reader.size
                    return movie_size - moofs[fragment_index].box.offset

            return [MediaSegment(moof.box.offset, fragment_size(i), self._moof_start_time(moov, moof))
                    for i, moof in enumerate(moofs)]
        finally:
            reader.close()

    def _moof_start_time(self, moov: MovieBox, moof: MovieFragmentBox):
        traf = moof.trafs[0]
        track_timescale = moov.tracks[0].mdia.mdhd.timescale
        return Fraction(traf.tfdt.base_media_decode_time + traf.truns[0].first_sample_composition_time_offset,
                        track_timescale) + moov.presentation_offset()


class TestCar(TestCase):
    def test_car(self):
        print(jsonify(MP4Parser().find_media_segments(FileByteReader(open("media/car-20120827-86.mp4", "rb")))))
