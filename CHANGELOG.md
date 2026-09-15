# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - unreleased

### Added

Initial **B-ACCR (Access Control Credential Reader)** profile example for the
CAS BACnet Stack example series, built from the plan-only stub. Implements:

- **DS-RP-B / DS-WP-B** - ReadProperty on every object; WriteProperty of
  `Out_Of_Service` on the four input-family objects (this profile has no
  profile-required writable `Present_Value`).
- **DS-COV-B** - SubscribeCOV (confirmed and unconfirmed), enabled on Analog
  Input 1 (Bronze) and Credential Data Input 1 (Flax). This repo is the
  series' canonical source for the SubscribeCOV pattern (F-COV):
  `SetPropertySubscribable` + `SetCOVSettings` at start-up, and
  `BACnetStack_UpdateValue` on every application-driven value change (the
  up/down keys).
- **DS-ACCDI-B** - a **Credential Data Input** object (Flax, type 37) serving
  `Present_Value` (`BACnetAuthenticationFactor`, via the OctetString callback),
  `Supported_Formats` (via the dedicated
  `RegisterCallbackGetPropertyAuthenticationFactorFormat` callback -
  simple-number32 is the one format this reader supports), `Update_Time` (via
  the existing Time callback, wrapped into `BACnetTimeStamp` by the stack),
  and `Reliability`.
- **DM-DDB-B / DM-DOB-B** - Who-Is/I-Am and Who-Has/I-Have.
- Base objects: Analog Input 1 "Bronze", Binary Input 1 "Emerald",
  Multi-State Input 1 "Hot Pink", Network Port 1 "Vermilion".
- **CAS BACnet Stack 6.0.21 (`6.x` @ `abd4cee1`), linked as a static library**
  (`-DCAS_BACNET_STACK_LINK=STATIC`, built by `tools/build-stack-static.sh`).
  `common/` **v2.2.0**, byte-identical with the rest of the series.
- `docs/objects.json`-driven "Objects and properties" README block, the
  series-wide profile table block, and a `## Footprint` table placeholder
  (filled at release).

**Gap check:** none. The AuthenticationFactor / AuthenticationFactorFormat /
Update_Time customer-DLL callbacks this profile needs were verified present
at the pin (stack PRs #166 and #167 - see `docs/profiles.md`); `TODO.md` has
nothing to report.

**Found while building this example:** a plain SubscribeCOV does not let the
client choose which property it monitors - the stack decides, per object
type (135-2024 Table 13-1). For most types that is `Present_Value`; for
**Credential Data Input** the stack's own
`BACnetSubscribeCOVProcessor::GetSubscriptionProperty()` returns
`Update_Time` instead. Calling `SetPropertySubscribable` on
`Present_Value` for Credential Data Input 1 compiles, returns `true`, and
still fails every client's SubscribeCOV with `Error(subscribe-cov):
property: not-cov-property` - confirmed on the wire with `bacpypes3` while
building this example. Fixed by making `Update_Time` the subscribable /
`UpdateValue`-driven property instead; the notification payload still
carries `Present_Value` (it is just not the trigger condition). See the long
comment above the `SetPropertySubscribable` calls in `main.cpp`.

**Verified with a live BACnet client (`bacpypes3`), this session:**
Who-Is/I-Am from 389012; `Object_List` (6 objects); every required property
of Analog Input 1 and Credential Data Input 1 read back correctly, including
`Present_Value` (AuthenticationFactor, correctly wrapped), `Supported_Formats`
(1 entry, simple-number32), `Update_Time` (a real timestamp), and
`Reliability`; WriteProperty of `Out_Of_Service` on both objects accepted and
read back; WriteProperty of `Present_Value` rejected
(`write-access-denied`); SubscribeCOV confirmed on Analog Input 1 - initial
notification carries exactly `Present_Value` + `Status_Flags`; SubscribeCOV
unconfirmed on Credential Data Input 1 - initial notification carries
`Present_Value` + `Update_Time` + `Status_Flags`; the device continues
answering ReadProperty normally after a short-lifetime subscription elapses.
**Not verified this session:** a live, key-press-triggered *second* (change)
COV notification to an already-active subscriber - the session's environment
has no interactive console for the up/down keys `PollKey()` reads
(`_kbhit()`/`_getch()`, not scriptable via redirected stdin). The
`BACnetStack_UpdateValue` call this relies on is the same API already proven,
in this same session, to deliver the *initial* notification correctly for
both objects.

[1.0.0]: https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP/releases/tag/v1.0.0
