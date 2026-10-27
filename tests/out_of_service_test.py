#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACCR Wire Test: an input's Present_Value is writable while it is Out_Of_Service.

    python3 tests/out_of_service_test.py [--exe build/BACnetExampleBACCR] [--port 47812]

135-2024 cl. 12.2.4, and footnote 1 of Tables 12-2 (Analog Input), 12-5 (Binary Input),
12-19 (Multi-state Input) and 12-43 (Credential Data Input): Present_Value - and the
Credential Data Input's Reliability - "is required to be writable when Out_Of_Service is
TRUE". For each of the four input objects:

    1. in service, a WriteProperty of Present_Value (Reliability) is refused
       (Error PROPERTY / WRITE_ACCESS_DENIED)
    2. WriteProperty Out_Of_Service TRUE, then Present_Value (Reliability) is accepted and
       reads back the written value; a Multi-state value outside 1..Number_Of_States is
       refused VALUE_OUT_OF_RANGE
    3. WriteProperty Out_Of_Service FALSE, and Present_Value tracks the input again

The Credential Data Input's Present_Value (a BACnetAuthenticationFactor) has no customer
callback to carry the write, so that one check is a [KNOWN GAP] (TODO.md).

Exit code 0 = every check passed.
"""
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wiretest  # noqa: E402  (the vendored harness at the repository root)
from wiretest import codec, known_gap, record, summary  # noqa: E402
from discovery_test import parser  # noqa: E402  (this example's options)

PRESENT_VALUE, OUT_OF_SERVICE, RELIABILITY = 85, 81, 103
OBJECT_TYPE_CREDENTIAL_DATA_INPUT = 37
ERROR_CLASS_PROPERTY = 2
ERROR_CODE_WRITE_ACCESS_DENIED, ERROR_CODE_VALUE_OUT_OF_RANGE = 40, 37

# (label, object type, property, substitute value octets, value read back, live value)
CASES = [
    ("Analog Input 1", wiretest.OBJECT_TYPE_ANALOG_INPUT, PRESENT_VALUE, codec.application_real(30.0), 30.0, 21.5),
    ("Binary Input 1", wiretest.OBJECT_TYPE_BINARY_INPUT, PRESENT_VALUE, codec.application_enumerated(1), 1, 0),
    ("Multi-state Input 1", wiretest.OBJECT_TYPE_MULTI_STATE_INPUT, PRESENT_VALUE, codec.application_unsigned(2), 2, 1),
    ("Credential Data Input 1", OBJECT_TYPE_CREDENTIAL_DATA_INPUT, RELIABILITY, codec.application_enumerated(7), 7, 0),
]
PROPERTY_NAMES = {PRESENT_VALUE: "Present_Value", RELIABILITY: "Reliability"}


def write(client, port, object_type, property_identifier, octets):
    return client.write_property(port, object_type, 1, property_identifier, octets, timeout=2.0)


def main():
    args = parser().parse_args()
    reader = wiretest.start(args.exe, ["--port", args.port], "B-ACCR")
    client = wiretest.Client(retries=1)
    try:
        for label, object_type, property_identifier, octets, substitute, live in CASES:
            name = PROPERTY_NAMES[property_identifier]
            refused = write(client, args.port, object_type, property_identifier, octets)
            record(f"{label}: in service, a write of {name} is refused WRITE_ACCESS_DENIED",
                   refused.error == (ERROR_CLASS_PROPERTY, ERROR_CODE_WRITE_ACCESS_DENIED), refused.describe())
            out = write(client, args.port, object_type, OUT_OF_SERVICE, codec.application_boolean(True))
            accepted = write(client, args.port, object_type, property_identifier, octets)
            read = client.read_property(args.port, object_type, 1, property_identifier, timeout=2.0)
            record(f"{label}: Out_Of_Service TRUE, then {name} is written and reads back {substitute}",
                   out.ok and accepted.ok and read.ok and read.value == substitute,
                   f"{out.describe()}; {accepted.describe()}; {read.describe()}")
            if object_type == wiretest.OBJECT_TYPE_MULTI_STATE_INPUT:
                too_big = write(client, args.port, object_type, PRESENT_VALUE, codec.application_unsigned(4))
                record(f"{label}: out of service, Present_Value 4 (above Number_Of_States 3) is refused "
                       "VALUE_OUT_OF_RANGE", too_big.error == (ERROR_CLASS_PROPERTY, ERROR_CODE_VALUE_OUT_OF_RANGE),
                       too_big.describe())
            if object_type == OBJECT_TYPE_CREDENTIAL_DATA_INPUT:
                factor = (codec.opening(0) + codec.context_unsigned(0, 4) + codec.context_unsigned(1, 0)
                          + codec.context_octet_string(2, bytes.fromhex("00A1B2C4")) + codec.closing(0))
                # Present_Value is a SEQUENCE; WriteProperty carries it inside the [3] value tag.
                pv = client.request(lambda invoke_id: bytes([0x00, 0x05, invoke_id, 0x0F])
                                    + codec.context_object_id(0, object_type, 1) + codec.context_unsigned(1, PRESENT_VALUE)
                                    + codec.opening(3) + factor[1:-1] + codec.closing(3), args.port, timeout=2.0)
                known_gap(f"{label}: out of service, Present_Value (BACnetAuthenticationFactor) is writable",
                          pv.ok, f"{pv.describe()}: the stack's customer interface has no callback to carry the "
                          "write (TODO.md)")
            back = write(client, args.port, object_type, OUT_OF_SERVICE, codec.application_boolean(False))
            read = client.read_property(args.port, object_type, 1, property_identifier, timeout=2.0)
            record(f"{label}: Out_Of_Service FALSE, and {name} reads the input's own value ({live}) again",
                   back.ok and read.ok and read.value == live, f"{back.describe()}; {read.describe()}")
    finally:
        client.close()
        reader.stop()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
