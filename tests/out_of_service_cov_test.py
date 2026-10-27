#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-ACCR Wire Test: taking an input out of service notifies its COV subscribers.

    python3 tests/out_of_service_cov_test.py [--exe build/BACnetExampleBACCR] [--port 47812]

135-2024 cl. 13.1 / Table 13-1: a COV notification is sent when the monitored value changes
(by COV_Increment or more, for an Analog Input) or when Status_Flags changes at all. Writing
Out_Of_Service sets or clears the OUT_OF_SERVICE bit of Status_Flags. For Analog Input 1 and
Credential Data Input 1, a Peer subscribes (SubscribeCOV, unconfirmed notifications) and then:

    1. WriteProperty Out_Of_Service TRUE   -> an UnconfirmedCOVNotification for the object
    2. (Analog Input 1) WriteProperty Present_Value 30.0 while out of service -> another one
    3. WriteProperty Out_Of_Service FALSE  -> another one

Exit code 0 = every check passed.
"""
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wiretest  # noqa: E402  (the vendored harness at the repository root)
from wiretest import codec, record, summary  # noqa: E402
from discovery_test import parser  # noqa: E402  (this example's options)

PRESENT_VALUE, OUT_OF_SERVICE = 85, 81
OBJECT_TYPE_CREDENTIAL_DATA_INPUT = 37
PDU_UNCONFIRMED_REQUEST, SERVICE_UNCONFIRMED_COV_NOTIFICATION = 0x10, 0x02
SUBSCRIBER_PROCESS_IDENTIFIER = 9


def subscribe_cov(object_type, instance, lifetime):
    def build(invoke_id):
        return (bytes([0x00, 0x05, invoke_id, 0x05]) + codec.context_unsigned(0, SUBSCRIBER_PROCESS_IDENTIFIER)
                + codec.context_object_id(1, object_type, instance)
                + bytes([0x29, 0x00])                       # [2] Issue Confirmed Notifications = FALSE
                + codec.context_unsigned(3, lifetime))
    return build


def is_notification(object_type, instance):
    monitored = codec.context_object_id(2, object_type, instance)
    return lambda frame: (frame.payload[:2] == bytes([PDU_UNCONFIRMED_REQUEST, SERVICE_UNCONFIRMED_COV_NOTIFICATION])
                          and monitored in frame.payload)


def write_then_notified(client, port, object_type, property_identifier, octets):
    """WriteProperty, then wait up to 3 s for this object's COV notification."""
    client.frames.clear()
    answer = client.write_property(port, object_type, 1, property_identifier, octets, timeout=2.0)
    found = client.wait_for(is_notification(object_type, 1), 3.0)
    # The notification reports the write's effect, so it follows the WriteProperty's SimpleACK.
    after_ack = (found is not None and answer.frame is not None
                 and client.frames.index(found) > client.frames.index(answer.frame))
    return answer, found, after_ack


def main():
    args = parser().parse_args()
    reader = wiretest.start(args.exe, ["--port", args.port], "B-ACCR")
    client = wiretest.Client(retries=1)
    try:
        for label, object_type in (("Analog Input 1", wiretest.OBJECT_TYPE_ANALOG_INPUT),
                                   ("Credential Data Input 1", OBJECT_TYPE_CREDENTIAL_DATA_INPUT)):
            subscribed = client.request(subscribe_cov(object_type, 1, 60), args.port, timeout=2.0)
            initial = client.wait_for(is_notification(object_type, 1), 3.0)
            record(f"{label}: SubscribeCOV is accepted and the initial notification arrives",
                   subscribed.ok and initial is not None, f"{subscribed.describe()}; initial {'seen' if initial else 'none'}")
            steps = [("Out_Of_Service TRUE", OUT_OF_SERVICE, codec.application_boolean(True))]
            if object_type == wiretest.OBJECT_TYPE_ANALOG_INPUT:
                steps.append(("Present_Value 30.0 while out of service", PRESENT_VALUE, codec.application_real(30.0)))
            steps.append(("Out_Of_Service FALSE", OUT_OF_SERVICE, codec.application_boolean(False)))
            for text, property_identifier, octets in steps:
                answer, found, after_ack = write_then_notified(client, args.port, object_type, property_identifier,
                                                               octets)
                record(f"{label}: WriteProperty {text} -> SimpleACK, then a COV notification for the object",
                       answer.ok and found is not None and after_ack,
                       f"{answer.describe()}; notification "
                       f"{('seen, but before the SimpleACK' if not after_ack else 'seen') if found else 'not seen in 3 s'}")
            # Cancel the subscription (SubscribeCOV with neither Issue Confirmed Notifications nor Lifetime).
            client.request(lambda invoke_id: bytes([0x00, 0x05, invoke_id, 0x05])
                           + codec.context_unsigned(0, SUBSCRIBER_PROCESS_IDENTIFIER)
                           + codec.context_object_id(1, object_type, 1), args.port, timeout=2.0)
    finally:
        client.close()
        reader.stop()
    return summary()


if __name__ == "__main__":
    sys.exit(main())
