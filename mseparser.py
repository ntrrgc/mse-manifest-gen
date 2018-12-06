import json
from abc import ABCMeta, abstractmethod
from fractions import Fraction
from typing import List

from bytereader import ByteReader


class WrongFile(Exception):
    pass


class MediaSegment:
    def __init__(self, offset: int, size: int, time: Fraction):
        self.offset = offset
        self.size = size
        self.time = time

    def to_dict(self):
        return {
            "offset": self.offset,
            "size": self.size,
            "time": float(self.time)
        }


class MSEParser(metaclass=ABCMeta):
    @abstractmethod
    def find_media_segments(self, reader: ByteReader) -> List[MediaSegment]:
        pass


class CustomizableJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def jsonify(thing):
    return json.dumps(thing, cls=CustomizableJsonEncoder, indent=2)
