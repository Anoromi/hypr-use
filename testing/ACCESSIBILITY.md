# Zen accessibility diagnosis

The accessibility bus was available, but `org.a11y.Status.IsEnabled` was false. Zen was absent from a direct AT-SPI application enumeration. This was an activation problem, not lack of Firefox accessibility support or an observed PID-matching failure.

Setting IsEnabled to true enabled session accessibility. Background Zen still needed an activation event. Sending Escape through the portal initialized its accessibility support without switching the foreground application. A subsequent read-only get_app_state succeeded with appName Zen, PID 7890, and 500 real AT-SPI elements. The tree hit the existing record limit. T3 remained the foreground application on workspace 1 at the final check.

## Reproduce after a fresh session

From the project root:

```sh
python testing/probe-a11y.py
python testing/probe-a11y.py --enable
```

The second command sets the session-wide accessibility flag. It leaves ScreenReaderEnabled false and does not edit browser preferences or system configuration. If a running background browser does not register immediately, its next activation may be needed. In this test the portal's Escape key action was sufficient. Do not send arbitrary keys automatically when an application might have an active dialog.

The helper uses the saved live-session environment; refresh that environment after a compositor/session restart. Accessibility enablement was left on for the current session. No persistent startup configuration was added.

Evidence: `zen-timing/accessibility-fix.json`. Successful scans still have a 500-record limit, and this check does not validate the returned coordinates or AT-SPI mutation targeting.

Sources:
- https://wiki.freedesktop.org/www/Accessibility/AT-SPI2/ documents IsEnabled as the application accessibility activation signal.
- https://raw.githubusercontent.com/mozilla-firefox/firefox/main/accessible/atk/Platform.cpp handles IsEnabled changes and dispatches accessibility activation to a focused window. This supports the observed behavior; it is current upstream source, not a line-by-line verification of the installed Zen build.
