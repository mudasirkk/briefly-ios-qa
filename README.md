# briefly-ios-qa

iOS QA harness for the Briefly app. Runs Expo Go (SDK 54) in an iOS Simulator
on a GitHub Actions macOS runner, loads the published EAS `preview` update,
and drives it with [Maestro](https://maestro.mobile.dev) flows. Each run
uploads a full session video, screenshots, and Maestro debug output as
artifacts.

No app source lives here — the app is loaded at runtime from its EAS update
channel.

## Run

```
gh workflow run "iOS QA" -f flow=flows/smoke.yaml
```

Flows live in `flows/`. Login flows read `TEST_EMAIL` / `TEST_PASSWORD` from
repo secrets.
