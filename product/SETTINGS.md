# Canonical NagramiX settings contract

Platform storage mechanisms differ, but ids, defaults and user-visible meaning should remain aligned. Existing persisted platform keys must not be renamed without a migration.

| Canonical id | Default | Category | Meaning |
| --- | --- | --- | --- |
| `interface.hideContactsTab` | `true` | Interface / Tabs | Hide the Contacts tab. |
| `interface.hideCallsTab` | `true` | Interface / Tabs | Hide the Calls tab where the platform exposes it. |
| `interface.showTabTitles` | `true` | Interface / Tabs | Show tab labels. |
| `interface.showSearchTab` | `false` | Interface / Tabs | Show a separate Search tab/button. |
| `interface.hideStories` | `false` | Features / Stories | Hide the stories strip. |
| `videoMessages.useRearCamera` | `false` | Features / Video messages | Start the next round-video recorder with the rear camera. |
| `stories.disableCameraSwipe` | `false` | Features / Stories | Disable the gesture that starts story recording. |
| `stories.confirmViewing` | `false` | Features / Stories | Confirm before opening each unseen story. |
| `stories.enableRepost` | `false` | Features / Stories | Expose the native story repost action. |
| `calls.confirmOutgoing` | `true` | Features / Calls | Confirm before starting an outgoing call. |
| `calls.forceTcp` | `false` | Other / Calls | Force supported voice/video call transports to TCP. |
| `messages.showDeletedMessages` | `false` | Features / Messages | Show locally captured incoming messages after deletion, subject to exclusions. |
| `messages.editHistory` | `false` | Features / Messages | Preserve and display revisions actually observed by this client. |
| `profiles.showId` | `true` | Interface / Profiles | Show the numeric peer id. |
| `profiles.showRegistrationDate` | `true` | Interface / Profiles | Show an explicitly approximate registration date. |
| `profiles.showMutualContactIcon` | `false` | Interface / Profiles | Mark real mutual contacts. |
| `network.dnsProvider` | `system` | Other / Network | Choose system or an approved DoH provider. |
| `network.customDohUrl` | empty | Other / Network | HTTPS URL used only for the custom DoH provider. |
| `network.proxyAutoSwitchEnabled` | `false` | Other / Proxy | Enable automatic failover among saved proxies. |
| `network.proxyAutoSwitchTimeout` | `15` | Other / Proxy | Failover delay in seconds; allowed values are 15, 30 and 60. |
| `network.showProxyButton` | `true` | Other / Proxy | Keep the proxy control visible in chats. |
| `network.hideProxySponsorChannel` | `true` | Other / Proxy | Hide proxy sponsor channel content. |

Archive, network and call settings require explicit platform specifications before an Android row can become Implemented. Similar upstream debug flags are not substitutes for NagramiX-owned settings.
