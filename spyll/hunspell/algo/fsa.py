class Leaf:
    def __init__(self):
        self.payloads = []
        self.children = {}


class FSA:
    def __init__(self, ):
        self.root = Leaf()

    def put(self, path, payload):
        cur = self.root
        for p in path:
            if p in cur.children:
                cur.children[p]
            else:
                cur.children[p] = Leaf()

            cur = cur.children[p]

        cur.payloads.append(payload)

    def lookup(self, path):
        for path, leaf in self.traverse(self.root, path):
            for payload in leaf.payloads:
                yield payload

    def traverse(self, cur, path, traversed=[]):
        yield (traversed, cur)
        if not path or path[0] not in cur.children:
            return
        for p, leaf in self.traverse(cur.children[path[0]], path[1:], [*traversed, path[0]]):
            yield (p, leaf)
