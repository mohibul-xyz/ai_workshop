# F05 — Task tags

> Status: approved   ·   Owner: workshop facilitator   ·   Feature: `feature_list.json` → F05

## 1. Problem
Teams want to group tasks across statuses ("urgent", "backend", "release-1.2") without
creating more projects. Today the only grouping is status and priority.

## 2. User stories
- As a team member, I want to attach tags to a task when I create or edit it, so that I can group related work.
- As a team lead, I want to list a project's tasks with a given tag, so that I can review one stream of work.

## 3. API contract

| Method | Path | Request | Success | Errors |
|---|---|---|---|---|
| `POST` | `/api/v1/projects/{id}/tasks` | `TaskCreate` + optional `"tags": ["urgent", "ops"]` | `201`, `TaskRead` with `"tags"` | `422` invalid tag |
| `PATCH` | `/api/v1/tasks/{id}` | optional `"tags": [...]` **replaces** the set; omitted = unchanged | `200`, `TaskRead` | `404`, `422` |
| `GET` | `/api/v1/projects/{id}/tasks?tag=urgent` | `tag` query param | `200`, tasks having that tag | `404` project, `422` invalid tag |
| `GET` | `/api/v1/tasks/{id}` | — | `200`, includes `"tags"` | `404` |

Tag rules:
- A tag is 1–32 chars of lowercase `a-z`, `0-9`, `-`; input is trimmed and lowercased first.
  Anything else → `422`.
- `tags` in responses is always present: a list of strings sorted alphabetically, `[]` if none.
- Duplicates in the request are collapsed (`["ops", "OPS"]` → `["ops"]`).
- At most 10 tags per task → otherwise `422`.

## 4. Data model
- `tags`: `id` PK, `name` `String(32)` unique (`uq_tags_name`), not null.
- `task_tags`: `task_id` FK → `tasks.id` `ON DELETE CASCADE`, `tag_id` FK → `tags.id`
  `ON DELETE CASCADE`, composite PK (`task_id`, `tag_id`), index on `tag_id`.
- Tags are global (shared across projects) and created on first use.
- Migration `0003_add_tags` creates both tables; downgrade drops `task_tags` then `tags`.

## 5. Acceptance criteria

- **AC1 — create_with_tags**
  Given a project
  When I create a task with `"tags": ["urgent", "ops"]`
  Then the response is `201` and `"tags"` is `["ops", "urgent"]`.

- **AC2 — tags_default_empty**
  Given a project
  When I create a task without `tags`
  Then `"tags"` is `[]` in the response and in `GET /tasks/{id}`.

- **AC3 — tags_normalised_and_deduplicated**
  When I create a task with `"tags": [" Urgent ", "urgent", "OPS"]`
  Then `"tags"` is `["ops", "urgent"]`.

- **AC4 — invalid_tag_rejected**
  When I create a task with a tag that is empty, longer than 32 chars, or contains a space or `_`
  Then the response is `422` and no task is created.

- **AC5 — too_many_tags_rejected**
  When I create a task with 11 distinct tags
  Then the response is `422`.

- **AC6 — patch_replaces_tags**
  Given a task tagged `["a", "b"]`
  When I `PATCH` it with `"tags": ["c"]`
  Then `"tags"` is `["c"]`; and `PATCH` with `"tags": []` clears them.

- **AC7 — patch_without_tags_keeps_them**
  Given a task tagged `["a"]`
  When I `PATCH` only its `title`
  Then `"tags"` is still `["a"]`.

- **AC8 — filter_by_tag**
  Given tasks tagged `["urgent"]`, `["ops"]` and untagged in one project
  When I `GET .../tasks?tag=urgent`
  Then only the `urgent` task is returned.

- **AC9 — filter_by_tag_is_normalised_and_scoped**
  Given an `urgent` task in project A and one in project B
  When I `GET /projects/A/tasks?tag=URGENT`
  Then only project A's task is returned.

- **AC10 — filter_combines_with_other_filters**
  Given `urgent` tasks with status `todo` and `done`
  When I `GET .../tasks?tag=urgent&status=todo`
  Then only the `todo` one is returned.

- **AC11 — tags_shared_across_tasks**
  When two tasks are created with tag `ops`
  Then exactly one `ops` row exists in `tags`.

- **AC12 — deleting_task_removes_links_not_tags**
  Given a task tagged `ops`
  When I delete the task
  Then its `task_tags` rows are gone and the `ops` tag still exists.

## 6. Non-goals
- Tag CRUD endpoints (`/tags`), renaming or merging tags, tag colours.
- Filtering by several tags at once (`?tag=a&tag=b`) — a later feature.
- Per-project tag namespaces.

## 7. Open questions
- ~~Should tags be per project or global?~~ **Resolved:** global, created on first use (simpler; non-goal covers namespaces).
- ~~Does PATCH merge or replace?~~ **Resolved:** replace; omitted means unchanged.
