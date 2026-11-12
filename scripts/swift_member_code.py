"""Выделить Swift-код, сохраняя интерполяции, позиции и номера строк."""
import re
from localization_literals import _comment_end, _opening, _expression_end, quoted

TOKENS = re.compile(r'//|/\*|#+"|"')


def code_view(text):
    result = list(text)

    def mask(start, end):
        result[start:end] = ['\n' if ch == '\n' else ' ' for ch in text[start:end]]

    def scan(start, limit):
        cursor = start
        while True:
            token = TOKENS.search(text, cursor, limit)
            if token is None:
                return
            index = token.start()
            end = _comment_end(text, index)
            if end is not None:
                mask(index, end)
                cursor = end
                continue
            opening = _opening(text, index)
            end, _ = quoted(text, index)
            mask(index, end)
            escape = '\\' + (opening.group(1) or '')
            position = index + len(opening.group())
            while position < end:
                if text.startswith(escape + '(', position):
                    expression = position + len(escape) + 1
                    close = _expression_end(text, expression)
                    result[expression:close] = list(text[expression:close])
                    scan(expression, close)
                    position = close + 1
                elif text.startswith(escape, position):
                    position += len(escape) + 1
                else:
                    position += 1
            cursor = end

    scan(0, len(text))
    return ''.join(result)


def contract(audit, strings, resolver):
    # A literal/comment may neither use a Swift member nor declare one. Real
    # expressions inside ordinary/raw/nested interpolations stay fully audited.
    models = {strings: 'extension PresentationStrings { var nagramiXKnown: String { "ok" } }', resolver: ''}
    accepted = [
        'let x = "window.nagramiXJavaScript()"',
        'let x = #"window.nagramiXJavaScript()"#',
        'let x = """\nwindow.nagramiXJavaScript()\n"""',
        'let x = ##"""\nwindow.nagramiXJavaScript()\n"""##',
        '// node.nagramiXMissing\n/* outer /* nested */ node.nagramiXMissing */',
        r'let x = "\\(node.nagramiXEscaped)"',
        r'let x = "\(strings.nagramiXKnown)"',
        r'let x = ##"\##(strings.nagramiXKnown)"##',
    ]
    rejected = [
        r'let x = "\(node.nagramiXMissing)"',
        r'let x = #"\#(node.nagramiXMissing)"#',
        r'let x = ##"\##(node.nagramiXMissing)"##',
        r'let x = #"\#(f("nested \(node.nagramiXMissing)"))"#',
        'let x = "var nagramiXPhantom = 1"\nnode.nagramiXPhantom()',
        '// var nagramiXPhantom = 1\nnode.nagramiXPhantom()',
        r'let x = "\(strings.nagramiXMissing)"',
    ]
    for text in accepted:
        view = code_view(text)
        assert len(view) == len(text) and view.count('\n') == text.count('\n')
        audit({**models, 'fixture.swift': text}, full=True)
    for text in rejected:
        try:
            audit({**models, 'fixture.swift': text}, full=True)
        except ValueError as error:
            assert 'undeclared' in str(error), error
        else:
            raise AssertionError('Swift member hidden by a literal: ' + text)
    try:
        code_view('let invalid = "unclosed')
    except ValueError:
        pass
    else:
        raise AssertionError('Unclosed literal accepted')
    return {'accepted_literals_and_comments': len(accepted), 'missing_real_members_rejected': len(rejected), 'unterminated_literal_rejected': True, 'interpolations_preserved': True}
