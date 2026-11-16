# ADR-0001: PostgreSQL as the only database

Status: accepted
Date: 2026-11-13

## Context

Scheduling needs transactions and constraints; the team knows PostgreSQL.

## Decision

Use PostgreSQL for all data.

## Alternatives

- MongoDB: no multi-row transactions needed by bookings.

## Consequences

- One store to back up and monitor.
