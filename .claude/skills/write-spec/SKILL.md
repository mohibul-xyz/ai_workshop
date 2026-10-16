---
name: write-spec
description: Write a feature spec for TaskHub before any code (spec-driven development). Use when asked to spec, design or plan a feature from feature_list.json, or when a feature has no file in specs/. Produces specs/<ID>-<slug>.md with Given/When/Then acceptance criteria, then a separate implementation plan.
---

# Write a spec (planner role)

You are the **planner**. You do not write code in this skill. A spec is the contract that the
generator implements and the evaluator (the `reviewer` subagent) checks against.

## 1. Gather context (read, don't guess)
- The feature entry in `feature_list.json` (`user_visible_behavior` is the seed).
- `docs/api-conventions.md` (URLs, fields, filters, pagination, errors).
- `docs/database-rules.md` if the data model changes.
- Existing code the feature touches (routers, services, models, tests).

## 2. Write `specs/<ID>-<slug>.md` from `specs/_template.md`
Fill every section:
1. **Problem** — who needs this and why, in 2–4 lines.
2. **User stories** — "As a … I want … so that …".
3. **API contract** — exact method, path, query params, request/response JSON with types,
   status codes for success and every error.
4. **Data model** — tables/columns/constraints/indexes and the migration it implies.
5. **Acceptance criteria** — numbered `AC1`, `AC2`, … each as **Given / When / Then**,
   observable through the API. Cover happy path, boundaries, errors, interaction with
   existing filters, and backward compatibility.
6. **Non-goals** — what this feature deliberately does not do.
7. **Open questions** — anything a human must decide. Do not silently pick an answer.

Rules for good criteria:
- One behaviour per AC; testable by a single test named `test_ac<N>_<slug>`.
- Concrete values (`tags=["urgent"]`), not adjectives ("works correctly").
- Every status code in the contract appears in some AC.

## 3. Stop for human review of the spec
Ask the human to answer the open questions and approve. Record the answers in the spec.

## 4. Write the plan `specs/<ID>-<slug>.plan.md` (still no code)
A numbered list of small steps. Each step names: files touched, the ACs it satisfies, and
the command that verifies it. The last steps are always: tests named after ACs →
`make lab-spec` → `make verify` → reviewer subagent → update `feature_list.json`.

## 5. Report
Spec path, plan path, number of ACs, open questions (resolved/unresolved).
