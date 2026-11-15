# Source and license notices

CloneDirector is licensed under **AGPL-3.0-only**; see `LICENSE`.

Starting points required by `SPEC.md` section 4.2:

- **CS2-Smarter-Bot**, ed0ard and contributors, AGPL-3.0:
  <https://github.com/ed0ard/CS2-Smarter-Bot/tree/ae672d36ab3ba0717bc921187d0aa44786b8a864>.
  `CloneDirector.csproj` adapts `BotState.csproj`. Plugin registration, round/spawn event handling,
  and lifecycle cleanup follow `BotState.Lifecycle.cs`. Bot-specific combat and movement code
  from that project is not copied. Its full AGPL license text is retained in `LICENSE`.
- **CS2-Bot-Controller**, XBribo and contributors, AGPL-3.0-only:
  <https://github.com/XBribo/CS2-Bot-Controller/tree/465fc0e3b0f663f08de935fc1dd069b34aa3f987>.
  Capability discovery follows `TECH.md`. `Core/Playback.cs` adapts the recording model, strict
  field checks, serializer options, and Brotli loader from
  `csharp/BotControllerImpl/MotionRecording.cs`. Changes: only loading is retained; added checks
  for format version, 64-tick recordings, nonempty buffers, and matching subtick counts. No native
  provider code or binaries are redistributed. The game supplies `BotControllerApi.dll` from
  the same release as its native controller and provider.

The glue that reads this project's clone profile, chooses routes, tracks sessions, and responds
to game events is new code built on those starting points. Neither upstream implements this
project's clone profile format or route selection policy.
