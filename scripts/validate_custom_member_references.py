#!/usr/bin/env python3
"""Reject missing custom member names from real production declarations.

Canonical mode checks final exported snapshots early, before the long suite.
Source mode checks every Swift file, then checks string receivers against the
actual PresentationStrings extensions. This is a name contract, not Swift type
checking; the real extensions are compiled by the late string SDK check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from validate_upstream_13_2_release import OVERLAY, checked_plan, checked_sdk_plans

STRINGS = 'submodules/NagramiXCore/Sources/NagramiXPresentationStrings.swift'
RESOLVER = 'submodules/NagramiXCore/Sources/NagramiXAppLocalization.swift'
DECL = re.compile(r'\b(?:var|let|func|case)\s+(nagramiX\w+)')
USE = re.compile(r'\.(nagramiX\w+)')
STRING_USE = re.compile(r'\b\w*[sS]trings\s*\.\s*(nagramiX\w+)')


def audit(texts, full=False):
    getters = set(DECL.findall(texts[STRINGS]) + DECL.findall(texts[RESOLVER]))
    declarations = set().union(*(set(DECL.findall(text)) for text in texts.values()))
    errors = []
    names = set(); count = 0
    for name, text in texts.items():
        for match in STRING_USE.finditer(text):
            member = match.group(1); names.add(member); count += 1
            if member not in getters:
                errors.append(f'{name}:{text.count(chr(10), 0, match.start()) + 1}: undeclared PresentationStrings.{member}')
        if full:
            for match in USE.finditer(text):
                if match.group(1) not in declarations:
                    errors.append(f'{name}:{text.count(chr(10), 0, match.start()) + 1}: undeclared custom member {match.group(1)}')
    if errors:
        raise ValueError('\n'.join(errors))
    return {'swift_files': len(texts), 'string_accesses': count, 'distinct_string_members': len(names), 'actual_string_declarations': len(getters), 'custom_declarations': len(declarations), 'full_custom_name_audit': full}


def canonical_texts():
    post = checked_plan('upstream_13_2_release_post')
    plans, expected = checked_sdk_plans(post)
    sources = dict(post['replacements'])
    for plan in plans:
        sources.update(plan['replacements'])
        sources.update({name: item['source'] for name, item in plan['copies'].items()})
    missing = {expected[name] for name in (STRINGS, RESOLVER) if name not in sources}
    by_hash = {}
    for path in [*OVERLAY.rglob('*.inc'), *OVERLAY.rglob('*.swift')]:
        value = hashlib.sha256(path.read_bytes()).hexdigest()
        if value in missing:
            by_hash[value] = path
    texts = {name: (OVERLAY / origin).read_text() for name, origin in sources.items() if name.endswith('.swift')}
    for name in (STRINGS, RESOLVER):
        if name not in texts:
            texts[name] = by_hash[expected[name]].read_text()
    return texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--canonical', action='store_true')
    group.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.canonical:
        result = audit(canonical_texts())
    else:
        texts = {str(path.relative_to(args.source)): path.read_text() for path in args.source.rglob('*.swift') if not path.is_symlink()}
        result = audit(texts, full=True)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
