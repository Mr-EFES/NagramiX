# Profile information

NagramiX may display the numeric Telegram peer id in user, group and channel
profiles. The value must be copyable and copying must use the platform-native
confirmation UI.

For users, NagramiX may also display an explicitly approximate registration
year. Telegram does not expose the account creation timestamp; the estimate is
derived only from broad historic numeric user-id ranges and must never be
presented as an exact date:

| User id below | Approximate year |
| ---: | ---: |
| 10,000,000 | 2013 |
| 50,000,000 | 2014 |
| 150,000,000 | 2015 |
| 300,000,000 | 2016 |
| 500,000,000 | 2017 |
| 800,000,000 | 2018 |
| 1,100,000,000 | 2019 |
| 1,400,000,000 | 2020 |
| 1,700,000,000 | 2021 |
| 2,100,000,000 | 2022 |
| 4,000,000,000 | 2023 |
| 7,000,000,000 | 2024 |
| 10,000,000,000 | 2025 |

Higher ids use the current calendar year. A mutual-contact marker is displayed
only when Telegram's real mutual-contact field is true and the peer is not the
current user, a bot or a deleted account. The marker follows platform theme
coloring. All three behaviors respect their canonical settings immediately.
