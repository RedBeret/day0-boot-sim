# ADR-004: Generate a Deterministic Synthetic PCAP

## Status

Accepted

## Context

The training repo needs a packet artifact, but raw packet capture on Windows-hosted Docker environments adds privileges and host dependency issues.

## Decision

Use a sidecar service that watches timeline events and writes a deterministic PCAP that mirrors the synthetic workflow.

## Consequences

- Learners get a packet artifact they can inspect in Wireshark.
- The capture is stable and repeatable across machines.
- The result is representative rather than a literal host sniff.
