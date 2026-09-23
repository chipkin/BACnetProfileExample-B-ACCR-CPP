# AGENTS.md

Guidance for AI coding agents working in this repository. See
<https://agents.md/> for the format. Human contributors should read
[README.md](README.md) first, then [TUTORIAL.md](TUTORIAL.md).

## What this project is

A **tutorial** C++ example that implements the BACnet **B-ACCR (Access Control
Credential Reader)** device profile using the CAS BACnet Stack. It is one of a
series - one git repo per BACnet profile - and builds on the B-SS (Smart
Sensor) example by adding WriteProperty (DS-WP-B), SubscribeCOV (DS-COV-B),
and a Credential Data Input object (DS-ACCDI-B). It is the series' canonical
source for the SubscribeCOV pattern (F-COV) - if you are implementing COV in
another example, copy this repo's approach. The top priority is that the code
reads like a tutorial a customer can learn from and copy-paste. Favour clarity
over cleverness.

## Layout

This repository is self-contained:

- `main.cpp` - the example device.
- `common/` - the shared helper (vendored).
- `README.md` - what this example is. Keep it short and about THIS example only.
- `TUTORIAL.md` - how to extend and review the example (including the F-COV
  SubscribeCOV pattern). Long-form material that would bloat the README
  belongs here.
- `docs/PICS.md` - the Protocol Implementation Conformance Statement. Its
  objects-and-properties section is GENERATED from `docs/objects.json`; do not
  hand-edit between the `OBJECTS-PROPERTIES` markers.
- `docs/objects.json` - the input to that generator. Update it in the same change
  as any `main.cpp` change that adds an object or a `GetProperty*` branch.
- `submodules/cas-bacnet-stack/` - the **CAS BACnet Stack** as a git submodule
  (private; compiled from source). After cloning, run
  `git submodule update --init --recursive`.

The `PROFILE-TABLE` block in README.md is also generated, from the example-series
repository's `docs/profile-table.md`. Edit it there, not here.

## Build

Plain CMake, identical on every platform, in the adapter's default SOURCE mode
(the stack's sources are compiled into the executable - no prebuilt library, no
DLL, no per-platform pre-step):

```bash
git submodule update --init --recursive   # once, if not cloned with --recursive
cmake -B build -S .
cmake --build build --config Release
```

The first build compiles the whole stack (~600 files) and takes a few minutes;
rebuilds after that are incremental and fast. Use `-D CAS_STACK_DIR=...` only if
your stack lives outside the bundled submodule. Do not reintroduce a link-mode
flag or a series-root build script into the documented build: a customer
downloads this repository on its own and must be able to build it with the two
commands above.

## Run

```bash
./build/BACnetExampleBACCR [--port 47808] [--deviceID 389012]   # Linux/macOS
.\build\Release\BACnetExampleBACCR.exe [--port 47808] [--deviceID 389012]   # Windows
```

Interactive keys while running: `h` help, `q` quit, up/down nudge Analog Input 1
AND simulate a new credential presentation on Credential Data Input 1 - both
fire a COV notification to any subscriber (see "The F-COV pattern" below).

## Conventions

- Device is named "Chipkin Example B-ACCR"; objects use the series' colour names; vendor id 389.
- Implement **only** the services and objects the B-ACCR profile requires - but
  expose **every required property** of each object for Protocol_Revision 24.
- **The F-COV pattern** (this repo is canonical for it): call
  `BACnetStack_SetPropertySubscribable` on the property a client will watch,
  bound the subscription table with `BACnetStack_SetCOVSettings`, enable the
  `SubscribeCOV` service, and call `BACnetStack_UpdateValue` every time the
  application changes a subscribable value so the stack evaluates and fires
  notifications. See the comment block above the calls in `main()`.
- Credential Data Input's `Present_Value` is `BACnetAuthenticationFactor`, a
  constructed type - the stack serves it by wrapping the application's
  `GetPropertyOctetString` callback's raw bytes (format-type/class come back
  as the stack-side default `0`). `Supported_Formats` needs its own dedicated
  callback (`RegisterCallbackGetPropertyAuthenticationFactorFormat`);
  `Update_Time` is wrapped from the existing Time callback. None of this is a
  gap - it is a verified customer-DLL capability (stack PRs #166/#167).
- Match the surrounding code style: `const`-correct parameters, check every stack
  return value, keep `main.cpp` linear and well-commented.
- **Never edit `common/` in this repo alone** - it is a vendored copy shared by
  every example in the series, with its own version (`COMMON_VERSION`) and
  changelog (`common/CHANGELOG.md`). To change it: edit, bump the version, add
  a changelog entry, then re-copy `common/` into every example repository.

## How to verify a change

There are no unit tests; verification is behavioural:

1. Build, then run one instance on a clear UDP port.
2. With a BACnet client (e.g. the CAS BACnet Explorer, or `bacpypes3`/`BAC0`),
   send **Who-Is** and confirm **I-Am** from the device instance.
3. **ReadProperty** every required property of every object and confirm the
   values; confirm `Protocol_Revision` is 24 and `Object_List` lists all objects.
4. **SubscribeCOV** (confirmed and unconfirmed) on Analog Input 1; press up/down
   and confirm a notification arrives carrying `Present_Value` and
   `Status_Flags`; let the subscription's lifetime elapse and confirm it
   expires. **SubscribeCOV** on Credential Data Input 1 and confirm the
   *initial* notification carries `Present_Value` and `Update_Time`.
5. **WriteProperty** `Out_Of_Service` on each input-family object and confirm
   it is accepted and reads back; confirm a write to any other property is
   rejected.
6. If you changed the objects or their properties, regenerate `docs/PICS.md`
   (`python tools/gen-objects-properties.py BACnetProfileExample-B-ACCR-CPP` from
   the series root) and confirm no row comes out flagged with ⚠.

## Releasing

Bump `APP_VERSION` in `main.cpp` and add an entry to [CHANGELOG.md](CHANGELOG.md),
then tag `vX.Y.Z`. The GitHub Actions workflow builds and publishes the release.

## License

See [LICENSE](LICENSE). The CAS BACnet Stack is a separate, commercially
licensed product and is not covered by it.
