# BACnet Protocol Implementation Conformance Statement (PICS)

For the **BACnet B-ACCR (Access Control Credential Reader) C++ example** -
see [README.md](../README.md).

> This is the PICS **for the example as shipped**. It describes a tutorial
> device announcing itself as a Chipkin demo, not a product. When you turn this
> example into your own device, this document is one of the things you rewrite:
> the vendor, model and version rows all come from the
> `CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of `main.cpp`. The
> example has **not** been submitted for BTL certification.

## 1. Product description

| | |
|---|---|
| **Vendor Name** | Chipkin Automation Systems |
| **Vendor Identifier** | 389 |
| **Product Name** | CAS BACnet Stack Example - B-ACCR |
| **Product Model Number** | CAS BACnet Stack Example - B-ACCR |
| **Application Software Version** | 1.1.0 (`APP_VERSION` in `main.cpp`) |
| **Firmware Revision** | the linked CAS BACnet Stack version (6.0.23.0 at this Stack Pin) |
| **BACnet Protocol Version** | 1 |
| **BACnet Protocol Revision** | 30 |

**Product Description:** a BACnet/IP access control credential reader built on
the CAS BACnet Stack. It presents the three base sensor objects (Analog Input,
Binary Input, Multi-State Input) shared across this example series plus a
Credential Data Input object reporting the last credential presented at the
door, answers ReadProperty for every required property of every object,
accepts WriteProperty of `Out_Of_Service` on its four input-family objects,
pushes changes to subscribers with SubscribeCOV instead of requiring polling,
and is discoverable by Who-Is / I-Am and Who-Has / I-Have. It is the series'
canonical source for the SubscribeCOV (F-COV) pattern, and a tutorial for
implementers of the B-ACCR profile.

## 2. BACnet standardized device profile (Annex L)

**B-ACCR - BACnet Access Control Credential Reader** (Annex L.7,
Miscellaneous).

This device claims exactly one profile. Because the B-ACCR requirements are a
superset of B-GENERAL's, a conformant B-ACCR device also satisfies
**B-GENERAL** (Annex L.8); that is subsumption, not a second claim.

## 3. BIBBs supported (Annex K)

| BIBB | Description |
|---|---|
| DS-RP-B | Data Sharing - ReadProperty - B |
| DS-WP-B | Data Sharing - WriteProperty - B |
| DS-COV-B | Data Sharing - COV - B |
| DS-ACCDI-B | Data Sharing - Access Credential Data Input - B |
| DM-DDB-B | Device Management - Dynamic Device Binding - B |
| DM-DOB-B | Device Management - Dynamic Object Binding - B |

No other BIBBs are supported. In particular this device does **not** support
DS-RPM-B (ReadPropertyMultiple), DS-WPM-B (WritePropertyMultiple), any alarm
and event (AE-*) BIBB, scheduling (SCHED-*), trending (T-*), or
DM-DCC-B (DeviceCommunicationControl).

## 4. Application services supported

| Service | Initiate | Execute |
|---|:---:|:---:|
| ReadProperty | no | **yes** |
| WriteProperty | no | **yes** |
| SubscribeCOV | no | **yes** |
| ConfirmedCOVNotification | **yes** | no |
| UnconfirmedCOVNotification | **yes** | no |
| Who-Is | no | **yes** |
| I-Am | **yes** | - |
| Who-Has | no | **yes** |
| I-Have | **yes** | - |

An unsolicited I-Am is broadcast to the local subnet at start-up, as well as in
response to Who-Is. A COV notification (confirmed or unconfirmed, per the
subscription) is sent to a subscriber whenever the subscribed property changes
and the application reports that change with `BACnetStack_UpdateValue`.

Any other confirmed service - including ReadPropertyMultiple and
WritePropertyMultiple - is rejected. That rejection is part of the profile
boundary, not a limitation to work around.

## 5. Segmentation capability

Segmentation is **supported in both directions**
(`Segmentation_Supported` = `segmented-both`), by the stack: at `6.x` @
`69b6249f` the customer build compiles `STACK_OPTION_SEGMENTATION` in (stack
#2992), and this example keeps the stack's defaults - `Max_Segments_Accepted`
16 and `APDU_Segment_Timeout` 5000 ms, as read from the running device. Table
12-13 footnote 1: "These properties are required if, and shall be present only
if, segmentation of any kind is supported" - they are not rows in section 11
because its generator lists only unconditionally required properties.
`Max_APDU_Length_Accepted` is 1476 octets, the BACnet/IP maximum. (This section
used to say `no-segmentation`.)

## 6. Standard object types supported

No object is dynamically creatable or deletable. `Out_Of_Service` is writable
on the four input-family objects (Analog Input, Binary Input, Multi-State
Input, Credential Data Input). While an object's `Out_Of_Service` is TRUE, its
`Present_Value` is writable too (Analog, Binary and Multi-State Input; cl.
12.2.4 and footnote 1 of Tables 12-2, 12-5 and 12-19), and so is the Credential
Data Input's `Reliability` (Table 12-43 footnote 1): the written value is what
clients read until `Out_Of_Service` returns to FALSE. The Credential Data
Input's `Present_Value` is not writable even then - the stack's customer
interface has no callback that carries a `BACnetAuthenticationFactor` write
(`TODO.md`). No other property of any object is writable.

| Object type | Instance | Object_Name | Optional properties supported |
|---|:---:|---|---|
| Device | 389012 | Chipkin Example B-ACCR | Description |
| Analog Input | 1 | Bronze | - |
| Binary Input | 1 | Emerald | - |
| Multi-State Input | 1 | Hot Pink | State_Text |
| Credential Data Input | 1 | Flax | - |
| Network Port | 1 | Vermilion | - |

The device instance is configurable at start-up with `--deviceID`, and the
Device's Object_Name with `--deviceName` (BACnet requires both to be
configurable, cl. 12.1.1.3 and 12.1.1.4). Changing either means restarting
the device; neither is writable over the network. The table shows the
defaults.

## 7. Data link layer options

**BACnet/IP (Annex J)**, UDP port 47808 (0xBAC0) by default, configurable at run
time with `--port`.

BBMD is not supported, Foreign Device registration is not supported, and
BACnet/SC, MS/TP, Ethernet (Annex H) and PTP are not supported.

## 8. Device address binding

Static device binding is **not supported**. The device answers Who-Is/Who-Has
and does not initiate any confirmed request to a peer it must first bind -
including a COV notification, which is sent to the address the subscription
itself supplied.

## 9. Networking options

None. The device is not a router, not a BBMD, and does not register as a
foreign device.

## 10. Character sets supported

UTF-8 (ANSI X3.4). Supporting a character set does not imply the device can
handle data in all character sets.

## 11. Objects and properties

<!-- OBJECTS-PROPERTIES:BEGIN (generated by tools/gen-objects-properties.py from docs/objects.json - do not edit here) -->
Every object this example creates, and every REQUIRED property of each (per ANSI/ASHRAE 135-2024 clause 12 and the CAS BACnet Stack's property profiles), plus the optional properties the example turns on. **Served by** says who answers a ReadProperty: the **stack** generates it, or the **app** serves it from a `GetProperty*` callback in `main.cpp`. A ⚠ row is a required property the app does not serve and the stack would fill with a default - that is a defect, not a feature.

### Device 389012 "Chipkin Example B-ACCR" - the device itself; the instance is configurable with --deviceID and the Object_Name with --deviceName (both at start-up; the heading shows the defaults). The stack rows are device-wide facts only the stack knows - the protocol version and revision it implements, the services and object types it was configured with, the live object list and address-binding table, and Database_Revision, which the stack starts at 0 and increments for each object added at start-up: it reads 6 (the Device, Analog Input 1, Binary Input 1, Multi-state Input 1, Credential Data Input 1 and Network Port 1) and stays 6, because nothing creates, deletes or renames an object afterwards (a card presentation or an Out_Of_Service write changes a value, not the object database). The accepted rows are the stack's configured defaults for APDU limits, segmentation and system status; an application that answered them from its own constants could contradict the stack, so this example does not

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| System_Status | BACnetDeviceStatus | stack default, accepted (Generic Enumerated default: `0`) | no |
| Vendor_Name | CharacterString | app | no |
| Vendor_Identifier | Unsigned16 | app | no |
| Model_Name | CharacterString | app | no |
| Firmware_Revision | CharacterString | app | no |
| Application_Software_Version | CharacterString | app | no |
| Description *(optional, enabled)* | CharacterString | app | no |
| Protocol_Version | Unsigned | stack | no |
| Protocol_Revision | Unsigned | stack | no |
| Protocol_Services_Supported | BACnetServicesSupported | stack | no |
| Protocol_Object_Types_Supported | BACnetObjectTypesSupported | stack | no |
| Object_List | BACnetARRAY[N] of BACnetObjectIdentifier | stack | no |
| Max_APDU_Length_Accepted | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_MAX_APDU_LENGTH_ACCEPTED`) | no |
| Segmentation_Supported | BACnetSegmentation | stack default, accepted (`BACnetSegmentation::segmentedBoth` with `STACK_OPTION_SEGME) | no |
| APDU_Timeout | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_APDU_TIMEOUT`) | no |
| Number_Of_APDU_Retries | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_NUMBER_OF_APDU_RETRIES`) | no |
| Device_Address_Binding | BACnetLIST of BACnetAddressBinding | stack | no |
| Database_Revision | Unsigned | stack | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

### Analog Input 1 "Bronze" - REAL, degrees Celsius; starts at 21.5; Present_Value COV-subscribable (F-COV canonical example). COV_Increment 1.0 (required: the object supports COV reporting, cl. 12.2.16)

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | Real | app | yes |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Units | BACnetEngineeringUnits | app | no |
| COV_Increment *(optional, enabled)* | Real | app | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

### Binary Input 1 "Emerald" - starts inactive

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | BACnetBinaryPV | app | yes |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Polarity | BACnetPolarity | app | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

### Multi-state Input 1 "Hot Pink" - state 1 of 3: On, Off, Auto

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | Unsigned | app | yes |
| Status_Flags | BACnetStatusFlags | stack | no |
| Event_State | BACnetEventState | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | yes |
| Number_Of_States | Unsigned | app | no |
| State_Text *(optional, enabled)* | BACnetARRAY[N] of CharacterString | app | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

### Credential Data Input 1 "Flax" - Present_Value is BACnetAuthenticationFactor (a 4-byte simple-number32 card ID, served via the OctetString callback; the stack always reports Format-Type 0 = UNDEFINED and Format-Class 0, so every read means "no current authentication factor" (cl. 12.36.4) - a stack gap that makes this a Blocked Example, see README.md); Supported_Formats is served via RegisterCallbackGetPropertyAuthenticationFactorFormat, Update_Time via the Time callback, which the stack wraps into a BACnetTimeStamp. Update_Time - NOT Present_Value - is the COV-subscribable property for this object type (135-2024 Table 13-1; F-COV canonical example, see TUTORIAL.md); the notification payload still carries Present_Value. The up/down keys simulate a new card presentation

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | BACnetAuthenticationFactor | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Reliability | BACnetReliability | app | yes |
| Out_Of_Service | Boolean | app | yes |
| Supported_Formats | BACnetARRAY[N] of BACnetAuthenticationFactorFormat | app | no |
| Update_Time | BACnetTimeStamp | app | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

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
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

<!-- OBJECTS-PROPERTIES:END -->

## 12. References

- ANSI/ASHRAE Standard 135-2024, Annex A (PICS template), Annex K (BIBBs),
  Annex L (device profiles), Clause 12 (object types).
- [README.md](../README.md) - what this example is and how to build it.
- [TUTORIAL.md](../TUTORIAL.md) - how to extend it, and how to keep this
  document honest when you do.
