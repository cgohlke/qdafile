Read and write QDA files
========================

Qdafile is a Python library to read and write KaleidaGraph(tm) version 3.x
QDA data files.

KaleidaGraph is a registered trademark of `Abelbeck Software
<http://www.synergy.com>`_.

Qdafile is no longer being actively developed.

:Author:
  `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:License: BSD 3-Clause

:Version: 2020.1.1

Requirements
------------
* `CPython >= 3.6 <https://www.python.org>`_
* `Numpy 1.14 <https://www.numpy.org>`_

Revisions
---------
2020.1.1
    Remove support for Python 2.7 and 3.5.
    Update copyright.

Examples
--------
>>> from qdafile import QDAfile
>>> QDAfile().write('_empty.qda')
>>> QDAfile(
...     [[1.0, 2.0, 0.], [3.0, 4.0, 5.0], [6.0, 7.0, 0.]],
...     rows=[2, 3, '2'],
...     headers=['X', 'Y', 'Z'],
...     dtypes=['>f8', '>i4', '>f4'],
...     ).write('_test.qda')
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
