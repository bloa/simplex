import re


def prefix_sort(unsorted):
    data = {}
    order = []
    for x in unsorted:
        m = re.match(r'([A-z]+)([0-9]*)', x)
        assert m
        pre, suf = m.group(1), m.group(2)
        if pre in order:
            data[pre].append(suf)
        else:
            data[pre] = [suf]
            order.append(pre)
    return [f'{pre}{suf}' for pre in order for suf in sorted(data[pre], key=lambda s: int(s) if s else -1)]

def prefix_unique(unsorted):
    tmp = prefix_sort(unsorted)
    return sorted(set(unsorted), key=lambda x: tmp.index(x))
