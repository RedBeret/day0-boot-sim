# ADR-001: Use a Synthetic DHCP Metadata Service

## Status

Accepted

## Context

The training goal is to teach Day 0 bootstrapping on a Windows workstation. Raw DHCP behavior is awkward to expose safely from Docker Desktop on Windows and would distract from the provisioning mental model.

## Decision

Represent DHCP as a synthetic metadata service that returns the same information a bootstrapping workflow cares about:

- boot file URI
- config server URI
- fake serial
- fake model
- synthetic management IP

## Consequences

- The repo stays local, deterministic, and Windows-friendly.
- Learners still understand the role DHCP plays in steering the next step.
- The implementation is intentionally not a full DHCP appliance.
