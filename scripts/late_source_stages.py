"""Exact, reversible source-only stages after the published Telegram 13.2 tree.

This is a validation bridge, not an application migration or an SDK build.
Historical runtime fixtures receive their original bytes only after every
intervening stage's output, guard and template has been verified.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'ios'
LATE_SOURCE_STAGES = (
    'wide_bottom_bar',
    'author_selection_no_restore',
    'preview_reply_intent',
    'cloud_credential_entry',
    'extended_poll_integrity',
    'bot_delete_without_block',
    'wide_tab_bar_setting',
    'pip_swipe_handoff',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_late_plans():
    # Lazy import: the final release validator also consumes this stage list.
    from validate_upstream_13_2_release import checked_plan
    plans = [checked_plan(stage) for stage in LATE_SOURCE_STAGES]
    for stage, plan in zip(LATE_SOURCE_STAGES, plans):
        assert not plan['copies'] and not plan['deletions'], stage
    assert plans[-1]['required_previous_stage'] == LATE_SOURCE_STAGES[-2]
    return plans


def verified_prefix(source, plans=None):
    """Recognize an exact checkpoint, then verify the whole prefix, not one ID."""
    plans = checked_late_plans() if plans is None else plans
    count = 0
    for index in range(len(plans) - 1, -1, -1):
        outputs = plans[index]['outputs']
        if outputs and all((source / name).is_file()
                           and digest((source / name).read_bytes()) == value
                           for name, value in outputs.items()):
            count = index + 1
            break
    if not count:
        return 0
    expected = {}
    for plan in plans[:count]:
        for name, value in {**plan['inputs'], **plan['guards']}.items():
            if name in expected:
                assert expected[name] == value, 'Broken late source chain: ' + name
        expected.update(plan['guards'])
        expected.update(plan['outputs'])
    for name, value in expected.items():
        assert (source / name).is_file() and digest((source / name).read_bytes()) == value, 'Late source checkpoint differs: ' + name
    return count


def validation_names():
    """The existing historical suite's sparse file boundary, including new paths."""
    names = set()
    for path in OVERLAY.glob('*_patches.json'):
        plan = json.loads(path.read_text())
        for field in ('inputs', 'outputs', 'guards', 'copies'):
            names.update(plan.get(field, {}))
    names.update(json.loads((OVERLAY / 'upstream_13_1_manifest.json').read_text())['files'])
    names.update((
        'Telegram/Telegram-iOS/en.lproj/Localizable.strings',
        'submodules/TelegramPresentationData/Sources/PresentationData.swift',
        'submodules/GalleryUI/Sources/ZoomableContentGalleryItemNode.swift',
    ))
    return names


@contextmanager
def historical_source(source, before_stage=None):
    """Yield a verified inverse checkpoint without writing to the actual source.

    With no stage, unwind all applied late stages to the published boundary.
    before_stage permits a newer validator to inspect its exact input boundary.
    This sparse tree is solely for source fixtures, never an application build.
    """
    source = Path(source)
    plans = checked_late_plans()
    count = verified_prefix(source, plans)
    stop = 0 if before_stage is None else LATE_SOURCE_STAGES.index(before_stage)
    assert stop <= count, 'Requested source checkpoint is not applied'
    if count == stop:
        yield source
        return
    overrides = {}

    def data(name):
        return overrides[name] if name in overrides else (source / name).read_bytes()

    for index in range(count - 1, stop - 1, -1):
        plan = plans[index]
        for name, value in {**plan['outputs'], **plan['guards']}.items():
            assert digest(data(name)) == value, 'Cannot reverse ' + LATE_SOURCE_STAGES[index] + ': ' + name
        for name, template in plan['previous'].items():
            previous = (OVERLAY / template).read_bytes()
            assert digest(previous) == plan['inputs'][name], name
            overrides[name] = previous
    with tempfile.TemporaryDirectory(prefix='nagramix-late-source-prior-') as temporary:
        prior = Path(temporary)
        for name in validation_names():
            path = source / name
            if name in overrides or path.is_file():
                target = prior / name
                assert target.resolve().is_relative_to(prior.resolve()), name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data(name))
        for name, previous in overrides.items():
            assert (prior / name).read_bytes() == previous, name
        yield prior
