#!/usr/bin/env python3
"""Подготовить для просмотра только значения каталога UI; сеть не используется."""
import argparse
import hashlib
import json
from pathlib import Path
from validate_app_language_localization import strings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    resource=args.source/'submodules/NagramiXCore/Resources/en.lproj/Localizable.strings'
    catalog=strings(resource)
    if not catalog or not all(key.startswith('NagramiX.') for key in catalog):
        raise SystemExit('Ожидался отдельный каталог NagramiX UI')
    payload=json.dumps(list(catalog.values()),ensure_ascii=False,indent=2)+'\n'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(payload)
    review={'destination':'Google Translate (translate.googleapis.com)',
            'scope':'Только значения UI: подписи, подсказки, ошибки, debug. Без ключей каталога, кода, переписки и credentials.',
            'count':len(catalog),'unique_texts':len(set(catalog.values())),
            'sha256':hashlib.sha256(payload.encode()).hexdigest(),
            'network_used':False,'external_transfer_status':'awaiting_explicit_payload_and_destination_approval'}
    args.output.with_suffix('.review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    print(f'Подготовлено {len(catalog)} UI-текстов; SHA256 {review["sha256"]}. Ничего не отправлено.')

if __name__=='__main__':main()
