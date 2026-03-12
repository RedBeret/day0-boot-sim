# Study Guide

## Framing

Think of this repo as a safe sandbox for the bootstrapping phase that happens before a device is fully under management. The workflow is generic on purpose so you can learn the pattern without vendor lock-in.

## Concept Map

| Generic concept | In this repo | Real-world analog |
| --- | --- | --- |
| Device powers on | `POST /devices/{id}/boot` | A fresh device starting with minimal state |
| DHCP discovery | Synthetic metadata request | A device asking where to get bootstrap instructions |
| Boot file URI | `boot_file_uri` in the DHCP payload | A pointer to a script, image, or config blob |
| Config server URI | `config_server_uri` | A controller, registry, or config repository |
| Bootstrap apply | `APPLY_BOOTSTRAP` state | The first device-side configuration or registration step |
| Event timeline | `/devices/{id}/timeline` | Operational audit trail or provisioning logs |
| Packet capture | `pcaps/day0-boot-sim.pcap` | Packet evidence used for troubleshooting |

## What to Watch During the Demo

1. The state machine moves in a strict order.
2. DHCP data is enough to point the device at the next bootstrap artifact.
3. The bootstrap file is separate from the device state record.
4. The device timeline is as important as the final `READY` state.
5. Idempotency matters because Day 0 workflows are often retried.

## How This Relates to ZTP-Style Thinking

Vendor ZTP systems differ in details, but the mental model is consistent:

- A minimally aware endpoint asks for startup guidance.
- The environment returns enough metadata to fetch a bootstrap artifact.
- The artifact establishes identity, baseline config, or controller registration.
- Operators need a timeline when things go wrong.

This repo focuses on that common shape.

## Suggested Exercises

1. Run the happy-path demo.
2. Re-run the same demo and confirm the idempotent no-op event.
3. Trigger the missing bootstrap scenario and read the timeline.
4. Trigger the timeout-once scenario and find the retry event in both logs and timeline.
5. Open the generated PCAP in Wireshark and compare the synthetic DHCP and HTTP phases to the timeline JSON.

## Things to Compare

- Timeline event order versus the state machine diagram
- Structured logs versus the SQLite-backed API view
- Packet timestamps versus event timestamps
- Happy path versus failure modes
