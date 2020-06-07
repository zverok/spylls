import re
import time
import os.path
from collections import Counter

from spyll.hunspell.dictionary import Dictionary

def readlist(path, ignoredot=True):
    if not os.path.isfile(path):
        return []
    # we ignore "incomplete tokenization" feature
    return [ln for ln in open(path).read().splitlines() if not ignoredot or ln[-1:] != '.']

def test(name):
    path = f'tests/fixtures/hunspell-orig/{name}'
    dictionary = Dictionary(path)
    bad = readlist(path + '.wrong')
    sug = list(map(lambda s: re.split(r',\s*', s), readlist(path + '.sug', ignoredot=False)))
    return [
        {
            'word': word,
            'expected': sug[i] if i < len(sug) and sug[i][0] != '' else [],
            'got': list(dictionary.suggest(word))
        } for i, word in enumerate(bad)
    ]

stats = Counter()

def section(title):
    print()
    print(title)
    print('=' * len(title))

def report(name, *, pending=[]):
    global stats

    start = time.monotonic()
    result = test(name)
    duration = time.monotonic() - start

    counter = Counter()
    out = []
    for data in result:
        if data['expected'] == data['got']:
            # print(f"  {data['word']}: +")
            counter['good'] += 1
        else:
            if data['word'] in pending:
                counter['pending'] += 1
            else:
                out.append(f"  {data['word']}: {data['expected']} vs {data['got']}")
                counter['bad'] += 1

    summary = f"{name}: {counter['good']} OK"
    if counter['bad'] > 0:
        summary += f", {counter['bad']} fails"
    if counter['pending'] > 0:
        summary += f", {counter['pending']} pending"
    if duration > 0.05:
        stats['slow'] += 1
        summary += f" [{duration:.4f}s]"

    print(summary)
    if out:
        print("\n".join(out))

    stats['total'] += 1
    if counter['bad'] > 0:
        stats['fail'] += 1
    elif counter['pending'] > 0:
        stats['pending'] += 1
    else:
        stats['ok'] += 1

# ==================
section('Base')

report('base')
report('base_utf')

report('allcaps')
report('allcaps2')
report('allcaps_utf')
report('breakdefault')

# ==================
section('Suggest base')

report('sug', pending=['permanent.Vacation'])
report('sugutf', pending=['permanent.Vacation'])

report('sug2')

# ==================
section('Permutations')

report('map')
report('maputf')

report('rep')
report('reputf')


# ==================
section('Prohibit bad suggestions')

report('forceucase')
report('keepcase', pending=['bar']) # one of suggestions with .
report('nosuggest')
report('onlyincompound')

report('opentaal_forbiddenword1')
report('opentaal_forbiddenword2')
# report('opentaal_keepcase') -- reader fail, `break #`

# ==================
section('Phonetical suggestions')

# report('phone')
# report('ph')
# report('ph2')

# ==================
section('IO quirks')

report('oconv')
report('utf8_nonbmp')

# ==================
section('Edge cases and bugs')

report('checksharps')
report('checksharpsutf')

report('ngram_utf_fix')

report('IJ')

report('1463589')
report('1463589_utf')
report('1695964')
report('i35725', pending=['pernament', 'Permenant', 'Pernament', 'Pernemant'])
report('i54633')
report('i58202', pending=['fooBar', 'FooBar', 'BazFoo'])


print()
print("------------")
print(f"{stats['total']} tests: {stats['ok']} OK, {stats['pending']} pending, {stats['fail']} fails ({stats['slow']} slow)")
