# Offline and unavailable-proxy startup

NagramiX must start without blocking the application UI when the device has no
network or the selected proxy is unavailable. Waiting-for-network state does
not trigger proxy rotation. DNS and proxy checks remain on background/native
network queues, and reconnection stays under Telegram's native connection
manager.

Compilation does not verify this behavior. Airplane Mode, offline launch,
unavailable proxy and network-restoration scenarios require a physical device.
