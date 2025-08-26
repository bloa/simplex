import pytest

import simplex.utils


@pytest.mark.parametrize(('unsorted', 'expected'), [
    (['x1', 'x2'], ['x1', 'x2']),
    (['x2', 'x1'], ['x1', 'x2']),
    (['x2', 'a1'], ['x2', 'a1']),
    (['x2', 'a1', 'x', 'a3', 'y4', 'y3', 'z'], ['x', 'x2', 'a1', 'a3', 'y3', 'y4', 'z']),
])
def test_prefix_sort(unsorted, expected):
    assert simplex.utils.prefix_sort(unsorted) == expected

@pytest.mark.parametrize(('unsorted', 'expected'), [
    (['x1', 'x2'], ['x1', 'x2']),
    (['x2', 'x1', 'x1', 'x2'], ['x1', 'x2']),
    (['x2', 'a1', 'a1', 'x2'], ['x2', 'a1']),
])
def test_prefix_unique(unsorted, expected):
    assert simplex.utils.prefix_unique(unsorted) == expected
