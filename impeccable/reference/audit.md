<!-- DanaSkill local modification: explicit-device-scope.1 (2026-11-18). -->
Run systematic **technical** quality checks and generate a comprehensive report. Don't fix issues; document them for other commands to address.

This is a code-level audit, not a design critique. Check what's measurable and verifiable in the implementation.

**Web only.** Native platforms (`ios` / `android` / `adaptive`) route to [audit.native.md](audit.native.md) instead; if the project is native, switch to it now.

## Diagnostic Scan

Run comprehensive checks across 5 dimensions. Score each dimension 0-4 using the criteria below.

### 1. Accessibility (A11y)

**Check for**:
- **Contrast issues**: Text contrast ratios < 4.5:1 (or 7:1 for AAA)
- **Motion sensitivity**: `prefers-reduced-motion` needs an intentional alternative that preserves state change and hierarchy; flag a global `0.01ms` kill that destroys useful feedback, flashing above threshold, and motion that blocks focus, reading, or task completion
- **Missing ARIA**: Interactive elements without proper roles, labels, or states
- **Keyboard navigation**: Missing focus indicators, illogical tab order, keyboard traps
- **Semantic HTML**: Improper heading hierarchy, missing landmarks, divs instead of buttons
- **Alt text**: Missing or poor image descriptions
- **Form issues**: Inputs without labels, poor error messaging, missing required indicators

**Score 0-4**: 0=Inaccessible (fails WCAG A), 1=Major gaps (few ARIA labels, no keyboard nav), 2=Partial (some a11y effort, significant gaps), 3=Good (WCAG AA mostly met, minor gaps), 4=Excellent (WCAG AA fully met, approaches AAA)

### 2. Performance

**Check for**:
- **Layout thrashing**: Reading/writing layout properties in loops
- **Expensive animations**: Casual layout-property animation, unbounded blur/filter/shadow effects, or effects that visibly drop frames
- **Missing optimization**: Images without lazy loading, unoptimized assets
- **will-change overuse**: `will-change` applied broadly or left on at rest (it is a targeted hint for known expensive animations, not a baseline requirement)
- **Bundle size**: Unnecessary imports, unused dependencies
- **Render performance**: Unnecessary re-renders, missing memoization

**Score 0-4**: 0=Severe issues (layout thrash, unoptimized everything), 1=Major problems (no lazy loading, expensive animations), 2=Partial (some optimization, gaps remain), 3=Good (mostly optimized, minor improvements possible), 4=Excellent (fast, lean, well-optimized)

### 3. Theming

**Check for**:
- **Hard-coded colors**: Colors not using design tokens
- **Broken dark mode**: Missing dark mode variants, poor contrast in dark theme
- **Inconsistent tokens**: Using wrong tokens, mixing token types
- **Theme switching issues**: Values that don't update on theme change

**Score 0-4**: 0=No theming (hard-coded everything), 1=Minimal tokens (mostly hard-coded), 2=Partial (tokens exist but inconsistently used), 3=Good (tokens used, minor hard-coded values), 4=Excellent (full token system, dark mode works perfectly)

### 4. Responsive Design and Mobile Task Usability

Resolve target viewports under [Device scope](../SKILL.md#device-scope); ordinary Web audits use the requested or actual desktop viewport. Only when mobile web is explicitly in scope, follow the [Mobile Web Task Contract](adapt.md#mobile-web-task-contract) for the audited tasks. Exercise those tasks from entry to completion, including applicable input, submission, back navigation, state restoration, and failure recovery. Existing CSS, product context, and inferred usage do not add mobile checks.

**Check for**:
- **Fixed widths**: Hard-coded widths that break at the resolved target viewports
- **Touch targets, when touch is in scope**: Check the skill's 44×44 CSS-pixel usability target and spacing; distinguish this design target from any cited accessibility requirement
- **Broken touch interaction, when touch is in scope**: Mouse-only controls, hidden hover actions, failed taps or gestures, scroll conflicts, and interrupted drags that remain stuck. Exercise applicable touch interactions; inspect cancellation, lost capture, and `touch-action` where relevant
- **Blocked mobile tasks, when mobile is in scope**: Undiscoverable or unreachable actions, keyboard-obscured input or submission, lost list position or filters on return, and lost work during applicable interruption or retry paths
- **Horizontal scroll**: Unintended page overflow or scroll regions that hide required actions; task-justified horizontal comparison can remain
- **Text scaling**: Layouts that break when text size increases
- **Target widths**: Missing usable compositions at the resolved target widths; intrinsic layouts can work without explicit breakpoint variants

**Score 0-4** for responsive presentation within the resolved device scope: 0=Broken at target sizes, 1=Major layout or target-size issues, 2=Partial with significant gaps, 3=Good with minor issues, 4=Fluid and usable presentation across tested target sizes. Report untested required sizes; unrequested mobile sizes are outside scope. For mobile work, this score never substitutes for the separate mobile task verdict below.

### 5. Implementation Integrity (CRITICAL)

Run the bundled detector and verify each finding in context. Look for repeated implementation shortcuts, design-system drift, misleading or decorative content, and structure that is interchangeable with an unrelated product. Keep deterministic findings separate from visual judgment and call out false positives.

**Score 0-4**: 0=systemic drift, 1=major repeated failures, 2=several verified issues, 3=minor isolated issues, 4=coherent and intentional

## Generate Report

### Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | ? | [most critical a11y issue or "--"] |
| 2 | Performance | ? | |
| 3 | Theming | ? | |
| 4 | Responsive Presentation | ? | |
| 5 | Implementation Integrity | ? | |
| **Total** | | **??/20** | **[Rating band]** |

**Rating bands**: 18-20 Excellent (minor polish), 14-17 Good (address weak dimensions), 10-13 Acceptable (significant work needed), 6-9 Poor (major overhaul), 0-5 Critical (fundamental issues)

### Mobile Task Verdict

Include this section only when mobile web is explicitly in scope under [Device scope](../SKILL.md#device-scope). Report independently of **??/20**, using the [Mobile Web Task Contract](adapt.md#mobile-web-task-contract): **pass** when scoped core tasks are demonstrated, **fail** when an observed blocker prevents completion, or **unverified** when required interaction evidence is missing. An observed failure remains a failure even if other tasks are unverified. A high overall score cannot clear either failed or unverified mobile acceptance. Desktop audits need no mobile verdict or mobile task report.

Record task actions, observed results, and coverage gaps in `.impeccable/review/mobile-tasks.md`, or reference the project's existing equivalent report. Distinguish viewport screenshots, synthesized touch input, browser engine/version, and physical-device evidence. Existing tools that synthesize touch can establish what they actually exercise; missing hardware alone is not a failure. Keyboard text entry does not verify the on-screen keyboard or its occlusion. If core interaction cannot be executed, report `unverified` and the concrete limitation; do not invent results, require device access, or retry indefinitely.

### Implementation Integrity Verdict
**Start here.** Pass/fail: does the implementation express a coherent product-specific system? Cite verified evidence and detector findings.

### Executive Summary
- Audit Health Score: **??/20** ([rating band])
- Mobile Task Verdict, only when mobile is in scope: **pass / fail / unverified**, with evidence scope and remaining gaps
- Total issues found (count by severity: P0/P1/P2/P3)
- Top 3-5 critical issues
- Recommended next steps

### Detailed Findings by Severity

Tag every issue with **P0-P3 severity**:
- **P0 Blocking**: Prevents task completion. Fix immediately
- **P1 Major**: Significant difficulty or WCAG AA violation. Fix before release
- **P2 Minor**: Annoyance, workaround exists. Fix in next pass
- **P3 Polish**: Nice-to-fix, no real user impact. Fix if time permits

For each issue, document:
- **[P?] Issue name**
- **Location**: Component, file, line
- **Category**: Accessibility / Performance / Theming / Responsive / Implementation Integrity
- **Impact**: How it affects users
- **WCAG/Standard**: Which standard it violates (if applicable)
- **Recommendation**: How to fix it
- **Suggested command**: Which command to use (prefer: $impeccable adapt, $impeccable animate, $impeccable audit, $impeccable bolder, $impeccable clarify, $impeccable colorize, $impeccable critique, $impeccable delight, $impeccable distill, $impeccable document, $impeccable harden, $impeccable layout, $impeccable onboard, $impeccable optimize, $impeccable overdrive, $impeccable polish, $impeccable quieter, $impeccable shape, $impeccable typeset)

### Patterns & Systemic Issues

Identify recurring problems that indicate systemic gaps rather than one-off mistakes:
- "Hard-coded colors appear in 15+ components, should use design tokens"
- "Touch targets consistently too small (<44px) throughout mobile experience"

### Positive Findings

Note what's working well: good practices to maintain and replicate.

## Recommended Actions

List recommended commands in priority order (P0 first, then P1, then P2):

1. **[P?] `$command-name`**: Brief description (specific context from audit findings)
2. **[P?] `$command-name`**: Brief description (specific context)

**Rules**: Only recommend commands from: $impeccable adapt, $impeccable animate, $impeccable audit, $impeccable bolder, $impeccable clarify, $impeccable colorize, $impeccable critique, $impeccable delight, $impeccable distill, $impeccable document, $impeccable harden, $impeccable layout, $impeccable onboard, $impeccable optimize, $impeccable overdrive, $impeccable polish, $impeccable quieter, $impeccable shape, $impeccable typeset. Map findings to the most appropriate command. End with `$impeccable polish` as the final step if any fixes were recommended.

After presenting the summary, tell the user:

> You can ask me to run these one at a time, all at once, or in any order you prefer.
>
> Re-run `$impeccable audit` after fixes to see your score improve.

**IMPORTANT**: Be thorough but actionable. Too many P3 issues creates noise. Focus on what actually matters.

**NEVER**:
- Report issues without explaining impact (why does this matter?)
- Provide generic recommendations (be specific and actionable)
- Skip positive findings (celebrate what works)
- Forget to prioritize (everything can't be P0)
- Report false positives without verification
