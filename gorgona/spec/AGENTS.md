# Gorgona Agent Specification & Protocol

This document outlines the operational protocol for autonomous agents governed by Gorgona.

## 1. Core Mandate

Agents operate under hard, deterministic guardrails. When an agent exceeds depth boundaries, leaks credentials, crosses brand perimeters, or introduces stylistic slop, Gorgona halts execution immediately.

## 2. Hard Limits

1. **Repetition Limit**: No agent tool step may execute more than 3 times consecutively with identical inputs.
2. **Context Horizon**: Reasoning graphs deeper than 32 nodes trigger automated pruning.
3. **Secret Isolation**: Unmasked API keys, Bearer tokens, or private RSA keys cause hard crashes with exit code 1.
4. **Style Enforcement**: Zero em-dash policy across all public commits, markdown documents, and copy.

## 3. Delegation Pipeline

```
User Prompt
    │
    ▼
[Gorgona Router] ── (Heuristic: Complexity & Brand)
    │
    ├─ Fast Path (Deterministic Scripts / Small Models)
    └─ Reasoning Path (Large Autonomous Agents)
            │
            ▼
     [Exposure Guard]
            │
            ▼
     [Isolation Guard]
            │
            ▼
     [Text Cleaner]
            │
            ▼
    Safe Output Verified
```
