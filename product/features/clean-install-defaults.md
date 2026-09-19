# Clean-install language and appearance

## Product behavior

On a genuinely clean installation, before any account or application preference
exists, every welcome-carousel page and the primary start action are displayed
in Russian regardless of the iPhone language. Pressing the primary Russian
button downloads/applies Telegram's Russian localization before opening phone,
code, password and sign-up authorization screens.

The welcome screen may additionally show Telegram's native “Continue with …”
action for the language suggested from the iPhone locale (for example,
“Continue with English”). Choosing that alternative applies that language and
continues authorization in it. A Russian system suggestion is not duplicated
because Russian is already the primary flow. Existing language choices on an
upgrade are preserved.

A clean installation uses Telegram's built-in tinted dark theme
(`.nightAccent`, displayed as the dark variant) from the first presentation
frame, as the stored-settings fallback and as the default System night-switch
target. The black `.night` variant is not used by these defaults. Existing theme
choices on an upgrade are preserved; this default must not overwrite an
explicit user preference.

## Acceptance criteria

1. Delete the application and its data, set the iPhone language to English, and
   install the candidate: all carousel text and the main start button are
   Russian, while the alternative action offers English.
2. The Russian main action opens the phone/code/password flow in Russian; the
   English alternative opens it in English.
3. Repeat with Russian as the iPhone language: the welcome and authorization
   flow are Russian and no duplicate Russian alternative is shown.
4. In both cases the first frame, welcome flow and post-login UI use the tinted
   dark built-in theme until the user explicitly chooses another theme.
5. Upgrade an installation with explicit language/theme choices: those choices
   remain unchanged.

## Implementation

- iOS 0.2.8: exact-anchor overlay changes in TelegramPresentationData,
  TelegramUIPreferences, RMIntro and AuthorizationUI.
- iOS 0.2.9: replace Telegram's empty generated Russian application resource
  with a complete bundled fallback dictionary, translate every welcome key and
  validate those values both before compilation and inside the built `.app`.
- iOS 0.3.2: treat missing localization settings as genuinely missing so the
  Russian start action persists `ru` through Telegram's native localization
  pipeline, and change the System night-switch target from `.night` to
  `.nightAccent`.
