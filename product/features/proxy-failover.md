# Proxy visibility and failover

NagramiX can keep the proxy entry visible while proxy use is disabled, hide a
proxy-sponsored promo dialog, and automatically switch from an unavailable
selected proxy to another saved proxy after the configured delay. Supported
delays are 5, 10, 15, 30 and 60 seconds; the default is 15 seconds.

Connectivity checks must use each platform's native Telegram proxy-check path.
Waiting for network is not a proxy failure. A manual proxy selection cancels a
pending automatic decision, and proxy credentials must never be logged.
