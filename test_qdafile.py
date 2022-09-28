# test_qdafile.py

"""Qdafile package tests."""

import os
import glob

from qdafile import QDAfile


def test_qdafile():
    """More QDAfile class tests."""
    QDAfile().write('tests\\_empty.qda')
    QDAfile(
        [[1.0, 2.0, 0.0], [3.0, 4.0, 5.0], [6.0, 7.0, 0.0]],
        rows=[2, 3, '2'],
        headers=['X', 'Y', 'Z'],
        dtypes=['>f8', '>i4', '>f4'],
    ).write('tests\\_test.qda')

    for f in glob.glob(os.path.join('tests', '*.qda')):
        print('\n', f)
        try:
            kg = QDAfile(f)
        except OSError as e:
            print(e)
        else:
            print(kg)
            print(kg.data)


if __name__ == '__main__':
    test_qdafile()
