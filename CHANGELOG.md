# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No changes yet._

## [1.1.0] - 2026-10-27

This is a **Blocked Example**. The CAS BACnet Stack cannot yet report a presented
credential through its customer interface. See the note at the top of the README.

- **Does today:** a discoverable BACnet/IP device with Analog Input, Binary Input,
  Multi-state Input, Credential Data Input and Network Port objects. It answers
  ReadProperty, WriteProperty, Who-Is and SubscribeCOV.
- **Does not do today:** every read of Credential Data Input 1 `Present_Value`
  says "no credential" (Format-Type 0, cl. 12.36.4), because the real format type
  cannot be set. Two card presentations in the same second produce one COV
  notification, since `Update_Time` has one-second resolution. A write to the
  Credential Data Input's `Present_Value` is not possible.

Built on CAS BACnet Stack 6.x (`69b6249f`, 6.0.23).

### Added

- **`--deviceName <text>`** sets the Device's `Object_Name` at start-up (1 to 255
  bytes). The default, "Chipkin Example B-ACCR", is unchanged and the name cannot
  be written over BACnet. `--help` now lists only the options this example reads,
  and `--xml` (print each frame as XML) works.
- **Automated self-tests** under `tests/`: discovery, configuration, and
  out-of-service tests.
- **TUTORIAL.md** (the SubscribeCOV pattern, extending the example,
  troubleshooting) and **docs/PICS.md** (Annex A style).

### Changed

- **Device renamed** from "Rainbow" to "Chipkin Example B-ACCR" so examples on one
  network can be told apart. Object names such as "Bronze" are unchanged.
- **Build now compiles the stack source directly into the executable**:
  `cmake -B build -S .` then `cmake --build build --config Release` on every
  platform; the separate static-library step is gone.
- **Protocol_Revision is 30** (the documentation said 24), and segmentation is
  `segmented-both` (the PICS said none).
- **PICS Database_Revision is 6**, as the stack counts the objects added at
  start-up (cl. 12.11).

### Fixed

- **Taking an input out of service now notifies its COV subscribers**, as clause
  13.1 requires for a `Status_Flags` change.
- **An input's `Present_Value` is writable while it is out of service**
  (cl. 12.2.4); a Multi-state value outside 1..`Number_Of_States` is refused.
- **Analog Input 1 has `COV_Increment`** (1.0), as cl. 12.2.16 requires for COV.
- **Application_Software_Version and Firmware_Revision** report the real build
  version and stack version instead of a fixed "1.0.0".
- **Requests no longer go unanswered on Windows** in rare timing cases (shared
  `common/` 3.5.0).

## [1.0.0] - 2026-09-15

### Added

- Initial **B-ACCR (Access Control Credential Reader)** profile example in C++,
  built on CAS BACnet Stack 6.x (`abd4cee1`, 6.0.21).
- **DS-RP-B / DS-WP-B:** ReadProperty on every object; WriteProperty of
  `Out_Of_Service` on the four input objects.
- **DS-COV-B:** confirmed and unconfirmed SubscribeCOV on Analog Input 1 "Bronze"
  and Credential Data Input 1 "Flax", with the stack notified of each value change
  (the up/down keys).
- **DS-ACCDI-B:** Credential Data Input 1 serves `Present_Value`,
  `Supported_Formats` (simple-number32), `Update_Time` and `Reliability`.
- **DM-DDB-B / DM-DOB-B:** Who-Is/I-Am and Who-Has/I-Have.
- Objects: Analog Input 1 "Bronze", Binary Input 1 "Emerald", Multi-State Input 1
  "Hot Pink", Credential Data Input 1 "Flax", Network Port 1 "Vermilion".
- Note: for a Credential Data Input the stack monitors `Update_Time`, not
  `Present_Value`, for SubscribeCOV (135-2024 Table 13-1). The example makes
  `Update_Time` the COV trigger; notifications still carry `Present_Value`.
