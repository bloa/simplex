import collections


Token = collections.namedtuple('Token', ['type', 'value'])

KEYWORDS = {'min', 'max', 'and', 'or', 'xor', 'not', 'if', 'iif'}
MULTI_CHAR_OPS = {'==', '!=', '<=', '>='}
SINGLE_CHAR_OPS = {'+', '-', '*', '/', '<', '>', '!', '='}
IDENTIFIERS_CHARS = {'_', '$', '@'}

def tokenize(s):
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]

        if c.isspace():
            i += 1
            continue

        # numbers
        if c.isdigit():
            start = i
            has_dot = False
            while i < len(s) and (s[i].isdigit() or (s[i] == '.' and not has_dot)):
                if s[i] == '.':
                    has_dot = True
                i += 1
            num = s[start:i]
            value = float(num) if '.' in num else int(num)
            tokens.append(Token('NUMBER', value))

        # identifiers and keywords
        elif c.isidentifier() or c in IDENTIFIERS_CHARS:
            start = i
            while i < len(s) and (s[i].isalnum() or s[i] in IDENTIFIERS_CHARS):
                i += 1
            word = s[start:i]
            if word in KEYWORDS:
                tokens.append(Token('OP', word))
            elif word == 'True':
                tokens.append(Token('BOOL', True))
            elif word == 'False':
                tokens.append(Token('BOOL', False))
            elif word == 'inf':
                tokens.append(Token('NUMBER', float(word)))
            else:
                tokens.append(Token('VAR', word))

        # lists
        elif c in {'(', ')', ','}:
            tmp = {'(': 'LPAREN', ')': 'RPAREN', ',': 'COMMA'}
            tokens.append(Token(tmp[c], c))
            i += 1

        # operators
        elif c in SINGLE_CHAR_OPS:
            next_two = s[i:i+2]
            if next_two in MULTI_CHAR_OPS:
                tokens.append(Token('OP', next_two))
                i += 2
            elif c == '!':
                tokens.append(Token('OP', 'not'))
                i += 1
            else:
                tokens.append(Token('OP', c))
                i += 1

        else:
            msg = f'Unexpected character: {c}'
            raise SyntaxError(msg)

    return tokens
