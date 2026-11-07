#!/usr/bin/env python3
"""Reject wrong native13.2 input origins before the lengthy CI source suite."""
import copy
import hashlib
from validate_upstream_13_2_release import OVERLAY, checked_plan, native_input_contract


def main():
    checked_plan('upstream_13_2_release_pre')
    plan = checked_plan('upstream_13_2_release_post')
    compile_plan = checked_plan('upstream_13_2_release_compile')
    for name, expected in compile_plan['inputs'].items():
        assert expected == {**plan['outputs'], **plan['guards']}[name], 'Broken SDK stage chain: ' + name
    for name, expected in compile_plan['guards'].items():
        assert expected == {**plan['outputs'], **plan['guards']}.get(name, expected), name
    rejected = 0
    for name, snapshot in plan['rejected_native_before'].items():
        wrong = copy.deepcopy(plan)
        wrong['previous'][name] = snapshot
        data = (OVERLAY / snapshot).read_bytes()
        wrong['inputs'][name] = hashlib.sha256(data).hexdigest()
        try:
            native_input_contract(wrong)
        except AssertionError as error:
            assert 'Native13.2 input origin mismatch' in str(error)
            rejected += 1
        else:
            raise AssertionError('The original old-base input regression was accepted')
    assert rejected == 1
    wrong = copy.deepcopy(plan)
    wrong['native_inputs'].clear()
    try:
        native_input_contract(wrong)
    except AssertionError:
        rejected += 1
    else:
        raise AssertionError('Removing the native origin contract was accepted')
    print(f'PASS: both migration manifests, {len(plan["native_inputs"])} native13.2 git blobs; {rejected} origin regressions rejected')


if __name__ == '__main__':
    main()
