from collections import defaultdict


class Leaf:     # pylint: disable=too-few-public-methods
    def __init__(self):
        self.payloads = []
        self.children = defaultdict(Leaf)


class Trie:
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
