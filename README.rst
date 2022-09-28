Read and write QDA files
========================

Qdafile is a Python library to read and write KaleidaGraph(tm) version 3.x
QDA data files.

KaleidaGraph is a registered trademark of `Abelbeck Software
<http://www.synergy.com>`_.

Qdafile is no longer being actively developed.

:Author: `Christoph Gohlke <https://www.cgohlke.com>`_
:License: BSD 3-Clause
:Version: 2022.9.28

Requirements
------------

This release has been tested with the following requirements and dependencies
(other versions may work):

- `CPython 3.8.10, 3.9.13, 3.10.7, 3.11.0rc2 <https://www.python.org>`_
- `NumPy 1.22.4 <https://pypi.org/project/numpy/>`_

Revisions
---------

2022.9.28

- Return headers as str, not bytes (breaking).
- Add type hints.
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
...     [[1.0, 2.0, 0.], [3.0, 4.0, 5.0], [6.0, 7.0, 0.]],
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
>>> qda[2, :qda.rows[2]]
array([6., 7.])
