from pathlib import Path

from spyll.hunspell import Dictionary

BASE_FOLDER = Path('tests/integrational/fixtures')

def read_list(name, ignoredot=True):
    path = BASE_FOLDER / name
    # So we can uniformely read_list('test_case.{good,wrong}'), even if one of them is absent
    if not path.is_file():
        return []

    return [ln.strip() for ln in path.open().read().splitlines() if not ignoredot or ln[-1:] != '.']

def read_dictionary(name):
    path = BASE_FOLDER / name
    return Dictionary.from_files(str(path))

def section(title):
    print()
    print(title)
    print('=' * len(title))

def summary(stats):
    res = f"{stats['total']} tests: {stats['ok']} OK, {stats['pending']} pending, {stats['fail']} fails"
    if 'slow' in stats:
        res += f" ({stats['slow']} slow)"

    print()
    print("------------")
    print(res)
