# Architectural Decision Records (ADRs)

This directory contains Architectural Decision Records for the Sense Observability Platform.

## What is an ADR?

An Architectural Decision Record (ADR) captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:
- **Title**: Short descriptive name
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: What is the issue we're facing?
- **Decision**: What decision did we make?
- **Consequences**: What are the positive and negative outcomes?
- **Alternatives Considered**: What other options did we consider?

## Index

### Security & Reliability
- [ADR-001: SSL Certificate Verification](001-ssl-certificate-verification.md)
- [ADR-002: Request Size Limits for DoS Protection](002-request-size-limits.md)
- [ADR-003: Queue Backpressure Strategy](003-queue-backpressure.md)

### Architecture & Patterns
- [ADR-004: Repository Pattern for MDSO (Multi-Domain Service Orchestrator) Access](004-repository-pattern-mdso.md)
- [ADR-005: Redis State Externalization](005-redis-state-externalization.md)
- [ADR-006: Dependency Injection Container](006-dependency-injection.md)

### Code Organization
- [ADR-007: Shared Library Extraction](007-shared-library-extraction.md)
- [ADR-008: Test Coverage Strategy](008-test-coverage-strategy.md)

## Creating a New ADR

Use this template:

```markdown
# ADR-XXX: [Title]

**Status**: [Proposed | Accepted | Deprecated | Superseded]
**Date**: YYYY-MM-DD
**Authors**: [Names]
**Supersedes**: [ADR-XXX if applicable]

## Context

[What is the issue that we're seeing that motivates this decision or change?]

## Decision

[What is the change that we're proposing and/or doing?]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

## Alternatives Considered

### Alternative 1: [Name]
- **Pros**: ...
- **Cons**: ...
- **Why not chosen**: ...

## Implementation

[How will this be implemented? What are the steps?]

## References

- [Relevant documentation]
- [Related ADRs]
```

## Contributing

When making significant architectural decisions:
1. Create a new ADR with the next number
2. Follow the template above
3. Get review from team leads
4. Update the index in this README
5. Reference the ADR in code comments where relevant

## Reviewing ADRs

ADRs should be reviewed regularly (e.g., quarterly) to ensure they're still relevant and update status if needed.
