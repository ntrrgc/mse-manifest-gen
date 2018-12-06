from fractions import Fraction
from typing import List, Optional
from unittest import TestCase

from bytereader import ByteReader, FileByteReader, RegionByteReader
from byteutils import parse_big_endian_number, read_uint
from mseparser import WrongFile, MSEParser, MediaSegment, jsonify


def read_vint(reader: ByteReader, raw: bool = False):
    header_byte = ord(reader.read(1))
    if header_byte == 0:
        raise WrongFile("VINT with zero header byte")
    tail_length = 0
    mask = 0x80
    while header_byte & mask == 0:
        tail_length += 1
        mask >>= 1

    header_number_part = header_byte & ~mask if not raw else header_byte
    return parse_big_endian_number(bytes([header_number_part]) + reader.read(tail_length))


def read_element_header(reader: ByteReader):
    element_id = read_vint(reader, raw=True)
    size = read_vint(reader)
    return element_id, size


class Element:
    # offset and full_size here include the element header too
    def __init__(self, element_id, header_offset, header_size, content_size, parent_reader):
        self.element_id = element_id
        self.offset = header_offset
        self.full_size = header_size + content_size
        self.reader = RegionByteReader(parent_reader, header_offset + header_size, content_size)


def read_element(reader: ByteReader):
    header_offset = reader.position
    element_id, content_size = read_element_header(reader)
    header_size = reader.position - header_offset
    return Element(element_id, header_offset, header_size, content_size, reader)


def iter_elements(reader: ByteReader):
    while not reader.ended:
        element = read_element(reader)
        yield element
        reader.skip(element.reader.size)


def find_element(reader: ByteReader, element_id: int) -> Optional[Element]:
    for element in iter_elements(reader):
        if element.element_id == element_id:
            return element


class Cluster:
    def __init__(self, element: Element, timestamp_scale_value: int):
        assert element.element_id == 0x1F43B675
        self.element = element
        self.timestamp = Fraction(read_uint(find_element(element.reader, 0xE7).reader),
                                  Fraction(1_000_000_000, timestamp_scale_value))


class MatroskaParser(MSEParser):
    def find_media_segments(self, reader: ByteReader) -> List[MediaSegment]:
        try:
            ebml_id, size = read_element_header(reader)
            assert ebml_id == 0x1A45DFA3
            reader.skip(size)

            segment_id, _ = read_element_header(reader)
            assert segment_id == 0x18538067

            segment_reader = RegionByteReader(reader, reader.position, size=None)

            segment_info = next(
                element for element in iter_elements(segment_reader) if element.element_id == 0x1549A966)
            timestamp_scale = next(
                (element for element in iter_elements(segment_info.reader) if element.element_id == 0x2AD7B1), None)
            timestamp_scale_value = read_uint(timestamp_scale.reader) if timestamp_scale is not None else 1000000

            clusters = [Cluster(element, timestamp_scale_value) for element in iter_elements(segment_reader) if
                        element.element_id == 0x1F43B675]
            return [MediaSegment(offset=cluster.element.offset, size=cluster.element.full_size, time=cluster.timestamp)
                    for cluster in clusters]
        finally:
            reader.close()


class TestGolf(TestCase):
    def test_golf(self):
        print(jsonify(MatroskaParser().find_media_segments(FileByteReader(open("media/golf-v-250k-160x90.webm", "rb")))))
