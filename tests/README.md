# B-ACCR Wire Tests

Tests that drive the running example over BACnet/IP from outside it. B-ACCR is a
**Blocked Example** (stack #3934): its Profile Function, reporting a presented
credential with its Format-Type, cannot be performed through the stack's
customer interface, so there is nothing to test for it yet. What is tested is
the device the way a client discovering it sees it: every property every object
lists, the Credential Data Input's included, must read as a value. They are
written against the series' shared harness in
[`../wiretest/`](../wiretest/README.md) (vendored, like `common/`); everything
specific to this example is here. Python 3 standard library only - nothing to
`pip install`.

## Running

Build the example (README "Build"), then from the repository root:

```bash
python3 tests/run_wire_tests.py --exe build/BACnetExampleBACCR
```

On Windows, `--exe build\Release\BACnetExampleBACCR.exe`. It ends with
`ALL WIRE TESTS PASSED` (exit 0) or the scripts that failed. `--port` (default
47812) is the UDP port the test starts the device on. It takes a few seconds.
CI (`.github/workflows/release.yml`) runs it on Linux after the smoke test.

## The setup

```
test client (127.0.0.1, ephemeral UDP port)  - the Peer
    |  BACnet/IP, unicast
BACnetExampleBACCR  UDP --port               - Device 389012
```

The Peer is a Python BACnet client (`wiretest.Client`), never another example's
binary. It plays a BACnet client such as Chipkin BACnet Explorer.

## `discovery_test.py` - every listed property reads as a value

The series' discovery test, copied from B-SS-CPP; only the device instance,
executable name, port and the expected objects differ.

1. **Who-Is** (for 389012, unicast) -> the device's I-Am. Who-Is is
   unconfirmed, so if no I-Am comes back in 3 s it is sent once more, with a
   visible `[RETRY]` line.
2. **Device `Object_List`** names exactly the Device, Analog Input 1, Binary
   Input 1, Multi-state Input 1, Credential Data Input 1 and Network Port 1.
   This is the control: a walk over nothing would pass.
3. For each object, **`Property_List`** reads, and a ReadProperty of every
   property it lists - plus `Object_Identifier`, `Object_Name`, `Object_Type`
   and `Property_List`, which cl. 12.1.1.4.1 leaves out of the list - returns a
   ComplexACK. An Error, Reject, Abort or no answer prints an `[UNREADABLE]` line
   and fails the check. 135-2024 cl. 12.1.1.4.1: Property_List holds "one
   property identifier for each property that exists within the object".
4. Network Port 1's **`IP_DNS_Server` (406)**, **`FD_BBMD_Address` (418)** and
   **`FD_Subscription_Lifetime` (419)** are each listed and read as a value -
   the three reads Chipkin BACnet Explorer found failing at stack 6.0.21
   (reported against B-SS-CPP as #20, #21, #22; this example sets up its Network
   Port the same way).
5. Device **`Database_Revision`** reads 6: the stack adds one per object added at
   start-up (cl. 12.11), and it still reads 6 after Credential Data Input 1's
   `Out_Of_Service` is written TRUE and back to FALSE - a value change, not an
   object database change.
6. Analog Input 1's **`COV_Increment`** is listed in its `Property_List` and
   reads 1.0: the object supports COV reporting, so cl. 12.2.16 requires it.

It does not check what the Credential Data Input's `Present_Value` holds: its
Format-Type reads `UNDEFINED` (0), which is the stack #3934 gap (see
[`../TODO.md`](../TODO.md)), and a read of it still returns a value.

## `configuration_test.py` - the Device's identity is configurable at start-up

BACnet requires the Device's Object_Identifier and Object_Name to be
configurable (135-2024 cl. 12.1.1.3, 12.1.1.4); Object_Name must be unique
across the internetwork, so two units cannot share a compile-time name. The
credential reader is started several ways, and its help is checked:

1. **No options (control):** Device 389012 answers Who-Is, and its
   `Object_Name` is the default `Chipkin Example B-ACCR`.
2. **`--deviceID 389912 --deviceName "Chipkin Example B-ACCR Unit 2"`:** the
   device answers Who-Is as 389912, its `Object_Name` reads the configured
   name, Device 389012 is gone (Error OBJECT / UNKNOWN_OBJECT), the ready line
   names the configured device, and a Who-Has by that name gets an I-Have
   from Device 389912 with that name (DM-DOB-B).
3. **Boundaries:** an empty name and a 256-byte name each print a warning and
   keep the default; a 255-byte name (the limit) reads back whole.
4. **The command line:** `--help` lists `--port`, `--deviceID`, `--deviceName`
   and `--xml`, and not `--dcc-password` (this credential reader does not
   execute DeviceCommunicationControl); with `--xml` the console shows each
   frame as an XML block.

## `out_of_service_test.py` - Present_Value is writable while out of service

135-2024 cl. 12.2.4 and footnote 1 of Tables 12-2, 12-5, 12-19 and 12-43: an
input's `Present_Value` (and a Credential Data Input's `Reliability`) "is
required to be writable when Out_Of_Service is TRUE". For Analog Input 1,
Binary Input 1, Multi-state Input 1 (`Present_Value`) and Credential Data
Input 1 (`Reliability`):

1. **In service**, a write is refused (Error PROPERTY / WRITE_ACCESS_DENIED).
2. **`Out_Of_Service` TRUE**, the write is accepted and reads back; a
   Multi-state value above `Number_Of_States` is refused VALUE_OUT_OF_RANGE.
3. **`Out_Of_Service` FALSE**, the property reads the input's own value again.

Credential Data Input 1's `Present_Value` cannot be written even out of
service (no customer callback carries a `BACnetAuthenticationFactor`; see
[`../TODO.md`](../TODO.md)): that check prints `[KNOWN GAP]` and does not
fail the run. Against the binary from before this fix (2026-10-26, Windows)
it fails 4 of 13 checks (each out-of-service write).

## `out_of_service_cov_test.py` - an Out_Of_Service change notifies COV subscribers

135-2024 cl. 13.1 / Table 13-1: a COV notification is sent when `Status_Flags`
changes at all, and writing `Out_Of_Service` flips its OUT_OF_SERVICE bit. A
Peer subscribes (SubscribeCOV, unconfirmed) to Analog Input 1 and to Credential
Data Input 1, sees the initial notification, then writes `Out_Of_Service`
TRUE, (Analog Input 1) `Present_Value` 30.0, and `Out_Of_Service` FALSE: each
write must be answered with a SimpleACK and then followed by a notification for
the object within 3 s (the notification reports the write's effect, so it comes
after the answer). Against the binary from before this fix (2026-10-26,
Windows) it fails 4 of 7 checks (no notification for an `Out_Of_Service`
write); against the first version of the fix, which reported from inside the
write, 5 of 7 (the notification came before the SimpleACK).

## Results

Run 2026-10-15, stack `6.x` @ `64b2cfac5` (6.0.23), `wiretest/` 0.6.0,
`common/` 3.4.0:

| Platform | Build | Result |
|---|---|---|
| Windows | STATIC (msbuild `ReleaseLib|x64` stack lib, VS 18 NMake) | 12/12 - PASS, 89 reads, no `[RETRY]` |
| Linux (WSL Ubuntu 22.04) | STATIC (`projects/linux` makefile stack lib) | 12/12 - PASS, 89 reads, no `[RETRY]` |
| Windows, re-run 2026-10-26 at `6.x` @ `69b6249f`, `common/` 3.5.0 | CMake SOURCE, VS 18 | discovery 12/12 (88 reads), configuration 18/18 - PASS, no `[RETRY]` |
