# ADR-003: Store Device State and Timelines in SQLite

## Status

Accepted

## Context

The simulator needs durable local state, event history, and simple inspection without adding operational overhead.

## Decision

Use SQLite for:

- current per-device state
- append-only timeline events

Expose that data through the REST API instead of requiring direct database access during the demo.

## Consequences

- Local persistence stays simple and portable.
- Re-runs can demonstrate idempotency and recovery.
- The repo remains easy to reset by deleting one database file when needed.
