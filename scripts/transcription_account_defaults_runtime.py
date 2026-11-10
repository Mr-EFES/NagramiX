"""Run actual settings, coordinator and full ASR runtime against explicit IO adapters."""
from pathlib import Path
from private_temporary_transcription_runtime import fixture as private_fixture
from validate_quick_format import block

ROOT = Path(__file__).resolve().parents[1]
ASR = 'submodules/NagramiXTranscription/Sources/'
ACCOUNT = 'submodules/TelegramUI/Sources/AccountContext.swift'
PREFS = ASR + 'Preferences.swift'


def fixture(source):
    code = private_fixture(source)
    before = 'final class Account{let network=Network();'
    assert code.count(before) == 1
    code = code.replace(before, 'final class Account{struct RecordId {var int64:Int64 = 1}; var id=RecordId();let network=Network();')
    code = code.replace('@main struct PrivateTemporaryTranscriptionTests', 'struct PrivateTemporaryTranscriptionTests')
    startup = block((source / ACCOUNT).read_text(), '            if let peer {')
    # Exact startup call and exact manual-choice transform from the UIKit caller.
    preferences = (source / PREFS).read_text()
    manual = next(line.strip() for line in preferences.splitlines() if 'NagramiXTranscriptionSettings.update {' in line and '$0.provider = provider;' in line)
    # Same-file extension exposes a queue barrier only to the fixture, keeping
    # deterministic ordering without timing sleeps or changing production jobs.
    code += '\nextension NagramiXTranscriptionCoordinator {func flushForDefaults() {self.queue.sync {}}}\n'
    code += '\nstruct StartupPeer {let isPremium:Bool}\nfunc observeAccount(_ account:Account, peer:StartupPeer?) {\n' + startup + '\n}\n'
    code += 'func chooseProvider(_ provider:NagramiXTranscriptionProvider) {\n' + manual + '\n}\n'
    return code + (ROOT / 'scripts/tests/NagramiXTranscriptionAccountDefaultsTests.swift').read_text()


def negatives(code):
    variants = [
        ('fresh-disabled', 'var enabled = true', 'var enabled = false', 'fresh master is enabled'),
        ('automatic-on', 'var automatic = false', 'var automatic = true', 'fresh automatic stays opt-in'),
        ('premium-inverted', 'isPremium ? .telegram : .apple', 'isPremium ? .apple : .telegram', 'known Premium selects Telegram'),
        ('shared-account-key', '"nagramix.transcription.account-default.v1." + String(accountId)', '"nagramix.transcription.account-default.v1."', 'second account does not overwrite Premium default'),
        ('legacy-overwrite', 'if value.usesAccountDefaultProvider == true {', 'if value.usesAccountDefaultProvider != false {', 'legacy provider and OFF survive'),
        ('manual-same-apple', '$0.usesAccountDefaultProvider = false; $0.provider = provider;', '$0.provider = provider;', 'explicit same-value Apple freezes choice'),
        ('runtime-global-provider', 'context.map { NagramiXTranscriptionSettings.configuration(accountId: $0.account.id.int64) } ?? NagramiXTranscriptionSettings.current', 'NagramiXTranscriptionSettings.current', 'Premium runtime uses native Telegram'),
        ('coordinator-global-revision', 'NagramiXTranscriptionSettings.configuration(matching: configuration).revision == configuration.revision', 'NagramiXTranscriptionSettings.current.revision == configuration.revision', 'scoped coordinator starts'),
        ('coordinator-cancels-all', 'NagramiXTranscriptionSettings.configuration(matching: job.configuration)', 'NagramiXTranscriptionSettings.current', 'other account change leaves active job'),
    ]
    for name, before, after, diagnostic in variants:
        assert code.count(before) == 1, (name, code.count(before))
        yield name, code.replace(before, after, 1), diagnostic
