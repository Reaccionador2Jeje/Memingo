# AtDev Billing — Hybrid plans (Memingo)

**Status:** proposal only. Memingo language, interpreter, CLI, documentation, and self-hosted tooling remain free to use.

## Free-first model

Do not charge users to write, run, inspect, or learn the Memingo language. Optional paid offerings may include AtDev-hosted package distribution, hosted build automation, team collaboration, or convenience services. Core language functionality must not depend on a subscription.

## Proposed plans (CLP/month; exploratory)

| Plan | Reference price | Benefits |
| --- | ---: | --- |
| Community | $0 | Language, interpreter, CLI, docs, and local projects |
| Package Starter | $490 | Optional hosted package namespace with small quotas, when available |
| Developer | $990 | Higher hosted package/build quotas and project insights |
| Team | $1,990 | Shared namespaces and collaboration conveniences, when implemented |

Do not advertise features that do not exist. Prices are placeholders pending infrastructure cost and demand validation.

## Suggested entitlements

- `packages.hosted.private_namespaces`
- `packages.hosted.storage_bytes`
- `builds.hosted.monthly`
- `projects.collaboration.seats`
- `analytics.project.advanced`

The local compiler/interpreter must continue working if Billing is unavailable. Enforce hosted quotas on the server. Never put secrets or payment credentials in source control.

## Launch gates

Build the hosted service first, document data export/deletion and package ownership, test authorization and quota enforcement, and obtain adult account-owner review of payment-provider eligibility and legal/tax obligations. No real-money checkout is active.
