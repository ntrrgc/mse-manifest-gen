import struct

from bytereader import ByteReader


def parse_big_endian_number(the_bytes: bytes):
    ret = 0
    for byte in the_bytes:
        ret = (ret << 8) | byte
    return ret


def parse_signed_big_endian_number(the_bytes: bytes):
    format = {
        1: "b",
        2: ">h",
        4: ">i",
        8: ">q",
    }[len(the_bytes)]
    return struct.unpack(format, the_bytes)[0]


def read_uint(reader: ByteReader, default: int = 0) -> int:
    if reader.ended:
        return default
    return parse_big_endian_number(reader.read())
