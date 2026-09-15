# BACnet B-ACCR (Access Control Credential Reader) - C++ example

A minimal, copy-paste-friendly example showing how to implement the BACnet
**B-ACCR (Access Control Credential Reader)** device profile in C++ using the
[CAS BACnet Stack](https://store.chipkin.com/services/stacks/bacnet-stack).
It listens on **BACnet/IP (UDP 47808)**, answers **ReadProperty** and
**WriteProperty** requests, is discoverable via **Who-Is / I-Am**, and pushes
its credential and sensor readings to subscribers with **SubscribeCOV**
instead of making every client poll.

Part of the CAS BACnet Stack **BACnet profile example series** - one repository
per BACnet device profile. This example claims **only** B-ACCR, and is the
series' **canonical source for the SubscribeCOV pattern (F-COV)** - if you are
adding COV to a later example, start from this one.

Reading order: [B-SS (Smart Sensor)](https://github.com/chipkin/BACnetProfileExample-B-SS-CPP) is the **first** example and the one to
start with.

> **Versions:** this document describes **example v1.0.0**, built and verified
> against **CAS BACnet Stack 6.0.21** (`6.x` @ `abd4cee1`), linked as a static
> library, at **Protocol_Revision 24**, with the vendored `common/` helper at
> **v2.5.0**. Running the example prints all three - if what it prints
> disagrees with this line, trust the program and check `CHANGELOG.md`.

## What is a B-ACCR (Access Control Credential Reader) profile?

A **device profile** is a standard "template" defined in Annex L of ANSI/ASHRAE
135. It lists the capabilities a class of device must support so that any
compliant client knows what to expect, and the BACnet Testing Laboratories (BTL)
certify devices against it. (New to BACnet in general? See Chipkin's
[What is BACnet?](https://docs.chipkin.com/protocols/bacnet/) guide.)

**B-ACCR (Access Control Credential Reader)** is a Miscellaneous profile
(Annex L.7): a device - typically a card/badge reader at a door - that reports
the credential most recently presented, and **pushes** that report to
subscribers rather than requiring them to poll. It requires no alarming,
scheduling, or trending; its one distinguishing object is **Credential Data
Input**.

**What the profile requires:**

- **Data Sharing - ReadProperty - B side (DS-RP-B):** the device must answer
  **ReadProperty** requests for the values of its objects.
- **Data Sharing - WriteProperty - B side (DS-WP-B):** the device must accept
  **WriteProperty** requests.
- **Data Sharing - COV - B side (DS-COV-B):** the device must execute
  **SubscribeCOV**, and send **ConfirmedCOVNotification** /
  **UnconfirmedCOVNotification** when a subscribed property changes. This is
  what distinguishes a B-ACCR from a plain B-SS: instead of a client polling
  for the latest card read, it subscribes once and gets pushed every change.
- **Data Sharing - Access Credential Data Input - B side (DS-ACCDI-B):** the
  device must present a **Credential Data Input** object reporting the last
  credential read.
- **Discovery:** the device must be findable, so it answers **Who-Is** with
  **I-Am**, and announces itself with an unsolicited I-Am at start-up.

**What the profile does NOT require** - and this example therefore omits on
purpose: **alarming / event reporting**, **scheduling**, **trending**, and
**ReadPropertyMultiple / WritePropertyMultiple**.

**But it is still a full BACnet device.** Even a simple profile must present the
standard object model - a **Device** object, a **Network Port** object (every
device needs one), and its objects - and each object must expose all of its
**required properties**. The CAS BACnet Stack generates most of those
automatically (Object_Identifier, Object_Type, Status_Flags,
Object_List, Protocol_*, ...); this example supplies the handful that are
application-specific. The result is conformant for **Protocol_Revision 24**.

## SubscribeCOV (the heart of B-ACCR, and the series' F-COV pattern)

Instead of a client re-reading `Present_Value` on a timer, it **subscribes
once** and the device pushes a notification every time the value changes -
lower latency, lower network load, and (per the standard) an **initial
notification** the moment the subscription is confirmed, so the client always
starts from a known value.

Three pieces make this work, all visible in `main.cpp`:

1. **`BACnetStack_SetPropertySubscribable`** - per object, on the property a
   plain SubscribeCOV actually monitors for that object type. For Analog
   Input 1 that is `Present_Value`, as it is for most object types. **For
   Credential Data Input it is `Update_Time`, not `Present_Value`** - a plain
   SubscribeCOV does not let the client choose a property, the *server*
   decides per object type (135-2024 Table 13-1), and the stack's own
   `BACnetSubscribeCOVProcessor::GetSubscriptionProperty()` names
   `Update_Time` for this object type specifically. Subscribing to the wrong
   property compiles and returns `true` from the setup call, but every
   client's SubscribeCOV then fails with `Error(subscribe-cov): property:
   not-cov-property` - confirmed on the wire while building this example (see
   `CHANGELOG.md`). The notification payload is unaffected by this
   distinction: it still carries `Present_Value` - `Update_Time` is only the
   trigger condition, not the only field delivered.
2. **`BACnetStack_SetCOVSettings`** - bounds the device's subscription table:
   how many active subscriptions it holds (0 = no limit here) and the longest
   lifetime it grants one (28,800 seconds / 8 hours, the stack's own default).
3. **`BACnetStack_UpdateValue`** - called every time the application changes a
   subscribable value (the up/down keys, here), so the stack evaluates active
   COV subscriptions on that property and fires a notification if anyone is
   subscribed. Skipping this call is the single most common way to build a
   device that *looks* COV-capable (the service is enabled, the property is
   subscribed) but never actually notifies.

## Credential Data Input's Present_Value is not a scalar

Clause 12.36 types `Present_Value` as **`BACnetAuthenticationFactor`**, a
SEQUENCE of `{format-type, format-class, value [OCTET STRING]}` - the first
object type in this series whose defining property isn't a plain number,
enumeration, or string.

The CAS BACnet Stack serves it by **wrapping the application's existing
OctetString callback**: register the credential's raw bytes there (this
example uses a 4-byte "simple-number32" card ID) and the stack assembles the
SEQUENCE around them - `format-type` / `format-class` come back as the
stack-side default `0`. This is a real, verified customer-DLL capability
(stack PRs #166 and #167), not a gap - `TODO.md` has nothing to report.

Two more required properties need their own explanation:

- **`Supported_Formats`** is a *different* constructed type
  (`BACnetAuthenticationFactorFormat`, an ARRAY) and needs its own dedicated
  callback, `RegisterCallbackGetPropertyAuthenticationFactorFormat`, because -
  unlike the one-field `AuthenticationFactor` above - it carries three
  independently-meaningful fields no single primitive callback can express.
- **`Update_Time`** is `BACnetTimeStamp`-typed. The stack wraps it from the
  application's existing **Time** callback - no dedicated callback needed.
  This is exactly the piece that used to make a CDI's *initial* COV
  notification incomplete; it is closed at this pin.

## The device this example creates

```
Device 389012  "Rainbow"   (Vendor 389 - Chipkin Automation Systems)
    │
    ├── Analog Input  1            "Bronze"   Present_Value  21.5    (REAL, degrees Celsius; read-only; COV-subscribable)
    ├── Binary Input  1            "Emerald"  Present_Value  inactive  (0 = inactive / 1 = active; read-only)
    ├── Multi-State Input 1        "Hot Pink" Present_Value  1       (state, 1..3; read-only)
    ├── Credential Data Input 1    "Flax"     Present_Value  (card 0x00A1B2C3)  (AuthenticationFactor; read-only; Update_Time COV-subscribable)
    └── Network Port 1             "Vermilion" the BACnet/IP port    (required on every device)
```

The three **input** objects (Bronze, Emerald, Hot Pink) are the shared minimum
every example in this series carries. **Credential Data Input 1 (Flax)** is the
B-ACCR addition - the object that makes this a credential reader. Object names
follow this series' colour-naming convention (Device is always "Rainbow").

## What this example supports

The example implements exactly the capabilities below - and nothing more, which
is the point of a profile example. These capabilities satisfy the **B-ACCR
(Access Control Credential Reader)** profile; because this profile's BIBBs are
a superset of the **B-GENERAL** baseline, a conformant device necessarily
satisfies **B-GENERAL** too. That is subsumption, not a second claim: this
repository still claims exactly one profile.

### BIBBs (BACnet Interoperability Building Blocks)

| BIBB | Description | Supported |
|------|-------------|:---------:|
| DS-RP-B | Data Sharing - ReadProperty - B | ✅ |
| DS-WP-B | Data Sharing - WriteProperty - B | ✅ |
| DS-COV-B | Data Sharing - COV - B | ✅ |
| DS-ACCDI-B | Data Sharing - Access Credential Data Input - B | ✅ |
| DM-DDB-B | Device Management - Dynamic Device Binding - B | ✅ |
| DM-DOB-B | Device Management - Dynamic Object Binding - B | ✅ |

### Services (executed / B-side)

| Service | Notes |
|---------|-------|
| ReadProperty | Responds to property reads (DS-RP-B). |
| WriteProperty | Accepts writes to `Out_Of_Service` on the four input-family objects (DS-WP-B). |
| SubscribeCOV | Confirmed and unconfirmed subscriptions to Analog Input 1's `Present_Value` and Credential Data Input 1's `Update_Time` (DS-COV-B); both notifications carry `Present_Value`. |
| Who-Is / I-Am | Answers Who-Is with I-Am, and broadcasts an I-Am on start-up (DM-DDB-B). |
| Who-Has / I-Have | Answers Who-Has with I-Have (DM-DOB-B). |

### Object types

| Object type | Instance | Name | Access |
|-------------|:--------:|------|--------|
| Device | 389012 | Rainbow | - |
| Analog Input | 1 | Bronze | read-only; `Present_Value` COV-subscribable |
| Binary Input | 1 | Emerald | read-only |
| Multi-State Input | 1 | Hot Pink | read-only |
| Credential Data Input | 1 | Flax | read-only; `Update_Time` COV-subscribable (notification carries `Present_Value`) |
| Network Port | 1 | Vermilion | - |

`Out_Of_Service` is writable (DS-WP-B) on all four input-family objects above.

## Before you ship

This example is a tutorial, and it identifies itself as one. Everything in this
table is read by clients and shown to the operator in **every discovery tool on
the network**. Left as-is, your product appears on a real site announcing itself
as a Chipkin demo. None of it is cosmetic.

| Constant (`main.cpp`) | Ships as | Change it to |
|---|---|---|
| `VENDOR_IDENTIFIER` | `389` (Chipkin) | **Your** company's vendor ID. Assigned by ASHRAE, free: <https://bacnet.org/assigned-vendor-ids/> |
| `VENDOR_NAME` | `Chipkin Automation Systems` | Your company name — must match the vendor ID above. |
| `DEVICE_NAME` | `"Rainbow"` | Your device's `Object_Name`. **Must be unique across the BACnet internetwork** — see the note below. |
| `MODEL_NAME` | `CAS BACnet Stack Example - B-ACCR` | Your model designation. This is what a building operator reads to identify your device. |
| `DEVICE_DESCRIPTION` | a description of *this example* | What your device actually is. |
| `FIRMWARE_REVISION` / `APPLICATION_SOFTWARE_VERSION` | `1.0.0` | Your real versions — wire them to your build. |
| Device instance | `389012` (`--deviceID` overrides) | Must be unique on the internetwork. BACnet requires this to be configurable; keep it so. |

> **`Object_Name` uniqueness is the one that will bite you.** The device instance
> is runtime-configurable via `--deviceID`, but `DEVICE_NAME` is a compile-time
> constant. Ship two units and configure their instances correctly, and **both
> still announce `Object_Name "Rainbow"`** — a spec violation, and exactly the
> uniqueness problem the code comments warn about. In a real product,
> `Object_Name` must be per-unit configurable too (serial number, DIP switches,
> a config file, or a `--deviceName` argument).

`main.cpp` marks this block with a `CHANGE ALL OF THIS BEFORE YOU SHIP` banner.

## Requires the CAS BACnet Stack (licensed product)

This example **builds against the CAS BACnet Stack, which is a commercial Chipkin
product** - it is not free or open source, and there is no public/trial build.
The stack is referenced here as the **private** git submodule
`submodules/cas-bacnet-stack`; you can only fetch and build it once you have a CAS
BACnet Stack license and access to that repository.

**To get the CAS BACnet Stack (and access to build this example), contact
Chipkin:** <https://store.chipkin.com/services/stacks/bacnet-stack> or
sales@chipkin.com.

You do not need a stack licence to *read* this example. Every file outside
submodules/ is CC0 public domain, so once you have access to this repository you
can review the approach and the amount of code involved before you buy. The licence
is what lets you *build* it - that is the part the stack submodule gates.

## What's in this repository

This is a **self-contained** project. It ships:

- `main.cpp` - the example device.
- `common/` - the shared helper (UDP, callbacks, CLI, keyboard) vendored in.
- `submodules/cas-bacnet-stack/` - the **CAS BACnet Stack as a git submodule**
  (private; requires a license - see above). Built into a prebuilt **STATIC**
  library by the stack's own project files (`tools/build-stack-static.sh`),
  then linked - no DLL is shipped.

## Prerequisites

- A C++17 compiler (MSVC, GCC, or Clang).
- CMake >= 3.15.
- Git (to fetch the stack submodule).

### Windows

- **C++ compiler** - install
  [Visual Studio Community](https://visualstudio.microsoft.com/downloads/)
  (free) and select the **"Desktop development with C++"** workload.
- **CMake** - from <https://cmake.org/download/>, or `winget install Kitware.CMake`.

### Linux / macOS

- Debian/Ubuntu: `sudo apt install build-essential cmake git`
- macOS: `xcode-select --install` and `brew install cmake`

## Get the code

Clone this repository **and its submodule** (the CAS BACnet Stack):

```bash
git clone --recursive https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP.git
cd BACnetProfileExample-B-ACCR-CPP

# already cloned without --recursive? fetch the submodule:
git submodule update --init --recursive
```

## Build

This example links the CAS BACnet Stack as a prebuilt **STATIC** library. Build
the library once from the pinned submodule commit, then configure and build the
example against it:

```bash
tools/build-stack-static.sh BACnetProfileExample-B-ACCR-CPP   # from the series root; builds
                                                                # submodules/cas-bacnet-stack/bin/...
cmake -B build -S . -DCAS_BACNET_STACK_LINK=STATIC
cmake --build build --config Release
```

> **The stack library build takes a few minutes** the first time - it compiles
> the entire CAS BACnet Stack (~600 source files) once, via the stack's own
> project files (`msbuild` on Windows, `make` on Linux). The example itself
> (`main.cpp` + `common/`) then builds in seconds against that library, and
> rebuilds after that are incremental.

If your CAS BACnet Stack lives somewhere other than the bundled submodule, point
CMake at it: `cmake -B build -S . -D CAS_STACK_DIR=/path/to/cas-bacnet-stack`.

### Link mode

This example links the stack through the `CASBACnetStack::Adapter` CMake target
(`submodules/cas-bacnet-stack/adapters/cpp`) in **STATIC** mode -
`-DCAS_BACNET_STACK_LINK=STATIC` links the prebuilt
`CASBACnetStack_x64_Release.lib` / `libCASBACnetStack_x64_Release.a` built by
`tools/build-stack-static.sh` above. **Application code is identical
regardless of link mode** - `main.cpp` and `common/` call `BACnetStack_AddDevice(...)`
and friends by the exact export name. Every mode requires calling
`LoadBACnetFunctions()` once at the top of `main()` before any other
`BACnetStack_*` call, which runs a version handshake; if it fails,
`CASBACnetStackAdapter_LastError()` says why and the program exits with a
message rather than crashing.

The adapter also offers a **SOURCE** mode (compiles the stack's `source/*.cpp`
straight into the executable, no library build step) - this example is built
and published in **STATIC** mode only.

## Run

```bash
# Linux / macOS
./build/BACnetExampleBACCR

# Windows
.\build\Release\BACnetExampleBACCR.exe
```

Expected output:

```
BACnet B-ACCR (Access Control Credential Reader) Example - C++ v1.0.0
CAS BACnet Stack version: 6.0.21.0
Common helper (common/) version: 2.5.0
FYI: Listening for BACnet/IP on UDP port 47808 (Network Port 1).
TX 21 bytes to 192.168.3.255:47808 (broadcast) (Network Port 1)
FYI: Device 389012 ("Rainbow") ready. Vendor ID 389. Press 'h' for help.
```

The `TX` line is the start-up I-Am the device broadcasts to announce itself. It
goes to the **local subnet broadcast** address (here `192.168.3.255`, computed
from the Network Port's interface), not the global `255.255.255.255`. As clients
talk to the device you'll see `RX ... bytes from ...` and `TX ... bytes to ...`
lines showing the traffic; a WriteProperty prints a line such as
`WriteProperty: Analog Input 1 (Bronze) Out_Of_Service <- true`, and a
SubscribeCOV-driven notification is visible as outbound traffic to the
subscriber's address.

The device listens on UDP **47808** (BACnet/IP). Allow that port through your
firewall. To use a different port, pass `--port` (see below).

### Command-line options

| Option | Default | Meaning |
|--------|---------|---------|
| `--port <n>` | `47808` | UDP port to listen on (BACnet/IP). |
| `--deviceID <n>` | `389012` | The device's BACnet instance number (BACnet requires this to be configurable). |
| `--help`, `-h` | - | Show usage and exit. |
| `--version` | - | Print the example, stack, and `common/` helper versions, then exit. |

### Interactive commands

While the example runs, these keys are available (shared across all examples in
the series):

| Key | Action |
|-----|--------|
| `h` | Show the version information and this command list. |
| `q` | Quit. |
| up arrow | Increase Analog Input 1 (`Bronze`) by 1.1, **and** simulate a new card presented at Credential Data Input 1 (`Flax`) - both fire a COV notification to any subscriber. |
| down arrow | The same, decreasing. |

## Verify

Verified against a live BACnet client this repository's PR describes; use a
BACnet client such as the
[**CAS BACnet Explorer**](https://store.chipkin.com/products/tools/cas-bacnet-explorer)
or a scripted client (`bacpypes3` / `BAC0`):

1. **Discover** - send a **Who-Is**. The device replies with **I-Am** from
   instance **389012** (vendor **389**). It also broadcasts an I-Am at start-up.
2. **Browse the object model** - the device shows six objects: the Device
   (`Rainbow`), three base inputs, Credential Data Input (`Flax`), and the
   Network Port (`Vermilion`). Reading the Device's `Object_List` returns all six.
3. **Read the Device** - ReadProperty `389012` -> `Object_Name` returns
   `"Rainbow"`; `Protocol_Revision` returns `24`; `Description` returns the
   profile description string.
4. **Read Credential Data Input 1** - ReadProperty `Present_Value` returns the
   current card ID (an octet string); `Supported_Formats` returns one entry
   (`simple-number32`); `Update_Time` returns the wall-clock moment the card
   last changed; `Reliability` returns `no-fault-detected`.
5. **SubscribeCOV on Analog Input 1 (the F-COV test)** - subscribe (confirmed,
   then separately unconfirmed) to `Present_Value`. Confirm the **initial**
   notification arrives immediately, carrying `Present_Value` and
   `Status_Flags`. Press the up/down key on the running device; confirm a
   **change notification** arrives with the new value. Subscribe with a short
   lifetime and confirm the subscription **expires** when it elapses (a
   further value change produces no notification).
6. **SubscribeCOV on Credential Data Input 1** - subscribe to `Update_Time`
   (the property this object type's plain SubscribeCOV actually monitors -
   see "SubscribeCOV" above) and confirm the **initial** notification carries
   `Present_Value` **and** `Update_Time`. Press up/down again and confirm a
   change notification for the new card.
7. **WriteProperty** `Out_Of_Service` = `true` on Analog Input 1; re-read it
   back as `true`. **Confirm the profile boundary** - a WriteProperty to
   `Present_Value` (any object) is rejected: none of this profile's objects
   has a profile-writable `Present_Value`.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| On start-up the app prints a wall of red `Error:` lines but the device works | **Expected — this is not your bug.** Two benign sources, both from the stack's own debug logging: (1) the device receives its **own** broadcast I-Am and logs a decode cascade (*"Services is not supported service=[0]"* … *"Failed to process the incoming NPDU"*) — any BACnet/IP device that listens for broadcasts hears itself; (2) a one-time *"UUID has not been set. A UUID must be set for the BACnetSC device to start."* — the stack starts a BACnet/SC datalink these IP-only examples never configure. It appears once and does not spam. On a healthy start-up roughly half the output is these lines. |
| CMake error: *"CAS BACnet Stack adapter not found under: ..."* | Submodules not initialized. Run `git submodule update --init --recursive` (or pass `-D CAS_STACK_DIR=...`). |
| `CASBACnetStackDLL.h: No such file or directory` | Same - submodules not checked out. |
| Windows: *"No CMAKE_CXX_COMPILER could be found"* | Install Visual Studio with the "Desktop development with C++" workload, then re-run from a fresh terminal. |
| First build seems stuck for minutes | Normal - it's compiling ~600 stack files. Only the first build is slow. |
| App prints *"Failed to bind UDP port 47808"* | Another BACnet program is already using 47808. Stop it, or run with `--port <n>`. |
| SubscribeCOV to a property other than `Present_Value` on Analog Input 1, or other than `Update_Time` on Credential Data Input 1, is rejected with `not-cov-property` | Correct - a plain SubscribeCOV monitors exactly one property per object type, decided by the stack (135-2024 Table 13-1), not the client. |
| WriteProperty to `Present_Value` is rejected | Correct - no object in this profile has a profile-writable `Present_Value`. Only `Out_Of_Service` is writable, on the four input-family objects. |
| Client sends Who-Is but sees no I-Am | Firewall is blocking UDP 47808, or the client and device are on different subnets (Who-Is is a broadcast). Allow the port; test on the same subnet first. |
| Replies show an unexpected device instance or vendor | Another BACnet device is already answering on this host/port. On Linux/macOS two processes can share the port and both reply; on Windows the example asks for `SO_EXCLUSIVEADDRUSE` (`common/SimpleUDP.cpp`) so this shows up as a bind failure instead. Stop the other device, or use `--port`. |

## Extending the example

The example is intentionally small so it's easy to change.

**Change a value or name** - edit the constants / callbacks in `main.cpp` (e.g.
the initial `g_credentialValue`, or the `"Flax"` string in `GetPropertyCharString`).

**Add COV to a new property.** This is the series' reference pattern - follow
these three steps in order:

1. `BACnetStack_SetPropertySubscribable(deviceInstance, type, instance,
   propertyIdentifier, true)` once at start-up, after the property is
   enabled - **and `propertyIdentifier` must be the property that object
   TYPE'S plain SubscribeCOV actually monitors** (135-2024 Table 13-1;
   `Present_Value` for most types, `Update_Time` for Credential Data Input,
   `Access_Event_Time` for an Access Point). Get this wrong and setup still
   returns `true`, but every client's SubscribeCOV fails with
   `not-cov-property` - see "SubscribeCOV" above for how this example found
   that the hard way.
2. Confirm `BACnetStack_SetCOVSettings` has already been called once for the
   device (it has, in this example) - it is not per-property.
3. Every place the application changes that property's value, call
   `BACnetStack_UpdateValue(deviceInstance, type, instance,
   propertyIdentifier)` right after. **This is the step people forget**: the
   service can be enabled and the property subscribable, and a device that
   never calls `UpdateValue` will still never notify anyone.

> **Why a half-wired COV property fails silently.** SubscribeCOV itself still
> succeeds (the stack accepts the subscription and sends the *initial*
> notification, since that one is generated from the current value
> regardless). What is missing is every *subsequent* notification - and
> nothing on the wire says why. A scan tool sees "subscription accepted" and
> calls it healthy. Verify with the actual sequence in the "Verify" section
> above (press the key, confirm a **second** notification arrives), not just
> that the subscription was accepted.

### What each object type needs you to serve

| Object type | You must serve | Plus |
|---|---|---|
| Analog Input | `Present_Value` (Real), `Object_Name`, `Units` | subscribable `Present_Value` |
| Binary Input | `Present_Value` (Enumerated), `Object_Name` | `Polarity` |
| Multi-State Input | `Present_Value` (Unsigned), `Object_Name` | `Number_Of_States` |
| Credential Data Input | `Present_Value` (OctetString, wrapped as AuthenticationFactor), `Object_Name`, `Reliability` (Enumerated) | `Supported_Formats` (dedicated AuthenticationFactorFormat callback), `Update_Time` (Time callback; ALSO the subscribable property - see "SubscribeCOV" above) |

### Who serves what: the application or the stack?

For Credential Data Input 1, the whole picture:

| Property | Served by | How |
|---|---|---|
| `Object_Identifier` | **stack** | generated from the object you added |
| `Object_Type` | **stack** | generated |
| `Object_List` | **stack** | generated (Device object) |
| `Property_List` | **stack** | generated |
| `Status_Flags` | **stack** | generated |
| `Out_Of_Service` | **you** | `GetPropertyBool` / `SetPropertyBool` (writable) |
| `Present_Value` | **you** | `GetPropertyOctetString` - raw bytes; the stack wraps the `AuthenticationFactor` SEQUENCE around them |
| `Object_Name` | **you** | `GetPropertyCharString` |
| `Reliability` | **you** | `GetPropertyEnumerated` |
| `Supported_Formats` | **you** | `GetPropertyAuthenticationFactorFormat` (per element) + `GetPropertyUnsignedInteger` (array length, index 0) |
| `Update_Time` | **you** | `GetPropertyTime` - the stack wraps it into `BACnetTimeStamp` |

## Objects and properties

<!-- OBJECTS-PROPERTIES:BEGIN (generated by tools/gen-objects-properties.py from docs/objects.json - do not edit here) -->
Every object this example creates, and every REQUIRED property of each (per ANSI/ASHRAE 135-2024 clause 12 and the stack's `docs/property-profile-reference.md`), plus the optional properties the example turns on. **Served by** says who answers a ReadProperty: the **stack** generates it, or the **app** serves it from a `GetProperty*` callback in `main.cpp`. A ⚠ row is a required property the app does not serve and the stack would fill with a default - that is a defect, not a feature.

### Analog Input 1 "Bronze" - REAL, degrees Celsius; starts at 21.5; Present_Value COV-subscribable (F-COV canonical example)

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | Real | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Units | BACnetEngineeringUnits | app | no |

### Binary Input 1 "Emerald" - starts inactive

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | BACnetBinaryPV | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Polarity | BACnetPolarity | app | no |

### Multi-state Input 1 "Hot Pink" - state 1 of 3: On, Off, Auto

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | Unsigned | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Number_Of_States | Unsigned | app | no |
| State_Text *(optional, enabled)* | BACnetARRAY[N] of CharacterString | app | no |

### Credential Data Input 1 "Flax" - Present_Value is BACnetAuthenticationFactor (a 4-byte simple-number32 card ID, served via the OctetString callback - format-type/class default to 0 stack-side); Supported_Formats and Update_Time are REQUIRED (cl. 12.36) but not yet listed in the stack's property-profile-reference.md for this object type (a documentation gap, not a capability gap - both are served: Supported_Formats via RegisterCallbackGetPropertyAuthenticationFactorFormat, Update_Time via the existing Time callback wrapped into BACnetTimeStamp). Present_Value COV-subscribable (F-COV canonical example); the up/down keys simulate a new card presentation

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | BACnetAuthenticationFactor | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Reliability | BACnetReliability | app | no |
| Out_Of_Service | Boolean | app | yes |

### Network Port 1 "Vermilion" - BACnet/IP; Network_Type and Protocol_Level are set from BACnetStack_AddNetworkPortObject()'s arguments (IPv4, BACnet Application) at start-up, not a GetProperty callback like the object's other app-served rows; Changes_Pending is likewise computed and answered natively by the stack's Network Port object. Reliability has no fault condition this example detects, so it is accepted at the generic default (normal)

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Reliability | BACnetReliability | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | no |
| Network_Type | BACnetNetworkType | app | no |
| Protocol_Level | BACnetProtocolLevel | app | no |
| Changes_Pending | Boolean | app | no |

<!-- OBJECTS-PROPERTIES:END -->

## The BACnet profile example series

<!-- PROFILE-TABLE:BEGIN (generated from cas-bacnet-stack-examples/docs/profile-table.md - do not edit here) -->
The CAS BACnet Stack supports every standardized device profile in ASHRAE 135-2024 Annex L. One example repository per profile shows how. ✅ = the required BIBB (service) is supported by the CAS BACnet Stack; the **Example** column is the state of that profile's tutorial repository.

### Controllers (Annex L.4)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-SS** Smart Sensor | [B-SS-CPP](https://github.com/chipkin/BACnetProfileExample-B-SS-CPP) ✅ | ✅ DS-RP-B · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-SA** Smart Actuator | [B-SA-CPP](https://github.com/chipkin/BACnetProfileExample-B-SA-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-ASC** Application Specific Controller | [B-ASC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ASC-CPP) ✅ · [B-ASC-Node](https://github.com/chipkin/BACnetProfileExample-B-ASC-Node) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B |
| **B-AAC** Advanced Application Controller | [B-AAC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AAC-CPP) ✅ | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ AE-N-I-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-CRL-B · ✅ SCHED-I-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B |
| **B-BC** Building Controller | [B-BC-CPP](https://github.com/chipkin/BACnetProfileExample-B-BC-CPP) 📝 | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-RPM-B · ✅ DS-WP-A · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ AE-N-I-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-CRL-B · ✅ SCHED-E-B · ✅ T-VMT-I-B · ✅ T-ATR-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B · ✅ DM-BR-B |

### Life safety controllers (Annex L.5)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-LSC** Life Safety Controller | [B-LSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-LSC-CPP) 📝 | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-B · ✅ AE-LS-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B |
| **B-ALSC** Advanced Life Safety Controller | [B-ALSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ALSC-CPP) 📝 | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-B · ✅ AE-LS-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-EL-I-B · ✅ SCHED-I-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B |

### Access control controllers (Annex L.6)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-ACC** Access Control Controller | [B-ACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACC-CPP) 📝 | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-B · ✅ DS-ACUC-B · ✅ DS-ACSC-B · ✅ AE-AC-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-EL-I-B · ✅ SCHED-I-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B · ✅ DM-BR-B |
| **B-AACC** Advanced Access Control Controller | [B-AACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AACC-CPP) 📝 | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-RPM-B · ✅ DS-WP-A · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-A · ✅ DS-COV-B · ✅ DS-ACAD-A · ☐ DS-ACCDI-A · ✅ DS-ACUC-B · ✅ DS-ACSC-B · ✅ AE-AC-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-EL-I-B · ✅ SCHED-I-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B · ✅ DM-BR-B |

### Lighting controllers (Annex L.11)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-LD** Lighting Device | [B-LD-CPP](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DS-LO-B / DS-BLO-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B |
| **B-LS** Lighting Supervisor | [B-LS-CPP](https://github.com/chipkin/BACnetProfileExample-B-LS-CPP) 📝 | ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-WP-B · ✅ DS-WG-E-B · ✅ DS-ALO-A · ✅ SCHED-E-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B |

### Elevator controllers (Annex L.13)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-EM** Elevator Monitor | [B-EM-CPP](https://github.com/chipkin/BACnetProfileExample-B-EM-CPP) ✅ | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-COV-B · ✅ DS-COVM-B · ✅ AE-N-I-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B |
| **B-EC** Elevator Controller | [B-EC-CPP](https://github.com/chipkin/BACnetProfileExample-B-EC-CPP) 📝 | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-B · ✅ DS-COVM-B · ✅ AE-N-I-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-RD-B |
| **B-AEC** Advanced Elevator Controller | [B-AEC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AEC-CPP) 📝 | ✅ DS-RP-B · ✅ DS-RPM-B · ✅ DS-WP-B · ✅ DS-WPM-B · ✅ DS-COV-B · ✅ DS-COVM-B · ✅ AE-N-I-B · ✅ AE-ACK-B · ✅ AE-INFO-B · ✅ AE-EL-I-B · ✅ SCHED-I-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B · ✅ DM-OCD-B · ✅ DM-RD-B · ✅ DM-BR-B |

### Authentication and authorization (Annex L.14)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-AS** Authorization Server | [B-AS-CPP](https://github.com/chipkin/BACnetProfileExample-B-AS-CPP) 📝 | ✅ DS-RP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ AA-AS-B |

### Miscellaneous (Annex L.7, combinable with any one family)

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-BBMD** Broadcast Management Device | [B-BBMD-CPP](https://github.com/chipkin/BACnetProfileExample-B-BBMD-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ NM-BBMDC-B |
| **B-ACDC** Access Control Door Controller | [B-ACDC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACDC-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DS-ACAD-B · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-ACCR** Access Control Credential Reader | [B-ACCR-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DS-COV-B · ✅ DS-ACCDI-B · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-RTR** Router | [B-RTR-CPP](https://github.com/chipkin/BACnetProfileExample-B-RTR-CPP) 📝 | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-A · ✅ DM-DOB-B · ✅ DM-LM-B · ✅ NM-RC-B |
| **B-GW** Gateway | [B-GW-CPP](https://github.com/chipkin/BACnetProfileExample-B-GW-CPP) 📝 | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ GW-EO-B / GW-VN-B |
| **B-DAP** Device Address Proxy | [B-DAP-CPP](https://github.com/chipkin/BACnetProfileExample-B-DAP-CPP) ✅ | ✅ DS-RP-B · ✅ DS-WP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DAB-B |
| **B-SCHUB** BACnet/SC Hub | [B-SCHUB-CPP](https://github.com/chipkin/BACnetProfileExample-B-SCHUB-CPP) 📝 | ✅ DS-RP-B · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ NM-SCH-B |
| **B-GENERAL** General device (Annex L.8) | *(satisfied by every example above)* | ✅ DS-RP-B · ✅ DM-DDB-B · ✅ DM-DOB-B |

### Operator interfaces and workstations (Annex L.1–L.3, L.9–L.10, L.12) — client-side profiles

| Profile | Example | Required BIBBs (services) |
|---|---|---|
| **B-OD** Operator Display | [B-OD-CPP](https://github.com/chipkin/BACnetProfileExample-B-OD-CPP) ✅ | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-V-A · ✅ DS-M-A · ✅ AE-N-A · ✅ AE-VN-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-OWS** Operator Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-V-A · ✅ DS-M-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-VM-A · ✅ AE-VN-A · ✅ SCHED-VM-A · ✅ T-V-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-MTS-A |
| **B-AWS** Advanced Operator Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-AV-A · ✅ DS-AM-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-AVM-A · ✅ AE-AVN-A · ✅ AE-ELVM-A · ✅ SCHED-AVM-A · ✅ T-AVM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A · ✅ DM-DDA-A · ✅ NM-CC-A · ✅ AR-AVM-A |
| **B-XAWS** Extended Advanced Operator Workstation | planned | ✅ union of B-AWS + B-AACWS + B-ALWS + B-AEWS |
| **B-LSAP** Life Safety Annunciator Panel | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-LSV-A · ✅ AE-N-A · ✅ AE-LS-A · ✅ AE-ACK-A · ✅ AE-LSVN-A |
| **B-LSWS** Life Safety Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-LSV-A · ✅ DS-LSM-A · ✅ AE-N-A · ✅ AE-LS-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-LSVM-A · ✅ AE-LSAVN-A · ✅ AE-ELV-A · ✅ SCHED-VM-A · ✅ T-V-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A |
| **B-ALSWS** Advanced Life Safety Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-LSAV-A · ✅ DS-LSAM-A · ✅ AE-N-A · ✅ AE-LS-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-LSAVM-A · ✅ AE-LSAVN-A · ✅ AE-ELVM-A · ✅ SCHED-AVM-A · ✅ T-AVM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A · ✅ AR-AVM-A |
| **B-ACSD** Access Control Security Display | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-ACV-A · ✅ DS-ACM-A · ✅ AE-N-A · ✅ AE-AC-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-ACAVN-A · ✅ AE-ELV-A · ✅ SCHED-VM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-MTS-A |
| **B-ACWS** Access Control Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-ACAV-A · ✅ DS-ACM-A · ✅ DS-ACUC-A · ✅ AE-N-A · ✅ AE-AC-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-ACVM-A · ✅ AE-ACAVN-A · ✅ AE-ELV-A · ✅ SCHED-VM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A |
| **B-AACWS** Advanced Access Control Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-ACAV-A · ✅ DS-ACAM-A · ✅ DS-ACUC-A · ✅ DS-ACSC-A · ✅ AE-N-A · ✅ AE-AC-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-ACAVM-A · ✅ AE-ACAVN-A · ✅ AE-ELVM-A · ✅ SCHED-AVM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A · ✅ AR-AVM-A |
| **B-LOD** Lighting Operator Display | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-LV-A · ✅ DS-WG-A · ✅ DS-ALO-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-ALWS** Advanced Lighting Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-LAV-A · ✅ DS-LAM-A · ✅ DS-WG-A · ✅ DS-ALO-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-AVM-A · ✅ AE-AVN-A · ✅ AE-ELVM-A · ✅ SCHED-AVM-A · ✅ T-AVM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A |
| **B-LCS** Lighting Control Station | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-LO-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B |
| **B-ALCS** Advanced Lighting Control Station | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-WG-A · ✅ DS-ALO-A · ✅ SCHED-E-B · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B · ✅ DM-DCC-B · ✅ DM-TS-B / DM-UTC-B |
| **B-ED** Elevator Display | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-WP-A · ✅ DS-EV-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-EVN-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-DOB-B |
| **B-EWS** Elevator Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-COVM-A · ✅ DS-EV-A · ✅ DS-EM-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-EVM-A · ✅ AE-EAVN-A · ✅ SCHED-VM-A · ✅ T-V-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A |
| **B-AEWS** Advanced Elevator Workstation | planned | ✅ DS-RP-A · ✅ DS-RP-B · ✅ DS-RPM-A · ✅ DS-WP-A · ✅ DS-WPM-A · ✅ DS-COVM-A · ✅ DS-EAV-A · ✅ DS-EAM-A · ✅ AE-N-A · ✅ AE-ACK-A · ✅ AE-AS-A · ✅ AE-EAVM-A · ✅ AE-EAVN-A · ✅ AE-ELVM-A · ✅ SCHED-AVM-A · ✅ T-AVM-A · ✅ DM-DDB-A · ✅ DM-DDB-B · ✅ DM-ANM-A · ✅ DM-ADM-A · ✅ DM-DOB-B · ✅ DM-DCC-A · ✅ DM-MTS-A · ✅ DM-OCD-A · ✅ DM-RD-A · ✅ DM-BR-A |

Profile definitions: ANSI/ASHRAE 135-2024 Annex L. BIBB definitions: Annex K. Get the stack: <https://store.chipkin.com/services/stacks/bacnet-stack>.
<!-- PROFILE-TABLE:END -->

## Footprint

Release-build sizes and start-up timing, from the latest tagged release's CI
run (`metrics-windows.json` / `metrics-linux.json`), both built with
`CAS_BACNET_STACK_LINK=STATIC`:

<!-- METRICS -->
| Platform | Binary | Size | SHA-256 (prefix) | Start-up to `ready` | Stack commit | Link mode | Compiler |
|---|---|---|---|---|---|---|---|
| Windows x64 (windows-2022) | `BACnetExampleBACCR.exe` | 3,251,712 bytes (~3.1 MiB) | `f49ef8af048612d9` | 179 ms | `abd4cee1` | STATIC | Visual Studio 17 2022 |
| Linux x64 (ubuntu-latest) | `BACnetExampleBACCR` | 39,944 bytes (~39 KiB) | `b7e307d14ea9805c` | 109 ms | `abd4cee1` | STATIC | `/usr/bin/c++` |

From release [v1.0.0](https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP/releases/tag/v1.0.0) (`metrics-windows.json` / `metrics-linux.json`).

## References

- **ANSI/ASHRAE Standard 135** (BACnet) - the protocol standard. Object model
  (Clause 12), services (Clause 15), BACnet/IP (Annex J), device profiles
  (Annex L). Purchase / preview via the [ASHRAE store](https://www.ashrae.org/technical-resources/standards-and-guidelines).
- **What is BACnet?** - Chipkin's introduction:
  <https://docs.chipkin.com/protocols/bacnet/>.
- **CAS BACnet Stack** - product page and documentation:
  <https://store.chipkin.com/services/stacks/bacnet-stack>.
- **CAS BACnet Explorer** - client for testing this device:
  <https://store.chipkin.com/products/tools/cas-bacnet-explorer>.
- **B-SS (Smart Sensor) example** - the read-only sibling this builds on:
  <https://github.com/chipkin/BACnetProfileExample-B-SS-CPP>.
- **B-SA (Smart Actuator) example** - the seed this repository was built from:
  <https://github.com/chipkin/BACnetProfileExample-B-SA-CPP>.
- **Shared helper used by this example** - [`common/README.md`](common/README.md).

## Use this in your own project

This repository is self-contained: clone it (with the submodule) and build, then
copy what you need into your product. The example source code is dedicated to the
public domain under [CC0-1.0](LICENSE) - use it for anything, no attribution
required. The CAS BACnet Stack is a separate, commercially licensed product and
is not covered by CC0.

See also [CHANGELOG.md](CHANGELOG.md) and [AGENTS.md](AGENTS.md).
