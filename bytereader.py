import os
from abc import abstractmethod, ABCMeta
from io import BytesIO
from typing import Optional, BinaryIO
from unittest import TestCase


class ByteReader(metaclass=ABCMeta):
    def __init__(self, start: int, size: int):
        self.start = start
        self.size = size
        self.position = start

    @property
    def end(self):
        return self.start + self.size

    def read_at(self, position: int, num_bytes: int) -> bytes:
        assert num_bytes >= 0
        if not (self.start <= position <= self.end):
            raise RuntimeError(f"Illegal read, attempted to read [{position}, {position + num_bytes}) in "
                               f"[{self.start}, {self.end})")
        num_bytes = min(num_bytes, self.end - position)
        return self._read_at(position, num_bytes)

    @abstractmethod
    def _read_at(self, position: int, num_bytes: int) -> bytes:
        pass

    def close(self):
        pass

    def read(self, num_bytes: Optional[int] = None) -> bytes:
        if num_bytes is None:
            num_bytes = self.end - self.position
        ret = self.read_at(self.position, num_bytes)
        if ret:
            self.position += len(ret)
        return ret

    def peek(self, num_bytes: int) -> Optional[bytes]:
        return self.read_at(self.position, num_bytes)

    def skip(self, num_bytes: int):
        self.position = min(self.position + num_bytes, self.end)

    @property
    def ended(self):
        return self.position >= self.end


class FileByteReader(ByteReader):
    def __init__(self, file: BinaryIO):
        self._file = file
        self._file.seek(0, os.SEEK_END)
        super().__init__(start=0, size=self._file.tell())

    def close(self):
        self._file.close()

    def _read_at(self, pos: int, num_bytes: int) -> bytes:
        self._file.seek(pos, os.SEEK_SET)
        ret = self._file.read(num_bytes)
        return ret


class RegionByteReader(ByteReader):
    def __init__(self, parent: ByteReader, offset: int, size: Optional[int]):
        assert offset >= 0
        if size is None:
            size = parent.end - offset
        assert size >= 0
        assert offset + size <= parent.end
        super().__init__(start=offset, size=size)
        self._parent = parent

    def _read_at(self, position: int, num_bytes: int) -> Optional[bytes]:
        num_bytes = min(num_bytes, self.end - position)
        return self._parent.read_at(position, num_bytes)


class TestReaders(TestCase):
    def test_region(self):
        file_reader = FileByteReader(BytesIO(bytes(range(10))))
        file_reader.skip(8)
        self.assertEqual(bytes([8, 9]), file_reader.read(2))
        self.assertEqual(b"", file_reader.read(1))

        region_reader = RegionByteReader(file_reader, 5, 3)
        self.assertEqual(5, region_reader.start)
        self.assertEqual(5, region_reader.position)
        self.assertEqual(3, region_reader.size)
        self.assertEqual(bytes([5, 6]), region_reader.read(2))
        self.assertEqual(bytes([7]), region_reader.read(2))
        self.assertEqual(b"", region_reader.read(1))

        region_reader = RegionByteReader(file_reader, 2, 6)
        nested_reader = RegionByteReader(region_reader, 4, 2)
        self.assertEqual(4, nested_reader.start)
        self.assertEqual(4, nested_reader.position)
        self.assertEqual(2, nested_reader.size)
        self.assertEqual(bytes([4, 5]), nested_reader.read(2))
        self.assertEqual(6, nested_reader.position)
        self.assertTrue(nested_reader.ended)
