"""Читать обычные/raw/multiline литералы Swift и их интерполяции без комментариев."""
import re

_OPENING = re.compile(r'(#+)?("""|")')


def _comment_end(text, start):
    if text.startswith('//', start):
        end = text.find('\n', start)
        return len(text) if end < 0 else end + 1
    if not text.startswith('/*', start):
        return None
    depth, index = 1, start + 2
    while index < len(text) and depth:
        if text.startswith('/*', index):
            depth += 1; index += 2
        elif text.startswith('*/', index):
            depth -= 1; index += 2
        else:
            index += 1
    if depth:
        raise ValueError('Unclosed Swift comment')
    return index


def _opening(text, start):
    match = _OPENING.match(text, start)
    return match if match else None


def _expression_end(text, start):
    depth, index = 1, start
    while index < len(text):
        comment = _comment_end(text, index)
        if comment is not None:
            index = comment; continue
        if _opening(text, index):
            index, _ = quoted(text, index); continue
        if text[index] == '(':
            depth += 1
        elif text[index] == ')':
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError('Unclosed Swift interpolation')


def quoted(text, start):
    opening = _opening(text, start)
    if not opening:
        raise ValueError('Not a Swift string')
    hashes, quote = opening.group(1) or '', opening.group(2)
    end_mark, escape = quote + hashes, '\\' + hashes
    index = start + len(opening.group())
    parts, literal = [], ''
    if quote == '"""' and text.startswith('\n', index):
        index += 1
    escapes = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '"': '"', "'": "'", '\\': '\\'}
    while index < len(text):
        if text.startswith(end_mark, index):
            parts.append(('text', literal))
            if quote == '"""':
                indent = text[text.rfind('\n', 0, index) + 1:index]
                if not indent.strip():
                    stripped, line_start = [], True
                    for kind, value in parts:
                        if kind == 'arg':
                            stripped.append((kind, value)); line_start = False; continue
                        lines = value.splitlines(keepends=True)
                        output = ''
                        for line in lines:
                            if line_start and line.startswith(indent):
                                line = line[len(indent):]
                            output += line
                            line_start = line.endswith('\n')
                        stripped.append((kind, output))
                    parts = stripped
                    if parts and parts[-1][0] == 'text':
                        parts[-1] = ('text', parts[-1][1].removesuffix('\n'))
            return index + len(end_mark), parts
        if text.startswith(escape, index):
            following = index + len(escape)
            if following >= len(text):
                raise ValueError('Unclosed Swift escape')
            value = text[following]
            if value == '(':
                parts.append(('text', literal)); literal = ''
                end = _expression_end(text, following + 1)
                parts.append(('arg', text[following + 1:end])); index = end + 1; continue
            if value in escapes:
                literal += escapes[value]; index = following + 1; continue
            if value == 'u' and text.startswith('{', following + 1):
                end = text.find('}', following + 2)
                if end < 0:
                    raise ValueError('Unclosed Unicode escape')
                literal += chr(int(text[following + 2:end], 16)); index = end + 1; continue
            if quote == '"""' and value in '\r\n':
                index = following + 1
                while index < len(text) and text[index] in ' \t':
                    index += 1
                continue
            if not hashes:
                raise ValueError('Unsupported Swift escape: ' + value)
        literal += text[index]; index += 1
    raise ValueError('Unclosed Swift string')


def literals(text):
    index = 0
    while index < len(text):
        comment = _comment_end(text, index)
        if comment is not None:
            index = comment; continue
        if _opening(text, index):
            end, parts = quoted(text, index)
            yield index, end, parts
            index = end; continue
        index += 1


def canonical(parts):
    if not any(kind == 'arg' for kind, _ in parts):
        return ''.join(value for _, value in parts)
    count, result = 0, ''
    for kind, value in parts:
        if kind == 'arg':
            count += 1; result += f'%{count}$@'
        else:
            result += value.replace('%', '%%')
    return result
