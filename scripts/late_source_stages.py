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
    'temporary_message_interaction',
    'account_settings_entry',
    'release_090_preflight_fixes',
    'release_090_author_compile',
    'round_video_replay_stability',
    'pip_gallery_placeholder',
)
TEMPORARY_INTERACTION_STAGE = 'temporary_message_interaction'
TEMPORARY_REPLY_HELPER = 'submodules/TelegramUI/Sources/Chat/NagramiXTemporaryReplySend.swift'
TEMPORARY_REPLY_BUILD = 'submodules/TelegramUI/BUILD'
TEMPORARY_REPLY_BUILD_SHA = 'c819263cd1c2d6407308fe3f172f9f564b40e26f3b688da39739577bae792f52'


def copy_outputs(plan):
    return {name: item['sha256'] for name, item in plan['copies'].items()}


def check_copy_contract(stage, plan):
    """Only stage nine may introduce the one source covered by the native glob."""
    assert not plan['deletions'], stage
    index = LATE_SOURCE_STAGES.index(stage)
    if index >= 7:
        assert plan.get('required_previous_stage') == LATE_SOURCE_STAGES[index - 1], stage
    if stage != TEMPORARY_INTERACTION_STAGE:
        assert not plan['copies'], stage
        return
    assert plan['required_previous_stage'] == 'pip_swipe_handoff', stage
    assert set(plan['copies']) == {TEMPORARY_REPLY_HELPER}, 'Unexpected temporary interaction copy'
    assert plan['guards'].get(TEMPORARY_REPLY_BUILD) == TEMPORARY_REPLY_BUILD_SHA, 'Temporary reply helper lacks exact BUILD glob guard'
    item = plan['copies'][TEMPORARY_REPLY_HELPER]
    assert set(item) == {'source', 'sha256'}, 'Invalid temporary reply copy record'
    assert plan['templates'].get(item['source']) == item['sha256'], 'Temporary reply copy template is not pinned'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_late_plans():
    # Lazy import: the final release validator also consumes this stage list.
    from validate_upstream_13_2_release import checked_plan
    plans = [checked_plan(stage) for stage in LATE_SOURCE_STAGES]
    for stage, plan in zip(LATE_SOURCE_STAGES, plans):
        check_copy_contract(stage, plan)
    return plans


def verified_prefix(source, plans=None):
    """Recognize an exact checkpoint, then verify the whole prefix, not one ID."""
    plans = checked_late_plans() if plans is None else plans
    count = 0
    for index in range(len(plans) - 1, -1, -1):
        outputs = {**plans[index]['outputs'], **copy_outputs(plans[index])}
        if outputs and all((source / name).is_file()
                           and digest((source / name).read_bytes()) == value
                           for name, value in outputs.items()):
            count = index + 1
            break
    if not count:
        for plan in plans:
            for name in plan['copies']:
                assert not (source / name).exists() and not (source / name).is_symlink(), 'Helper exists without its source stage: ' + name
        return 0
    expected = {}
    for plan in plans[:count]:
        for name, value in {**plan['inputs'], **plan['guards']}.items():
            if name in expected:
                assert expected[name] == value, 'Broken late source chain: ' + name
        expected.update(plan['guards'])
        expected.update(plan['outputs'])
        expected.update(copy_outputs(plan))
    for name, value in expected.items():
        assert (source / name).is_file() and digest((source / name).read_bytes()) == value, 'Late source checkpoint differs: ' + name
    for plan in plans[:count]:
        for name in plan['copies']:
            assert not (source / name).is_symlink(), 'Copied helper is not a regular source: ' + name
    for plan in plans[count:]:
        for name in plan['copies']:
            assert not (source / name).exists() and not (source / name).is_symlink(), 'Future helper exists before its source stage: ' + name
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
    removed = set()

    def data(name):
        assert name not in removed, 'Historical source unexpectedly depends on a removed helper: ' + name
        return overrides[name] if name in overrides else (source / name).read_bytes()

    for index in range(count - 1, stop - 1, -1):
        plan = plans[index]
        for name, value in {**plan['outputs'], **plan['guards'], **copy_outputs(plan)}.items():
            assert digest(data(name)) == value, 'Cannot reverse ' + LATE_SOURCE_STAGES[index] + ': ' + name
        removed.update(plan['copies'])
        for name, template in plan['previous'].items():
            previous = (OVERLAY / template).read_bytes()
            assert digest(previous) == plan['inputs'][name], name
            overrides[name] = previous
    with tempfile.TemporaryDirectory(prefix='nagramix-late-source-prior-') as temporary:
        prior = Path(temporary)
        for name in validation_names():
            if name in removed:
                continue
            path = source / name
            if name in overrides or path.is_file():
                target = prior / name
                assert target.resolve().is_relative_to(prior.resolve()), name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data(name))
        for name, previous in overrides.items():
            assert (prior / name).read_bytes() == previous, name
        for name in removed:
            assert not (prior / name).exists() and not (prior / name).is_symlink(), name
        yield prior
