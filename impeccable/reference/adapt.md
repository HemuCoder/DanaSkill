<!-- DanaSkill local modification: explicit-device-scope.1 (2026-11-18). -->
> **Additional context needed**: target platforms/devices and usage contexts.

Adapt an existing design to a different context: another screen size, device, platform, or use case. The trap is treating adaptation as scaling. The job is rethinking the experience for the new context.

**Web only** (mobile web included). Native platforms (`ios` / `android` / `adaptive`) route to [adapt.native.md](adapt.native.md) instead; if the project is native, switch to it now.

## Mobile web task contract

Apply this contract only when mobile web is explicitly in scope under [Device scope](../SKILL.md#device-scope), including ordinary builds, refinements, and reviews. Read it without starting the rest of the `adapt` workflow. Existing responsive CSS, product category, and inferred usage do not activate it. A narrow screenshot alone establishes neither support nor usability. Reuse settled decisions within the requested scope; ask only when a missing product decision changes the work.

### Design the task before arranging the screen

Record a compact mobile task note in the existing surface brief, or in the working plan for a scoped change. Include the affected core tasks, real usage context and input methods, entry → action → completion → return path, state that must survive navigation or interruption, and the mobile interaction choices. A landing page may need only reading, navigation, and its primary action; an editor may need selection, editing, saving, and recovery. Phone use can be focused or interrupted: choose from product evidence. Extend existing context instead of creating a second product specification.

- Preserve product concepts, terminology, data, and business rules. Choose navigation, screen boundaries, information priority, and controls for the task and available space. Share logic and state where appropriate; a different mobile composition does not require a separate codebase.
- Multi-pane work can become list → detail → action with the list's filters and position restored on return. Keep comparison data together when comparison is the task. Vertical stacking, card conversion, bottom navigation, and sheets are options with tradeoffs, not automatic replacements.
- Provide discoverable tap actions for functions otherwise reached by hover, right-click, drag, or modifier-key selection. Gestures may accelerate an action; provide an accessible alternative for essential actions. Place frequent controls within comfortable reach while retaining context and content space.
- For input, use suitable field types, `inputmode`, autocomplete, and existing defaults to reduce typing. Keep the active field, validation feedback, and a reachable completion action usable with the software keyboard open. Account for changing visible height, browser chrome, safe areas, and overlay scrolling; a `vh`/`dvh` choice or safe-area padding alone does not prove keyboard behavior.
- Define browser Back, in-app Back, and dismiss behavior consistently with route history and task state. Preserve the appropriate selection, filters, scroll position, and unfinished input across the transitions the product supports. Use existing recovery mechanisms; do not invent offline sync or storage of sensitive drafts merely to satisfy this check.

### Verify the affected task paths

Exercise each affected core path from entry to its observable result with touch-capable input in an available supported environment. Use fixtures or reversible actions for submissions. Check the steps the task actually contains: discover the action, tap/scroll/select, enter and correct input, submit and observe success, return to context. For affected forms or navigation, include keyboard-open behavior, back/dismiss, and the relevant interruption or failure recovery. Test custom gestures and scrolling together. A color-only change can reuse current task evidence and inspect the changed affordances; a navigation or form change needs the affected path exercised again. Avoid unrelated whole-product retests.

Record evidence in `.impeccable/review/mobile-tasks.md`, or reference an existing current test report. Reused evidence retains its original build identity and a note explaining why the current diff leaves it applicable; a new build number alone does not invalidate unchanged behavior. For each task, give the route/build tested, environment and browser engine, input method, actions performed, observed result, and `pass`, `fail`, or `unverified`; list uncovered checks separately. For a planning-only request, record the intended checks in the brief and leave execution pending.

Keep the evidence types distinct:

- **Layout:** viewport sizes and screenshots establish composition, overflow, and visible states.
- **Interaction:** actual touch or synthesized touch establishes only the actions exercised in the named engine. Mouse clicks at a phone width do not establish touch behavior; automated text entry does not establish software-keyboard behavior.
- **Device coverage:** identify physical hardware, emulator/simulator, or browser emulation and any unsupported/unavailable cases. Chromium results do not establish iOS Safari behavior. Missing hardware alone is a coverage gap, not a demonstrated failure; use available evidence and state its limits.

Report source-level defects with their code evidence; keep inferred behavior distinct from executed task results. A failed core path blocks mobile completion. A required core path with no executable evidence is `unverified`, even when screenshots pass. Give the mobile task verdict separately from layout quality and numeric audit scores; a reviewer must carry failures and missing core evidence into the remaining work. When tooling cannot perform a check, deliver the implementation with that precise validation gap and next verification action. Stop retries that cannot add evidence; never invent a pass or require the user to provide hardware just to continue unrelated authorized work.

---

## Assess Adaptation Challenge

Resolve the target under [Device scope](../SKILL.md#device-scope), then understand what needs adaptation and why. An `adapt` request without a mobile target does not activate mobile work.

1. **Identify the source context**:
   - What was it designed for originally? (Desktop web? Mobile app?)
   - What assumptions were made? (Large screen? Mouse input? Fast connection?)
   - What works well in current context?

2. **Understand target context**:
   - **Device**: Mobile, tablet, desktop, TV, watch, print?
   - **Input method**: Touch, mouse, keyboard, voice, gamepad?
   - **Screen constraints**: Size, resolution, orientation?
   - **Connection**: Fast wifi, slow 3G, offline?
   - **Usage context**: On-the-go vs desk, quick glance vs focused reading?
   - **User expectations**: What do users expect on this platform?

3. **Identify adaptation challenges**:
   - What won't fit? (Content, navigation, features)
   - What won't work? (Hover states on touch, tiny touch targets)
   - What's inappropriate? (Desktop patterns on mobile, mobile patterns on desktop)

**CRITICAL**: Adaptation is rethinking the experience for the new context, not scaling pixels.

## Plan Adaptation Strategy

Use only the strategy sections for the requested target contexts:

### Mobile Adaptation (Desktop → Mobile)

Apply the [Mobile web task contract](#mobile-web-task-contract) first. Derive the layout from that path:

- Use a single column for sequential work; split a long stack into task steps when users need repeated trips between its ends.
- Choose visible navigation for frequent destinations and a drawer for secondary ones. Reserve persistent bars for controls whose value justifies the occupied screen space.
- Use a sheet for a short contextual choice when it preserves useful context; use a dedicated screen for sustained editing when space or keyboard behavior demands it. Native form controls remain valid choices.
- Aim for 44×44 CSS-pixel touch areas with separation as the skill's usability target. Preserve readable type, meaningful content, and essential functions through progressive disclosure.

### Tablet Adaptation (Hybrid Approach)

**Layout Strategy**:
- Choose the number of columns from the task and available width
- Side panels for secondary content
- Master-detail views (list + detail)
- Adaptive based on orientation (portrait vs landscape)

**Interaction Strategy**:
- Support both touch and pointer
- Touch targets 44x44px but allow denser layouts than phone
- Side navigation drawers
- Multi-column forms where appropriate

### Desktop Adaptation (Mobile → Desktop)

**Layout Strategy**:
- Multi-column layouts (use horizontal space)
- Side navigation always visible
- Multiple information panels simultaneously
- Fixed widths with max-width constraints (don't stretch to 4K)

**Interaction Strategy**:
- Hover states for additional information
- Keyboard shortcuts
- Right-click context menus
- Drag and drop where helpful
- Multi-select with Shift/Cmd

**Content Strategy**:
- Show more information upfront (less progressive disclosure)
- Data tables with many columns
- Richer visualizations
- More detailed descriptions

### Print Adaptation (Screen → Print)

**Layout Strategy**:
- Page breaks at logical points
- Remove navigation, footer, interactive elements
- Black and white (or limited color)
- Proper margins for binding

**Content Strategy**:
- Expand shortened content (show full URLs, hidden sections)
- Add page numbers, headers, footers
- Include metadata (print date, page title)
- Convert charts to print-friendly versions

### Email Adaptation (Web → Email)

**Layout Strategy**:
- Narrow width (600px max)
- Single column only
- Inline CSS (no external stylesheets)
- Table-based layouts (for email client compatibility)

**Interaction Strategy**:
- Large, obvious CTAs (buttons not text links)
- No hover states (not reliable)
- Deep links to web app for complex interactions

## Implement Adaptations

Apply changes systematically:

### Responsive Breakpoints

Choose content-driven breakpoints within the requested device range. These are reference ranges, not a required device or screenshot matrix:
- Mobile: 320px-767px
- Tablet: 768px-1023px
- Desktop: 1024px+
- Or content-driven breakpoints (where design breaks)

### Layout Adaptation Techniques

- **CSS Grid/Flexbox**: Reflow layouts automatically
- **Container Queries**: Adapt based on container, not viewport
- **`clamp()`**: Fluid sizing between min and max
- **Media queries**: Different styles for different contexts
- **Display properties**: Show/hide elements per context

### Touch Adaptation

- Increase touch target sizes (44x44px minimum)
- Add more spacing between interactive elements
- Remove hover-dependent interactions
- Add touch feedback (ripples, highlights)
- Consider thumb zones (easier to reach bottom than top)

### Content Adaptation

- Use `display: none` sparingly (still downloads)
- Progressive enhancement (core content first, enhancements on larger screens)
- Lazy loading for off-screen content
- Responsive images (`srcset`, `picture` element)

### Navigation Adaptation

- Select navigation by destination count, visit frequency, and return behavior from the task note.
- Use drawers, bottom navigation, persistent sidebars, or breadcrumbs where they help that path; retain discoverable access to core actions.

**IMPORTANT**: When a scoped task needs hardware-specific evidence, use available real devices and record uncovered cases under the task contract. Browser emulation provides evidence only for what it actually exercises.

**NEVER**:
- Hide core functionality on mobile (if it matters, make it work)
- Assume desktop = powerful device (consider accessibility, older machines)
- Change product concepts or terminology across contexts without a product reason; navigation presentation and task decomposition may adapt
- Break user expectations for platform (mobile users expect mobile patterns)
- Forget landscape orientation when it is part of the requested mobile/tablet context
- Use generic breakpoints blindly (use content-driven breakpoints)
- Ignore touch when touch input is explicitly in scope, including desktop touchscreens

## Verify Adaptations

Use the target viewports resolved under [Device scope](../SKILL.md#device-scope), normally one representative size per requested device class. When mobile web is explicitly in scope, execute and record the affected paths in the [Mobile web task contract](#mobile-web-task-contract). Select additional coverage only for the requested contexts and affected tasks:

- **Real devices**: Use the requested device classes
- **Orientations**: Cover orientations required by the brief or affected interaction
- **Browsers and OS**: Use the requested or established target environment
- **Input methods**: Exercise the applicable pointer, keyboard, and explicitly scoped touch paths
- **Edge sizes**: Add 320px, 4K, or another size only when requested or needed to reproduce a defect within scope
- **Slow connections**: Throttle when the affected task has a network constraint

**Custom controls** (sliders, drag surfaces, scrollable control strips): exercise affected controls with the scoped input methods in the same batched round as the checks above. For explicitly scoped mobile work, width checks alone cannot establish touch behavior:

- **Primary action**: Activate it with the target input method and confirm it responds as designed; a drag must complete, not just start
- **Scroll across it, when touch is in scope**: A swipe along the page's scroll axis across the control scrolls the page or container without activating it; a drag that starts on the control along its axis moves the control, not the page. Neither failure throws an error, so try both
- **Evidence**: Record the exercised gestures and their results in the task evidence, with input method and engine. Keep failed and unverified actions open; hardware availability and layout captures cannot change those results.

Hand off the scoped evidence to `$impeccable polish`, including any remaining failures or coverage gaps. Include a mobile task verdict only for explicitly scoped mobile work.

---

## Reference Material

The sections below were previously `responsive-design.md` and live inline now so the adapt flow has its deep responsive reference in one place.

### Responsive Design

#### Mobile-First: Write It Right

When mobile web is explicitly in scope, start with its task and a workable narrow composition, then layer wider layouts where useful. Otherwise start with the requested desktop composition. `min-width` queries are a convenient implementation choice; query direction alone establishes neither usability nor CSS download savings.

#### Breakpoints: Content-Driven

Let content determine breakpoints within the requested size range. Resize around the target composition only when needed to resolve a layout defect; existing breakpoints do not add device classes to the task. Use `clamp()` for fluid values where appropriate.

#### Detect Input Method, Not Just Screen Size

**Screen size doesn't tell you input method.** A laptop with touchscreen, a tablet with keyboard. Use pointer and hover queries:

```css
/* Fine pointer (mouse, trackpad) */
@media (pointer: fine) {
  .button { padding: 8px 16px; }
}

/* Coarse pointer (touch, stylus) */
@media (pointer: coarse) {
  .button { padding: 12px 20px; }  /* Larger touch target */
}

/* Device supports hover */
@media (hover: hover) {
  .card:hover { transform: translateY(-2px); }
}

/* Device doesn't support hover (touch) */
@media (hover: none) {
  .card { /* No hover state - use active instead */ }
}
```

**Critical**: Don't rely on hover for functionality. Touch users can't hover.

#### Safe Areas: Handle the Notch

Modern phones have notches, rounded corners, and home indicators. Use `env()`:

```css
body {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}

/* With fallback */
.footer {
  padding-bottom: max(1rem, env(safe-area-inset-bottom));
}
```

**Enable viewport-fit** in your meta tag:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

#### Responsive Images: Get It Right

##### srcset with Width Descriptors

```html
<img
  src="hero-800.jpg"
  srcset="
    hero-400.jpg 400w,
    hero-800.jpg 800w,
    hero-1200.jpg 1200w
  "
  sizes="(max-width: 768px) 100vw, 50vw"
  alt="Hero image"
>
```

**How it works**:
- `srcset` lists available images with their actual widths (`w` descriptors)
- `sizes` tells the browser how wide the image will display
- Browser picks the best file based on viewport width AND device pixel ratio

##### Picture Element for Art Direction

When you need different crops/compositions (not just resolutions):

```html
<picture>
  <source media="(min-width: 768px)" srcset="wide.jpg">
  <source media="(max-width: 767px)" srcset="tall.jpg">
  <img src="fallback.jpg" alt="...">
</picture>
```

#### Layout Adaptation Patterns

**Navigation**: Choose by the task's destination and return paths. **Tables**: For record lookup, a summary list with detail access can help; for cross-row comparison, retain comparable columns and a usable horizontal scroll region when needed. Preserve table semantics and access to important data. **Progressive disclosure**: Use `<details>/<summary>` for independently collapsible content when hiding it does not obstruct the primary task.

#### Testing: Don't Trust DevTools Alone

DevTools device emulation is useful for layout but misses:

- Actual touch interactions
- Real CPU/memory constraints
- Network latency patterns
- Font rendering differences
- Browser chrome/keyboard appearances

For explicitly scoped mobile work, prioritize its target browsers and devices, including iOS Safari or Android when required. Physical devices provide keyboard, browser-chrome, and performance evidence that viewport emulation misses. Record unavailable coverage under the task contract instead of treating a device list as completed testing.

---

**Avoid**: Deferring mobile task design until after desktop layout. Device detection instead of feature detection. Duplicating business logic for mobile and desktop. Ignoring supported tablet and landscape use. Assuming all mobile devices are powerful.
