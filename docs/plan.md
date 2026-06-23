# Plan (STUB): B-ACCR (Access Control Credential Reader) — C++ example

> **STATUS: STUB.** Seed facts below. Expand from
> [`bacnet-profile-plan-template.md`](../../bacnet-profile-plan-template.md) after the
> sample plans ([B-LD](../../BACnetProfileExample-B-LD-CPP/docs/plan.md),
> [B-BC](../../BACnetProfileExample-B-BC-CPP/docs/plan.md)) are reviewed.

**Profile:** B-ACCR · **Family:** Annex L.7 (Miscellaneous) · **Role:** B ·
**Archetype:** Specialized-object · **Difficulty:** 2/5 · **Build wave:** 1

**Thesis:** a card/credential reader — reports the credential presented at a door
via a **Credential Data Input** object, pushed to subscribers with **COV**. This
example = B-SS baseline + COV + a CDI object. **Canonical source for F-COV.**

## Required BIBBs (profiles.md L.7)
`DS-RP-B, DS-WP-B, DS-COV-B, DS-ACCDI-B; DM-DDB-B, DM-DOB-B`. No AE/SCHED/T.

## Services to enable
- ReadProperty (1), WriteProperty (15), **SubscribeCOV (5)**. Baseline discovery.

## Objects (baseline + )
- Credential Data Input 1 (`OBJECT_TYPE_CREDENTIAL_DATA_INPUT`) — Present_Value is
  an **AuthenticationFactor** (constructed type), plus `Update_Time`,
  `Supported_Formats`, `Reliability`. Colour: extend table.

## Shared features
- **DEFINE:** F-COV (first SubscribeCOV — enable service 5; the stack issues COV
  notifications on value change; serve `COV_Increment` where applicable).
- **REUSE:** F-ACCESS (B-ACDC — CDI is an access object), F-OUTPUTS (B-SA writes).

## Known stack gaps
- **AuthenticationFactor datatype is fiddly.** Confirm how the standard DLL serves
  a CDI `Present_Value` (AuthenticationFactor) and that the **initial COV
  notification** carries presentValue + updateTime (profiles.md S62/S63 closed
  exactly these gaps; DS-ACCDI-B ✅ via `btl-auto-ds-accdi-b-cov`). The official
  `8-2-14`/`8-3-16` rows stay SKIP over a spec tag dispute — not our concern, but
  note it.

## Notes / open questions
- This is the first example whose new object Present_Value is **not** a simple
  scalar. If the standard DLL cannot serve AuthenticationFactor cleanly, document
  it as a gap and serve the simplest faithful representation.
