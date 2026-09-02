# Gorgona Architectural Design

## Overview

Most AI agent frameworks are built with recursive, probabilistic loops. When things go wrong, agents burn through API credits, contaminate repository contexts, or hallucinate credentials.

Gorgona was designed with a single goal: **Deterministic Control**.

## Architectural Pillars

### 1. Zero External Dependencies
Gorgona requires only Python 3.10+ standard libraries. No heavy vector databases, no massive framework bloat, and no hidden telemetry. It can be installed in minimal containers and edge runners instantly.

### 2. Guardrails First
Every operation goes through sequential deterministic checks:
- **Exposure Guard**: Scans buffers and file trees for high entropy keys and tokens before disk write or network push.
- **Isolation Guard**: Ensures separate brand contexts and customer data never intermix.
- **Text Cleaner Guard**: Enforces pristine prose style and bans AI fluff phrases and em-dashes.
- **Memory Graph Guard**: Graph cycle detection via depth-first search to break infinite agent loops.

### 3. Failsafe Default
If any guard triggers an alert, the default action is immediate termination (freezing the agent to stone). No silent recoveries, no auto-retries that burn budget.
