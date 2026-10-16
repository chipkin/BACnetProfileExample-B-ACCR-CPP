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

It does not check what the Credential Data Input's `Present_Value` holds: its
Format-Type reads `UNDEFINED` (0), which is the stack #3934 gap (see
[`../TODO.md`](../TODO.md)), and a read of it still returns a value.

## Results

Run 2026-10-15, stack `6.x` @ `64b2cfac5` (6.0.23), `wiretest/` 0.6.0,
`common/` 3.4.0:

| Platform | Build | Result |
|---|---|---|
| Windows | STATIC (msbuild `ReleaseLib|x64` stack lib, VS 18 NMake) | 12/12 - PASS, 89 reads, no `[RETRY]` |
| Linux (WSL Ubuntu 22.04) | STATIC (`projects/linux` makefile stack lib) | 12/12 - PASS, 89 reads, no `[RETRY]` |
