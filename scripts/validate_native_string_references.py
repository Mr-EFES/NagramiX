#!/usr/bin/env python3
"""Проверить native строки по фактическому генератору Telegram до долгой SDK-сборки."""
import argparse,json,tempfile
from pathlib import Path
from validate_custom_member_references import canonical_texts
from validate_upstream_13_2_release import checked_plan,OVERLAY
import native_string_references as native

def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--canonical',action='store_true');g.add_argument('--source',type=Path);p.add_argument('--swiftc',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='nagramix-native-strings-') as temporary:
  folder=Path(temporary)
  if a.canonical:
   source=folder/'source';plan=checked_plan('release_095_composer_strings_compile')
   for n in [native.EN,native.GEN,native.BUILD]:
    target=source/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((OVERLAY/plan['guard_sources'][n]).read_bytes())
   texts=canonical_texts()
  else:
   source=a.source;texts={str(p.relative_to(source)):p.read_text() for p in source.rglob('*.swift') if not p.is_symlink()}
  report=native.check(source,texts,a.swiftc,folder)
 if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
