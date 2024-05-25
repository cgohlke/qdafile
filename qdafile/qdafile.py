# qdafile.py

# Copyright (c) 2007-2024, Christoph Gohlke
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Read and write QDA files.

Qdafile is a Python library to read and write KaleidaGraph(tm) version 3.x
QDA data files.

KaleidaGraph is a registered trademark of `Abelbeck Software
<http://www.synergy.com>`_.

Qdafile is no longer being actively developed.

:Author: `Christoph Gohlke <https://www.cgohlke.com>`_
:License: BSD 3-Clause
:Version: 2024.5.24

Requirements
------------

This revision was tested with the following requirements and dependencies
(other versions may work):

- `CPython <https://www.python.org>`_ 3.9.13, 3.10.11, 3.11.9, 3.12.3
- `NumPy <https://pypi.org/project/numpy>`_ 1.26.4

Revisions
---------

2024.5.24

- Support NumPy 2.
- Fix docstring examples not correctly rendered on GitHub.
- Add py.typed marker.
- Drop support for Python 3.8 and numpy < 1.22 (NEP29).

2022.9.28

- Return headers as str, not bytes (breaking).
- Add type hints.
- Convert to Google style docstrings.
- Drop support for Python 3.7 and numpy < 1.19 (NEP29).

2021.6.6

- Support os.PathLike file names.
- Remove support for Python 3.6 (NEP 29).

2020.1.1

- Remove support for Python 2.7 and 3.5.

Examples
--------

>>> from qdafile import QDAfile
>>> QDAfile().write('_empty.qda')
>>> QDAfile(
...     [[1.0, 2.0, 0.0], [3.0, 4.0, 5.0], [6.0, 7.0, 0.0]],
...     rows=[2, 3, '2'],
...     headers=['X', 'Y', 'Z'],
...     dtypes=['>f8', '>i4', '>f4'],
... ).write('_test.qda')
>>> qda = QDAfile('_test.qda')
>>> print(qda)
<QDAfile '_test.qda'>
  file id: 12
  columns: 3
  rows: [2, 3, 2]
  headers: ['X', 'Y', 'Z']
  dtypes: ['>f8', '>i4', '>f4']
>>> qda.headers[2]
'Z'
>>> qda[2, : qda.rows[2]]
array([6., 7.])

"""

from __future__ import annotations

__version__ = '2024.5.24'

__all__ = ['QDAfile', 'unique_headers']

import os
import struct
from typing import TYPE_CHECKING, BinaryIO, Sequence

import numpy

if TYPE_CHECKING:
    try:
        from numpy.typing import ArrayLike
    except ImportError:
        # numpy < 1.20
        from numpy import ndarray as ArrayLike


class QDAfile:
    """Read or write QDA files.

    Only numeric data types (float, double, and int) are supported.
    All data are converted to float64 on import. The byte order of the
    binary files is big endian (Motorola).

    Parameters:
        arg:
            File name, open file, or data array.
        **kwargs:
            Additional arguments if `arg` is an array or None:
            `name`, `headers`, `rows`, and `dtypes`.

    Raises:
        IOError, OSError:
            Failed to read QDA file.
        ValueError:
            Invalid data or additional arguments.

    """

    FID = {b'\x00\x06': 6, b'\x00\x08': 8, b'\x00\x0C': 12}

    DTYPE_STR = {
        0: '>f4',
        3: '>f8',
        4: '>i4',
        1: 'S40',
    }

    DTYPE_INT = {
        '>f4': 0,
        '>f8': 3,
        '>i4': 4,
    }

    fid: int
    """File identification."""
    name: str
    """File name."""
    data: numpy.ndarray
    """Data in columns and rows."""
    columns: int
    """Number of columns."""
    rows: list[int]
    """Number of rows in each column."""
    headers: list[str]
    """Column headers."""
    dtypes: list[str]
    """Column data types ('>f4', '>f8', or '>i4')."""

    def __init__(
        self, arg: str | os.PathLike | BinaryIO | None = None, /, **kwargs
    ) -> None:
        self.fid = 12
        self.name = 'Untitled'

        if arg is None:
            self._fromdata([], **kwargs)
        elif isinstance(arg, (str, os.PathLike)):
            with open(arg, 'rb') as fh:
                self._fromfile(fh)
        elif isinstance(arg, BinaryIO) or hasattr(arg, 'seek'):
            self._fromfile(arg)
        else:
            self._fromdata(arg, **kwargs)

    def write(
        self,
        arg: str | os.PathLike | BinaryIO | None = None,
        /,
    ) -> None:
        """Save data to QDA file."""
        if arg is None:
            arg = self.name
        if isinstance(arg, BinaryIO) or hasattr(arg, 'seek'):
            self._tofile(arg)  # type: ignore
        else:
            with open(arg, 'wb') as fh:
                self._tofile(fh)

    def _fromfile(self, fh: BinaryIO, /) -> None:
        """Initialize instance from open file object.

        Raise IOError if file can not be read.

        """
        fid = fh.read(2)
        try:
            self.fid = QDAfile.FID[fid]
        except KeyError as exc:
            raise OSError('not a QDA file or unsupported version') from exc

        columns = int(numpy.fromfile(fh, dtype='>i2', count=1)[0])
        if 1000 < columns < 0:
            raise OSError('not a QDA file')

        fh.read(512 - 4)
        rows: list[int] = numpy.fromfile(
            fh, count=columns, dtype='>i4' if self.fid == 12 else '>i2'
        ).tolist()

        types = numpy.fromfile(fh, dtype='>i2', count=columns)
        dtypes = []
        for t in types:
            try:
                dtypes.append(QDAfile.DTYPE_STR[t])
            except KeyError as exc:
                raise ValueError(
                    f'the file contains data of unsupported type {t}'
                ) from exc

        headers: list[str] = [
            s.split(b'\x00', 1)[0].decode('latin_1')
            for s in numpy.fromfile(fh, dtype='S40', count=columns)
        ]

        # TODO: store to Pandas dataframe
        data = numpy.empty(
            (columns, max(rows) if rows else 0), dtype='float64'
        )
        data[:] = numpy.nan
        for i, (row, dtype) in enumerate(zip(rows, dtypes)):
            try:
                data[i, 0:row] = numpy.fromfile(fh, dtype=dtype, count=row)
            except Exception:
                # can not store 'S40'
                pass
            fh.read(136 + 2 * row)

        self.name = fh.name
        self.data = data
        self.dtypes = dtypes
        self.columns = columns
        self.rows = rows
        self.headers = headers

    def _fromdata(
        self,
        arg: ArrayLike,
        /,
        name: str = 'Untitled.qda',
        headers: Sequence[str] | None = None,
        rows: Sequence[int] | None = None,
        dtypes: Sequence[str] | None = None,
    ) -> None:
        """Initialize instance from data array and optional arguments.

        Raise ValueError if data is incompatible with file format.

        """
        data = numpy.array(arg, dtype='>f8')
        data = numpy.atleast_2d(data)
        if data.ndim > 2:
            raise ValueError('data array must be 2 dimensional or less')

        try:
            columns = data.shape[0]
        except IndexError:
            columns = 0
        else:
            if columns > 1000:
                raise ValueError('dimensions of data array are too large')

        if rows:
            try:
                rows = [int(rows[i]) for i in range(columns)]
            except (IndexError, TypeError, ValueError) as exc:
                raise ValueError('invalid rows argument') from exc
        else:
            try:
                rows = [data.shape[1]] * columns
            except IndexError:
                rows = [0]

        if max(rows) > 32768:
            raise ValueError('data array dimensions are too large')

        if headers:
            try:
                headers = [headers[i][0:40] for i in range(columns)]
            except IndexError as exc:
                raise ValueError('invalid headers argument') from exc
        else:
            headers = unique_headers(columns)

        if dtypes:
            try:
                [QDAfile.DTYPE_INT[dtypes[i]] for i in range(columns)]
            except (IndexError, KeyError) as exc:
                raise ValueError('invalid dtypes argument') from exc
            dtypes = list(dtypes)
        else:
            dtypes = ['>f8'] * columns

        if (
            len(dtypes) != columns
            or len(headers) != columns
            or len(rows) != columns
        ):
            raise ValueError('invalid argument(s)')

        self.fid = 12
        self.name = name
        self.data = data
        self.columns = columns
        self.rows = rows
        self.headers = headers
        self.dtypes = dtypes

    def _tofile(self, fh: BinaryIO, /) -> None:
        """Write data to an open file."""
        fh.write(b'\x00\x0C')
        fh.write(struct.pack('>h', self.columns))
        fh.write(b'\x00\x0E\x01\x02\x00\x05\x00\x01')
        fh.write(b'\x00' * (512 - 12))
        for r in self.rows:
            fh.write(struct.pack('>i', r))
        for t in self.dtypes:
            fh.write(struct.pack('>h', QDAfile.DTYPE_INT[t]))
        for h in self.headers:
            b = h.encode('latin_1')
            fh.write(b + b'\x00' * (40 - len(b)))
        for i, (r, t, h) in enumerate(
            zip(self.rows, self.dtypes, self.headers)
        ):
            self.data[i, 0:r].astype(t).tofile(fh, format=t)
            fh.write(b'\x00\x01' * r)
            fh.write(b'\x0E\x02\x01\x00\x05\x00\x00\x01')
            b = h.encode('latin_1')
            fh.write(b + b'\x00' * (128 - len(b)))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key) -> numpy.ndarray:
        return self.data[key]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name!r}>'

    def __str__(self) -> str:
        return indent(
            repr(self),
            f'file id: {self.fid}',
            f'columns: {self.columns}',
            f'rows: {self.rows}',
            f'headers: {self.headers}',
            f'dtypes: {self.dtypes}',
        )


def unique_headers(number: int, /) -> list[str]:
    """Return list of unique column headers.

    Examples:
        >>> unique_headers(3)
        ['A', 'B', 'C']

    """
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    headers = []
    for i in chars:
        if number:
            headers.append(i)
        else:
            return headers
        number -= 1
    for i in chars:
        for j in chars:
            if number:
                headers.append(i + j)
            else:
                return headers
            number -= 1
    for i in chars:
        for j in chars:
            for k in chars:
                if number:
                    headers.append(i + j + k)
                else:
                    return headers
                number -= 1
    raise NotImplementedError()


def indent(*args) -> str:
    """Return joined string representations of objects with indented lines."""
    text = '\n'.join(str(arg) for arg in args)
    return '\n'.join(
        ('  ' + line if line else line) for line in text.splitlines() if line
    )[2:]


if __name__ == '__main__':
    import doctest

    doctest.testmod()
