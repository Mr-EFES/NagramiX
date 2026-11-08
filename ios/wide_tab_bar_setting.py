"""Восстановленная согласованная настройка широкой панели."""
import hashlib
import json
from pathlib import Path

def apply_wide_tab_bar_setting(source: Path, overlay: Path) -> None:
    plan=json.loads((overlay/'wide_tab_bar_setting_patches.json').read_text())
    if (plan['target_pin']!='24638bc69bd083981b178dd1e7f921eebbf7fc46' or plan['overlay_base_pin']!='279f89e4d4f63f17227bf877dc3d8990f22ecd58'
        or plan.get('required_previous_stage')!='bot_delete_without_block' or any(plan['inputs'].keys()!=plan[k].keys() for k in ('outputs','previous','replacements'))
        or set(plan['inputs']) & set(plan['guards']) or plan['copies'] or plan['deletions']):
        raise SystemExit('wide_tab_bar_setting: inconsistent manifest')
    def checked(root,name,digest):
        relative=Path(name);path=root/relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(root.resolve()):
            raise SystemExit('wide_tab_bar_setting: unsafe path')
        if not path.is_file():raise SystemExit('wide_tab_bar_setting: missing '+name)
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('wide_tab_bar_setting: drift '+name)
        return data
    for name,digest in plan['templates'].items():checked(overlay,name,digest)
    for name,digest in plan['guards'].items():checked(source,name,digest)
    prepared={}
    for name,digest in plan['inputs'].items():
        if checked(source,name,digest)!=checked(overlay,plan['previous'][name],digest):raise SystemExit('wide_tab_bar_setting: previous mismatch '+name)
        prepared[name]=checked(overlay,plan['replacements'][name],plan['outputs'][name])
    # Every dependency and destination is checked before the first write.
    for name,data in prepared.items():(source/name).write_bytes(data)
