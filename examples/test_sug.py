import re
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

def report(name):
    result = test(name)
    counter = Counter()
    pending = pendings.get(name, [])
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
    print(summary)
    if out:
        print("\n".join(out))

pendings = {
    'base_utf': ['loooked'],
    'sug': ['permanent.Vacation'],
    'sugutf': ['permanent.Vacation'],
    'IJ': ['Ijs'],
    'keepcase': ['bar'],
    'i35725': [
      'pernament',
      'Permenant',
      'Pernament',
      'Pernemant'
    ],
    'i58202': [
      'fooBar',
      'FooBar',
      'BazFoo'
    ]
}

report('base')
report('base_utf')

report('sug')
report('sugutf')

report('sug2')

report('map')
report('maputf')

report('rep')
report('reputf')

report('ngram_utf_fix')

report('IJ')

report('1463589')
report('1463589_utf')
report('1695964')
report('i35725')
report('i54633')
report('i58202')

# report('checksharps') -- CHECKSHARPS+KEEPCASE means "upcase sharp s" is prohibited :facepalm:
# report('checksharpsutf')

report('allcaps')
report('allcaps2')
report('allcaps_utf')
# report('breakdefault') -- need to add BREAK to lookup, then suggest will work
# report('forceucase') -- "FORCEUCASE" flag pollutes the whole compound, check with lookup?
report('keepcase')
report('nosuggest')
report('onlyincompound')
# report('opentaal_forbiddenword1')
# report('opentaal_forbiddenword2')
# report('opentaal_keepcase')

# report('phone')
# report('ph')
# report('ph2')

report('oconv')
# report('utf8_nonbmp')
