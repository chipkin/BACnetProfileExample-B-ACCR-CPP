# Tutorial - extending and reviewing the B-ACCR example

[README.md](README.md) says what this example *is*. This document is the
*how*: how to extend it into your own device, who serves which property, how
to add COV to a new property, how to review the result for conformance, and
what goes wrong when you get it subtly right.

Read this once before you start changing `main.cpp`. The most expensive
mistake in this example is silent, and the section it lives in is
[Add COV to a new property](#add-cov-to-a-new-property) - specifically the
paragraph about Credential Data Input's subscribable property.

- [Extending the example](#extending-the-example)
- [Add COV to a new property](#add-cov-to-a-new-property)
- [Credential Data Input's Present_Value is not a scalar](#credential-data-inputs-present_value-is-not-a-scalar)
- [What each object type needs you to serve](#what-each-object-type-needs-you-to-serve)
- [Who serves what: the application or the stack?](#who-serves-what-the-application-or-the-stack)
- [Reviewing your device](#reviewing-your-device)
- [Troubleshooting](#troubleshooting)

## Extending the example

The example is intentionally small so it's easy to change.

**Change a value or name** - edit the constants / callbacks in `main.cpp`
(e.g. the initial `g_credentialValue`, or the `"Flax"` string in
`GetPropertyCharString`).

**Change the device identity before you ship** - vendor ID, vendor name, model
name, description, firmware revision and device name are all in the
`CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of `main.cpp`, with a
per-field note on each saying what to change it to. That block is the
authoritative checklist; it is in the source rather than here so it cannot be
skipped by someone who only reads the code.

## Add COV to a new property

This repository is the series' canonical reference for SubscribeCOV (F-COV).
Follow these three steps, in order, when you add COV to a property:

1. `BACnetStack_SetPropertySubscribable(deviceInstance, type, instance,
   propertyIdentifier, true)` once at start-up, after the property is
   enabled - **and `propertyIdentifier` must be the property that object
   TYPE'S plain SubscribeCOV actually monitors** (135-2024 Table 13-1;
   `Present_Value` for most types, `Update_Time` for Credential Data Input,
   `Access_Event_Time` for an Access Point). Get this wrong and setup still
   returns `true`, but every client's SubscribeCOV fails with
   `not-cov-property`.
2. Confirm `BACnetStack_SetCOVSettings` has already been called once for the
   device (it has, in this example) - it is not per-property.
3. Every place the application changes that property's value, call
   `BACnetStack_UpdateValue(deviceInstance, type, instance,
   propertyIdentifier)` right after. **This is the step people forget**: the
   service can be enabled and the property subscribable, and a device that
   never calls `UpdateValue` will still never notify anyone.

> **CREDENTIAL DATA INPUT'S SUBSCRIBABLE PROPERTY IS `Update_Time`, NOT
> `Present_Value` - read this before copying the Analog Input call as a
> template.** A plain SubscribeCOV (as opposed to SubscribeCOVProperty, which
> names an arbitrary property explicitly) does not let the client choose which
> property to monitor - the **server** decides, per object type, per
> 135-2024 Table 13-1. For most types that is `Present_Value`; for Credential
> Data Input the standard's own COV column says "if `Update_Time` changes at
> all, or `Status_Flags` changes at all" - **not** `Present_Value` (verified
> against the stack's own
> `BACnetSubscribeCOVProcessor::GetSubscriptionProperty()`, which returns
> `BACnetPropertyIdentifier::updateTime` for `credentialDataInput` and
> `presentValue` for everything else).
>
> Calling `SetPropertySubscribable` on Credential Data Input's `Present_Value`
> instead **compiles, runs, and returns `true`** - and then every client's
> SubscribeCOV on that object fails with `Error(subscribe-cov): property:
> not-cov-property`, because the stack is checking a *different* property's
> subscribable flag than the one that got set. This was confirmed on the wire
> with a real BACnet client while building this example (see `CHANGELOG.md`). The
> notification *content* is unaffected by this distinction: it still carries
> `Present_Value` + `Status_Flags` + `Update_Time` - `Update_Time` is only the
> **trigger condition**, not the only payload field.
>
> **Why a half-wired COV property fails silently.** SubscribeCOV itself still
> succeeds even if you forget step 3 (`UpdateValue`) - the stack accepts the
> subscription and sends the *initial* notification, since that one is
> generated from the current value regardless. What is missing is every
> *subsequent* notification, and nothing on the wire says why. A scan tool
> sees "subscription accepted" and calls it healthy. Verify with the actual
> sequence in [Reviewing your device](#reviewing-your-device) below (press the
> key, confirm a **second** notification arrives), not just that the
> subscription was accepted.

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
(stack PRs #166 and #167), not a gap.

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

Both properties are REQUIRED (cl. 12.36) but are **not yet listed** in the
stack's `docs/property-profile-reference.md` for the Credential Data Input
object type - that is why they do not appear as rows in
[docs/PICS.md](docs/PICS.md)'s generated table even though `main.cpp` serves
them. It is a documentation gap in the reference the generator reads, not a
capability gap in this example - see `docs/objects.json`'s note on the
Credential Data Input entry.

## What each object type needs you to serve

The application must serve every REQUIRED property the stack does not
generate. It differs per type - this is the checklist, so you do not have to
infer it:

| Object type | You must serve | Plus |
|---|---|---|
| Analog Input | `Present_Value` (Real), `Object_Name`, `Units` | subscribable `Present_Value` |
| Binary Input | `Present_Value` (Enumerated), `Object_Name` | `Polarity` |
| Multi-State Input | `Present_Value` (Unsigned), `Object_Name` | `Number_Of_States` |
| Credential Data Input | `Present_Value` (OctetString, wrapped as AuthenticationFactor), `Object_Name`, `Reliability` (Enumerated) | `Supported_Formats` (dedicated AuthenticationFactorFormat callback), `Update_Time` (Time callback; ALSO the subscribable property - see [Add COV to a new property](#add-cov-to-a-new-property)) |

`Out_Of_Service` is required on every object above, and writable (DS-WP-B) on
all four via `SetPropertyBool` / `SetPropertyWritable`.

## Who serves what: the application or the stack?

The single most common question when reading this file is "who answers this
property?" For **Credential Data Input 1** - the object that makes this a
B-ACCR - the whole picture:

| Property | Served by | How |
|---|---|---|
| `Object_Identifier` | **stack** | generated from the object you added |
| `Object_Type` | **stack** | generated |
| `Object_List` | **stack** | generated (Device object) |
| `Property_List` | **stack** | generated |
| `Status_Flags` | **stack** | generated |
| `Out_Of_Service` | **you** | `GetPropertyBool` / `SetPropertyBool` - writable (DS-WP-B) |
| `Present_Value` | **you** | `GetPropertyOctetString` - raw bytes; the stack wraps the `AuthenticationFactor` SEQUENCE around them |
| `Object_Name` | **you** | `GetPropertyCharString` |
| `Reliability` | **you** | `GetPropertyEnumerated` |
| `Supported_Formats` | **you** | `GetPropertyAuthenticationFactorFormat` (per element) + `GetPropertyUnsignedInteger` (array length, index 0) |
| `Update_Time` | **you** | `GetPropertyTime` - the stack wraps it into `BACnetTimeStamp`; this is also the property SubscribeCOV actually monitors for this object type |

Every object, not just this one, is in [docs/PICS.md](docs/PICS.md).

Going beyond this (alarming, scheduling, trending, ReadPropertyMultiple) means
implementing a richer profile - see the series table in
[README.md](README.md).

## Reviewing your device

After you have changed anything, review it against the conformance statement
rather than against "it looked fine in the explorer":

1. Regenerate [docs/PICS.md](docs/PICS.md) after editing `docs/objects.json`
   (see [Keeping the PICS honest](#keeping-the-pics-honest) below). A ⚠ row is
   a required property nothing serves.
2. Read **every** property listed for **every** object with a BACnet client,
   and compare the value against the PICS. `"undefined"`, `no-units` and `0`
   are the three shapes a missed callback takes.
3. **SubscribeCOV on Analog Input 1** (confirmed, then unconfirmed). Confirm
   the *initial* notification arrives immediately with `Present_Value` and
   `Status_Flags`. Press the up/down key on the running device; confirm a
   **change notification** arrives. Subscribe with a short lifetime and
   confirm the subscription **expires** when it elapses.
4. **SubscribeCOV on Credential Data Input 1** - subscribe to `Update_Time`
   (see [Add COV to a new property](#add-cov-to-a-new-property) for why) and
   confirm the *initial* notification carries `Present_Value` **and**
   `Update_Time`. Press up/down again and confirm a change notification for
   the new card.
5. **WriteProperty** `Out_Of_Service` = `true` on each input-family object;
   re-read it back as `true`. Confirm a WriteProperty to `Present_Value` (any
   object) is rejected: no object in this profile has a profile-writable
   `Present_Value`.
6. Diff a new object of a type against the existing one of that type. Anything
   that differs and shouldn't is a callback that matched on instance.

### Keeping the PICS honest

`docs/PICS.md` is partly generated. `docs/objects.json` describes each object
and who serves which property; the series tool regenerates the object tables
from it plus the stack's own `docs/property-profile-reference.md` at the
pinned commit:

```bash
python tools/gen-objects-properties.py BACnetProfileExample-B-ACCR-CPP            # rewrite
python tools/gen-objects-properties.py BACnetProfileExample-B-ACCR-CPP --check    # fail if stale
```

(That tool lives in the example-series repository, not in this one. If you
only have this repository, edit the generated block by hand and keep it
matching the callbacks in `main.cpp`.)

When you add an object or a property to `main.cpp`, update `docs/objects.json`
in the same change and regenerate. The `app` list is what the callbacks serve;
`accepted` is for a required property you deliberately leave to the stack's
default, and each one needs a justification. Anything required, not in `app`
and not in `accepted`, comes out as a ⚠ row - that is a defect, not a feature.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| On start-up the app prints a wall of red `Error:` lines but the device works | **Expected — this is not your bug.** Two benign sources, both from the stack's own debug logging: (1) the device receives its **own** broadcast I-Am and logs a decode cascade (*"Services is not supported service=[0]"* … *"Failed to process the incoming NPDU"*) — any BACnet/IP device that listens for broadcasts hears itself; (2) a one-time *"UUID has not been set. A UUID must be set for the BACnetSC device to start."* — the stack starts a BACnet/SC datalink these IP-only examples never configure. It appears once and does not spam. On a healthy start-up roughly half the output is these lines. |
| CMake error: *"CAS BACnet Stack adapter not found under: ..."* | Submodules not initialized. Run `git submodule update --init --recursive` (or pass `-D CAS_STACK_DIR=...`). |
| `CASBACnetStackDLL.h: No such file or directory` | Same - submodules not checked out. |
| Windows: *"No CMAKE_CXX_COMPILER could be found"* | Install Visual Studio with the "Desktop development with C++" workload, then re-run from a fresh terminal. |
| First build seems stuck for minutes | Normal - it's compiling ~600 stack files. Only the first build is slow. |
| App prints *"Failed to bind UDP port 47808"* | Another BACnet program is already using 47808. Stop it, or run with `--port <n>`. |
| SubscribeCOV to a property other than `Present_Value` on Analog Input 1, or other than `Update_Time` on Credential Data Input 1, is rejected with `not-cov-property` | Correct - a plain SubscribeCOV monitors exactly one property per object type, decided by the stack (135-2024 Table 13-1), not the client. See [Add COV to a new property](#add-cov-to-a-new-property). |
| A subscription is accepted (initial notification arrives) but no further notifications ever come | You forgot `BACnetStack_UpdateValue` after changing the value - see the "half-wired COV property" warning above. This is the single most common way to build a device that *looks* COV-capable but never actually notifies. |
| WriteProperty to `Present_Value` is rejected | Correct - no object in this profile has a profile-writable `Present_Value`. Only `Out_Of_Service` is writable, on the four input-family objects. |
| Client sends Who-Is but sees no I-Am | Firewall is blocking UDP 47808, or the client and device are on different subnets (Who-Is is a broadcast). Allow the port; test on the same subnet first. |
| Replies show an unexpected device instance or vendor | Another BACnet device is already answering on this host/port. On Linux/macOS two processes can share the port and both reply; on Windows the example asks for `SO_EXCLUSIVEADDRUSE` (`common/SimpleUDP.cpp`) so this shows up as a bind failure instead. Stop the other device, or use `--port`. |
