import re

def parse_flags(string, format='short'):
    if string is None:
      return []

    # TODO: should be aware of flag aliases (if it is number, but format is NOT numeric, try alias)
    # TODO: what if string format doesn't match expected (odd number of chars for long, etc.)?
    if format == 'short':
      return {*string}
    elif format == 'long':
      return {*re.findall(r'..', string)}
    elif format == 'num':
      return {*re.findall(r'\d+(?=,|$)', string)}
    # TODO: other flag formats: UTF, unknown
