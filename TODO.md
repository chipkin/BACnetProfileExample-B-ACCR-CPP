# TODO

Defects this example cannot fix itself.

## Blocked: a presented credential cannot be reported

This is a **Blocked Example**, blocked on
[chipkin/cas-bacnet-stack#3934](https://github.com/chipkin/cas-bacnet-stack/issues/3934)
(open). The README banner describes what the example does today.

- **Where:** the CAS BACnet Stack's customer interface.
- **What:** the stack wraps the application's OctetString callback for Credential
  Data Input `Present_Value` as `BACnetAuthenticationFactor(0, 0, ...)`, so every
  read reports Format-Type `0` (`UNDEFINED`), which clause 12.36.4 reserves for
  "no current authentication factor". The customer interface has no way to report
  the real Format-Type. At this Stack Pin (`6.x` @ `69b6249f`) the only way to set
  one is still the test-tool export `BACnetStackTestTool_PushCredentialDataInputFactor`,
  which a customer build does not have and this example does not use.
- **Also in #3934:** `Update_Time` has whole-second resolution, so two
  presentations within one second send one COV notification, not two.
- **Also in #3934:** while Credential Data Input 1 is out of service, its
  `Present_Value` should be writable (Table 12-43 footnote 1), but a write is
  refused write-access-denied: no customer Set callback carries a
  `BACnetAuthenticationFactor`. `tests/out_of_service_test.py` reports it as a
  `[KNOWN GAP]`.
- **When it is fixed:** report the card as `simple-number32`, rework the example
  to Profile-functional (Wire Tests that prove a presented credential reaches a
  Peer), and remove the Blocked banner.

## Coverage gaps the test tool still reports

No BTL FAIL remains at this release. The skipped rows are not example gaps:
8.2.14 / 8.3.16 (Credential Data Input COV rows, ref:
`chipkin/chipkin-bacnet-testing-tool#234`), 9.22.2.3 (ref:
`chipkin/chipkin-bacnet-testing-tool#172`) and 9.10.1.4 / .5 / .7 / .11 (ref:
`chipkin/chipkin-bacnet-testing-tool#733`).
