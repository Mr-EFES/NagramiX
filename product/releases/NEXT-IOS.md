# Next NagramiX iOS build

## Confirmed contents

The next iPhone build from `main` contains the 14 source-implemented and previously compile-verified NagramiX 0.2.6 feature groups:

1. tab visibility, labels and search controls;
2. eight application icons;
3. front/rear round-video camera selection;
4. story visibility, confirmation and repost controls;
5. forward with source and Copy as New without source;
6. experimental local deleted-message archive;
7. experimental locally observed edit history;
8. DNS provider selection and custom DNS-over-HTTPS;
9. proxy checking, visibility controls and automatic failover;
10. Force TCP for calls;
11. profile ID, approximate registration year and mutual-contact marker;
12. offline and unavailable-proxy startup hardening;
13. adaptive wide broadcast-channel posts;
14. paginated Select From Author.

## Still required

- Rebuild the unsigned ARM64 IPA from the final `main` commit and retain its provenance and checksum.
- Test every feature above on a physical iPhone, including clean install, upgrade, relaunch and offline/proxy scenarios; compilation is not device acceptance.
- Reconcile the owner's requests that are absent from the current product specifications. No unrecorded request is promised for the next build until it has an explicit specification and registry entry.
- Record failures individually, fix them on iOS first and repeat build/device verification before calling the build ready.

## Platform sequencing

iOS is the only active implementation target. Android sources remain preserved but Android feature work, builds and device acceptance are paused. Android parity resumes only after the corresponding iOS behavior is specified, implemented and accepted.
