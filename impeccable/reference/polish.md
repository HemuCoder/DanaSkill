<!-- DanaSkill local modification: explicit-device-scope.1 (2026-11-18). -->
> **Additional context needed**: quality bar and shipping constraints.

Polish is refinement, never concealed redesign. Preserve the incumbent visual world, content, behavior, and everything outside scope. If the concept itself is wrong, say so and recommend redesign or `bolder` instead of smuggling in a replacement.

A detector result is defect evidence, not proof of quality. Inspect the rendered experience and real interaction path.

## 1. Establish the system

Read DESIGN.md and representative tokens, shared components, patterns, and neighboring flows. If no formal system exists, use coherent project conventions.

Classify each drift before fixing it:

- **missing token:** the system needs a reusable value;
- **one-off implementation:** an existing shared component or pattern should replace it;
- **conceptual mismatch:** the flow, information architecture, or hierarchy differs from comparable product areas;
- **local defect:** the implementation is simply incomplete or inconsistent.

Fix the cause at the narrowest correct level. Ask when a binding system principle cannot be inferred.

## 2. Gather the evidence

Use the feature yourself at the target sizes resolved under [Device scope](../SKILL.md#device-scope): the requested or actual desktop viewport by default on the web; mobile and tablet only when explicitly requested. On a native platform (`ios` / `android` / `adaptive`), use the shipped device classes on the simulator, emulator, or hardware, captured per the platform reference's Verifying the build section. Determine:

- whether the path is functionally complete;
- the intended quality bar and time available;
- known constraints or deliberately unfinished work;
- the states, content lengths, roles, and input methods users will actually encounter.

Only when mobile web is explicitly in scope, read the [Mobile Web Task Contract](adapt.md#mobile-web-task-contract). Identify the scoped tasks this pass can affect; size screenshots alone establish neither mobile support nor task usability. Reuse current, still-applicable task evidence for pure visual edits and retest only what the change may affect. Do not expand a local polish pass into a whole-site audit.

If a prior critique exists, use it as one input:

```bash
.agents/skills/impeccable/scripts/impeccable critique-storage latest "<resolved target>" --json
```

Exit 0 returns JSON with the latest snapshot's `body` and an exact `snapshot_file` identity. Retain `snapshot_file` until the end of the pass. For a local file target, the helper compares the file's exact current content fingerprint with the fingerprint captured by critique. Unchanged staged, unstaged, or untracked content remains current; any byte change, deletion, or replacement with a non-file closes the backlog it identified while preserving its trend history and exits 2. A URL target has no local fingerprint and remains current until explicitly closed. When current, incorporate relevant P0/P1 findings from `body` and name the snapshot read. Exit 2 means none exists or the target changed. Perform an independent pass either way.

## 3. Triage

Separate functional defects from cosmetic ones and fix in this order:

1. broken or blocked tasks, data loss, misleading state, and inaccessible paths;
2. missing loading, empty, error, success, disabled, and permission states;
3. flow, hierarchy, responsive, and design-system drift;
4. visual and motion inconsistencies;
5. code and asset cleanup.

Do not perfect one corner while leaving the rest below the same quality bar.

## 4. Polish the whole path

### Flow and hierarchy

- Match neighboring mental models, terminology, disclosure, routing, save behavior, and optimistic or pessimistic patterns.
- Make the primary task and current state obvious without flattening every element to equal weight.
- Ensure arrival, transition, empty, and recovery paths connect instead of behaving as isolated screens.

### Layout and type

- Align to the project's grid and spacing scale; fix optical as well as mathematical alignment.
- Group related content tightly and separate distinct groups generously.
- Keep same-role typography consistent; test measure, wrapping, localization expansion, zoom, and font loading.
- Verify the affected surface at the resolved target viewports.

### Color, imagery, and icons

- Use semantic tokens and stable color meanings across themes.
- Verify text, control, and focus contrast in every state.
- Keep icon families, stroke/weight, sizing, and optical alignment coherent.
- Prevent image layout shift; use correct aspect ratios, responsive sources, and useful alt text.

### Interaction and state

- Every control needs appropriate default, hover, focus, active, disabled, loading, error, and success behavior.
- Preserve visible keyboard focus, logical tab order, labels, and platform-appropriate touch targets.
- Keep motion coherent, interruptible, and performant. Do not add animation merely to make polish visible.
- Validate long, missing, localized, offline, slow, and permission-limited content where the product can encounter it.

### Content and code

- Keep terminology, capitalization, punctuation, and factual copy consistent. Ask before changing claims.
- Remove debug output, dead code, unused imports, obsolete styles, and polish-created duplication.
- Replace custom implementations with shared components where the system owns the pattern.
- Promote genuinely reusable values to tokens; do not create a system abstraction for one local exception.

## 5. Verify and finish

Walk affected core task paths from entry to completion with the applicable input methods. Only when mobile web is explicitly in scope, recheck relevant discovery, touch actions, on-screen keyboard visibility, submission, back navigation, state restoration, and failure recovery under the [Mobile Web Task Contract](adapt.md#mobile-web-task-contract). Pure visual changes require checks proportional to their effect on these paths, not unrelated full interaction suites. Check within this scope:

- the resolved target viewports on the web, normally one representative size per requested device class; the shipped device classes in supported orientations on native;
- loading, empty, error, success, disabled, long-content, and missing-content states;
- zoom, contrast, focus, semantics, and screen-reader names;
- console errors, layout shift, interaction latency, and image loading everywhere; supported browsers on the web; supported OS versions, runtime warnings, and dropped frames on native;
- agreement with DESIGN.md, neighboring features, and the user's scope.

Only for explicitly scoped mobile web, record the mobile task verdict and evidence in `.impeccable/review/mobile-tasks.md` or the existing equivalent report: input method, engine/version, device or emulation, actions, outcomes, and gaps. Synthesized touch is valid for the interactions it exercises; text entry alone cannot prove soft-keyboard behavior. Missing hardware is not automatically a failure. If an affected core task fails or cannot be exercised, report `fail` or `unverified` with the concrete limitation; do not declare mobile acceptance complete or keep retrying without new evidence. Desktop work needs no mobile task report or verdict.

Follow the quality guidance supplied by `impeccable context` and hooks, then run any other relevant QA commands. Context requests a manual scan only when no automatic detector is active; never add another detector pass. Fix real defects and document only narrow intentional exceptions. A clean scan does not replace visual judgment.

Finish with a source diff: remove accidental churn, orphaned code, redundant values, and temporary artifacts. Ship only when the feature is functionally complete and consistently finished across the path.

When this pass clears every Priority Issue it took from a snapshot, close that snapshot:

```bash
.agents/skills/impeccable/scripts/impeccable critique-storage close "<resolved target>" "<snapshot_file returned by latest>"
```

This closes only the snapshot this pass actually processed; if a newer critique landed meanwhile, its backlog stays live. Do not close when no snapshot was read, when `snapshot_file` was not retained, or when Priority Issues remain.
