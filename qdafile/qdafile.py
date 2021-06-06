# qdafile.py

# Copyright (c) 2007-2021, Christoph Gohlke
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

:Author:
  `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:License: BSD 3-Clause

:Version: 2021.6.6

Requirements
------------
* `CPython >= 3.7 <https://www.python.org>`_
* `Numpy 1.15 <https://www.numpy.org>`_

Revisions
---------
2021.6.6
    Support os.PathLike file names.
    Remove support for Python 3.6 (NEP 29).
2020.1.1
    Remove support for Python 2.7 and 3.5.

Examples
--------
>>> from qdafile import QDAfile
>>> QDAfile().write('_empty.qda')
>>> QDAfile(
...     [[1.0, 2.0, 0.], [3.0, 4.0, 5.0], [6.0, 7.0, 0.]],
...     rows=[2, 3, '2'],
...     headers=['X', 'Y', 'Z'],
...     dtypes=['>f8', '>i4', '>f4'],
... ).write('_test.qda')
>>> qda = QDAfile('_test.qda')
>>> print(qda)
QDAfile
 _test.qda
 file id: 12
 columns: 3
 rows: [2, 3, 2]
 headers: [b'X', b'Y', b'Z']
 dtypes: ['>f8', '>i4', '>f4']
>>> qda.headers[2]
b'Z'
>>> qda[2, :qda.rows[2]]
array([6., 7.])

"""

__version__ = '2021.6.6'

__all__ = ('QDAfile', 'unique_headers')

import os
import struct

import numpy


class QDAfile:
    """Read or write QDA files.

    Only numeric data types (float, double, and int) are supported.
    All data are converted to double on import. The byte order of the
    binary files is big endian (Motorola).

    Raise IOError or ValueError on failure.

    Attributes
    ----------
    name : str
        File name.
    data : ndarray
        2D numpy array.
    columns : int
        Number of columns.
    headers :
        Sequence of column headers.
    rows : list
        Sequence of number of rows in column.
    dtypes : list
        Sequence of column data types ('>f4', '>f8', or '>i4').

    """

    FID = {b'\x00\x06': 6, b'\x00\x08': 8, b'\x00\x0C': 12}

    DTYPE = {
        0: '>f4',
        3: '>f8',
        4: '>i4',
        1: 'S40',
        '>f4': 0,
        '>f8': 3,
        '>i4': 4,
    }

    def __init__(self, arg=None, **kwargs):
        """Initialize instance using file name/descriptor or data array.

        If arg is an array, keyword arguments can be used to initialize
        name, headers, rows, and dtypes attributes.

        Raise IOError or ValueError on failure.

        """
        self.fid = 12
        self.name = 'Untitled'
        self.data = None
        self.columns = None
        self.rows = None
        self.headers = None
        self.dtypes = None

        if arg is None:
            self._fromdata([], **kwargs)
        elif isinstance(arg, (str, os.PathLike)):
            with open(arg, 'rb') as fh:
                self._fromfile(fh)
        elif hasattr(arg, 'seek'):
            self._fromfile(arg)
        else:
            self._fromdata(arg, **kwargs)

    def write(self, arg=None):
        """Save data to QDA file."""
        if arg is None:
            arg = self.name
        if hasattr(arg, 'seek'):
            self._tofile(arg)
        else:
            with open(arg, 'wb') as fh:
                self._tofile(fh)

    def _fromfile(self, fh):
        """Initialize instance from open file object.

        Raise IOError if file can not be read.

        """
        fid = fh.read(2)
        try:
            self.fid = QDAfile.FID[fid]
        except KeyError as exc:
            raise OSError('not a QDA file or unsupported version') from exc

        columns = numpy.fromfile(fh, dtype='>i2', count=1)[0]
        if 1000 < columns < 0:
            raise OSError('not a QDA file')

        fh.read(512 - 4)
        rows = list(
            numpy.fromfile(
                fh, count=columns, dtype='>i4' if self.fid == 12 else '>i2'
            )
        )

        dtypes = numpy.fromfile(fh, dtype='>i2', count=columns)
        try:
            dtypes = [QDAfile.DTYPE[dt] for dt in dtypes]
        except KeyError as exc:
            raise OSError(
                'the file contains data of unsupported type', dtypes
            ) from exc

        headers = [
            s.split(b'\x00', 1)[0]
            for s in numpy.fromfile(fh, dtype='S40', count=columns)
        ]

        # TODO: store to Pandas dataframe
        data = numpy.empty(
            (columns, max(rows) if rows else 0), dtype='float64'
        )
        data[:] = numpy.NaN
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
        self, data, name='Untitled.qda', headers=None, rows=None, dtypes=None
    ):
        """Initialize instance from data array and optional arguments.

        Raise ValueError if data is incompatible with file format.

        """
        data = numpy.array(data, dtype='>f8')
        data = numpy.atleast_2d(data)
        if len(data.shape) > 2:
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
                [QDAfile.DTYPE[str(dtypes[i])] for i in range(columns)]
            except (IndexError, KeyError) as exc:
                raise ValueError('invalid dtypes argument') from exc
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

    def _tofile(self, fh):
        """Write data to an open file."""
        fh.write(b'\x00\x0C')
        fh.write(struct.pack('>h', self.columns))
        fh.write(b'\x00\x0E\x01\x02\x00\x05\x00\x01')
        fh.write(b'\x00' * (512 - 12))
        for r in self.rows:
            fh.write(struct.pack('>i', r))
        for t in self.dtypes:
            fh.write(struct.pack('>h', QDAfile.DTYPE[t]))
        for h in self.headers:
            h = h.encode('ascii')
            fh.write(h + b'\x00' * (40 - len(h)))
        for i, (r, t, h) in enumerate(
            zip(self.rows, self.dtypes, self.headers)
        ):
            self.data[i, 0:r].astype(t).tofile(fh, format=t)
            fh.write(b'\x00\x01' * r)
            fh.write(b'\x0E\x02\x01\x00\x05\x00\x00\x01')
            h = h.encode('ascii')
            fh.write(h + b'\x00' * (128 - len(h)))

    def __str__(self):
        return '\n '.join(
            (
                self.__class__.__name__,
                self.name,
                f'file id: {self.fid}',
                f'columns: {self.columns}',
                f'rows: {self.rows}',
                f'headers: {self.headers}',
                f'dtypes: {self.dtypes}',
            )
        )

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def unique_headers(number):
    """Return list of unique column headers.

    Examples
    --------
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


if __name__ == '__main__':
    import doctest

    doctest.testmod()
