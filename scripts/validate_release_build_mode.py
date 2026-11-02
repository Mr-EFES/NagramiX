#!/usr/bin/env python3
"""Публикация всегда требует чистой SDK-сборки, независимо от ручного флага."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def block(text, name):
    start = text.index('      - name: ' + name + '\n')
    end = text.find('\n      - name:', start + 1)
    return text[start:end if end >= 0 else len(text)]


def condition(step, clean, publish):
    value = re.search(r'^        if: \$\{\{ (.*?) \}\}$', step, re.MULTILINE).group(1)
    value = value.replace('inputs.clean_build', str(clean)).replace('inputs.publish_release', str(publish))
    value = value.replace('&&', ' and ').replace('||', ' or ').replace('!', ' not ').strip()
    tree = ast.parse(value, mode='eval')
    allowed = (ast.Expression, ast.BoolOp, ast.UnaryOp, ast.Constant, ast.And, ast.Or, ast.Not)
    assert all(isinstance(node, allowed) for node in ast.walk(tree))
    return eval(compile(tree, '<workflow condition>', 'eval'), {'__builtins__': {}}, {})


def main():
    text = (ROOT / '.github/workflows/build-unsigned-ipa.yml').read_text()
    prepare = block(text, 'Подготовить чистую SDK-сборку')
    restore = block(text, 'Восстановить кеш Bazel')
    confirm = block(text, 'Подтвердить холодную основу релизной сборки')
    for clean, publish, expected_restore, expected_prepare in (
        (False, False, True, False),
        (True, False, False, True),
        (False, True, False, True),
        (True, True, False, True),
    ):
        assert condition(restore, clean, publish) == expected_restore
        assert condition(prepare, clean, publish) == expected_prepare
        assert condition(confirm, clean, publish) == publish
    assert text.index(prepare) < text.index(block(text, 'Получить Telegram-iOS'))
    assert 'test "$BAZEL_CACHE" = "$GITHUB_WORKSPACE/.bazel-cache"' in prepare
    assert 'rm -rf -- "$BAZEL_CACHE"' in prepare
    assert '!inputs.publish_release' in block(text, 'Сохранить кеш Bazel')
    assert 'RESTORED_CACHE_KEY' in confirm and '.iterdir()' in confirm
    print('Режим релиза: всегда чистый SDK; четыре сочетания параметров проверены')


if __name__ == '__main__':
    main()
