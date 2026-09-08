# DNS provider and custom DoH

NagramiX lets the user choose the system resolver, Google, Quad9, AdGuard,
Mullvad, Cloudflare, or a custom DNS-over-HTTPS endpoint. Provider meanings and
endpoints are identical on both platforms. Persisted identifiers are
platform-native implementation details and are not shared across installations.

DoH uses RFC 8484 POST requests with `application/dns-message`. A records are
attempted first and AAAA records second. Requests use finite connection and
read timeouts, reject malformed DNS replies, and never silently leak a failed
DoH lookup to the system resolver. Native connection retry remains responsible
for recovery.

A custom endpoint must be HTTPS, have a host, contain no spaces, and answer a
real lookup before it is persisted. Changing the provider clears the process
DNS result cache. Existing system-DNS behavior is preserved when `system` is
selected.
