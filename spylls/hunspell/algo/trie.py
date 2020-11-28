from collections import defaultdict


class Leaf:     # pylint: disable=too-few-public-methods,missing-class-docstring
    def __init__(self):
        self.payloads = []
        self.children = defaultdict(Leaf)


class Trie:
    """
    `Trie <https://en.wikipedia.org/wiki/Trie>`_ is a data structure for effective prefix search. It
    is used in Spylls to store prefixes and suffixes. For example, if we have suffixes "s", "ions",
    "ications", they are stored (reversed) this way:

    .. code-block:: text

        root
        +-s           ... metadata for suffix "s"
          +-noi       ... metadata for suffix "ions"
              +-taci  ... metadata for suffix "ications"

    So, for the word "complications", we can receive all its possible suffixes (all three) in one
    pass through trie.

    **Important:** Profiling shows that search through Trie of suffixes/prefixes is the center of
    Spylls performance, that's why it is very primitive and fast implementation instead of some
    library like `pygtrie <https://github.com/google/pygtrie>`_. Probably, by chosing fast (C)
    implementation of trie, the whole spylls can be make much faster.
    """
    def __init__(self, data=None):
        self.root = Leaf()
        if data:
            for key, val in data.items():
                self.set(key, val)

    def put(self, path, payload):
        cur = self.root
        for p in path:
            cur = cur.children[p]

        cur.payloads.append(payload)

    def set(self, path, payloads):
        cur = self.root
        for p in path:
            cur = cur.children[p]

        cur.payloads = payloads

    def lookup(self, path):
        for _, leaf in self.traverse(self.root, path):
            for payload in leaf.payloads:
                yield payload

    def traverse(self, cur, path, traversed=[]):
        yield (traversed, cur)
        if not path or path[0] not in cur.children:
            return
        for p, leaf in self.traverse(cur.children[path[0]], path[1:], [*traversed, path[0]]):
            yield (p, leaf)
