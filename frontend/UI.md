# PlotPlanner — Frontend Design System & Interaction Blueprint
**Cursor implementation specification | Version 1.0**

> Product intent: preserve PlotPlanner's current information architecture and dashboard structure, but give it a distinctive, polished scrapbook / geometric toy-house interface. It should feel curious, tactile, playful, and alive—without becoming noisy, childish in a patronising way, or difficult to use.

## 1. North-star experience

PlotPlanner helps people explore many interests, discover connections, and turn curiosity into practical next steps. The interface should feel like a personal creative workspace assembled from paper, toy blocks, thread, stickers, stars, and little lamps.

The product is **not** a generic analytics dashboard, a school learning app, or a chaotic sticker collage. It is a thoughtful digital scrapbook for a person’s evolving interests.

### Design principles
1. **Keep the existing product structure.** Do not redesign the app’s information architecture or remove existing pages just to make the UI feel new.
2. **Playful details, calm composition.** Use a restrained palette, strong spacing, and deliberate focal points. Every page should have one main visual idea.
3. **Interaction should feel physical.** Shapes can roll, swing, wobble, glow, connect with thread, or respond to proximity. Motion should communicate state or invite exploration, not run continuously everywhere.
4. **Make the user feel curious, not evaluated.** Avoid grades, red/green performance judgments, arbitrary “personality scores,” and gamification that makes self-discovery feel like a test.
5. **Data first, decoration second.** Real user data and actions must remain clear. Decorative shapes must never obscure content, controls, contrast, or keyboard focus.
6. **Accessible by default.** Respect reduced-motion settings, maintain contrast, support keyboard navigation, and never make hover the only way to discover functionality.
7. **No fake capability.** Preserve existing API contracts and business logic. Do not invent backend endpoints or fabricate AI results. If an action is unsupported, show no control for it until implemented.
8. **Responsive scrapbook.** The interface should feel intentional on desktop, tablet, and mobile—not like a desktop canvas squeezed into a narrow viewport.

## 2. Visual direction

### Mood
- Handmade paper, scrapbook edges, paper clips, stitching, washi-tape accents.
- Geometric toy blocks: circles, squares, rectangles, stars, triangles, rounded arches.
- String/thread connecting related ideas, with tiny bulbs at meaningful junctions.
- Cut-paper shapes and subtle paper grain.
- Warm, tactile surfaces with crisp typography and generous whitespace.
- A hint of retro creative software, balanced with modern SaaS usability.

### Avoid
- Rainbow gradients, neon glow, glassmorphism, excessive blur, and generic purple AI gradients.
- Using every reference-image motif on every screen.
- Heavy drop shadows, noisy textures behind paragraphs, and decorative animations competing with reading.
- Making every card a different colour.
- Emoji as the main visual system. Use a coherent geometric icon set or custom CSS/SVG shapes.
- Directly embedding stock/reference images as full-screen backgrounds. Treat the supplied images as mood references; recreate the language with CSS/SVG where practical.

## 3. Three-colour palette

Use **three muted primary colour families** as the core identity: blue, coral/red, and golden yellow. Balance them with warm paper neutrals, dark ink, and semantic utility colours. The three families should dominate the visual identity; neutral surfaces should do most of the layout work.

### Core palette
| Token | Hex | Use |
|---|---|---|
| `--color-blue` | `#5C91B7` | Primary blue blocks, links, selected graph nodes |
| `--color-blue-soft` | `#A9C9D7` | Soft blue surfaces, graph canvas, subtle fills |
| `--color-blue-pale` | `#DCEAF0` | Pale blue panels and hover surfaces |
| `--color-coral` | `#E87968` | Warm coral accents, active states, important calls to action |
| `--color-coral-soft` | `#F1B0A4` | Soft coral surfaces, selected stickers |
| `--color-coral-pale` | `#F8DFD9` | Pale coral backgrounds |
| `--color-yellow` | `#E8BD55` | Stars, bulbs, highlights, progress markers |
| `--color-yellow-soft` | `#F2D993` | Soft yellow blocks and banners |
| `--color-yellow-pale` | `#FBF0CD` | Pale yellow surfaces |
| `--color-paper` | `#F7F3E8` | Main app background; warm paper |
| `--color-paper-white` | `#FFFDF7` | Cards, forms, content surfaces |
| `--color-paper-deep` | `#E8E0D0` | Dividers, paper edges, inactive tracks |
| `--color-ink` | `#26343B` | Main text |
| `--color-ink-soft` | `#52636A` | Secondary text |
| `--color-line` | `#D7D0C2` | Borders and separators |
| `--color-success` | `#557E69` | Success only |
| `--color-warning` | `#A96D2D` | Warning only |
| `--color-danger` | `#B94E4E` | Destructive/error states only |

These are a starting point. Verify text/background contrast before finalising. Use ink text on pale fills; do not put small white text on yellow.

### Colour rules
- At most **one dominant accent colour per component**, with a second colour used for a small detail.
- A page should usually contain paper neutral + one primary family + tiny accents from another family.
- Do not give each navigation item its own colour.
- Use coral for high-priority action sparingly; blue for navigation/selection; yellow for curiosity, stars, lamps, and progress details.
- Colour must not be the only indication of status.
- Graph nodes may vary by category, but use controlled tints from these three families and provide labels/legends.

## 4. Materials, texture, and shape language

### Surfaces
- Main background: warm paper `#F7F3E8`, with optional very subtle grain/noise at 2–4% opacity.
- Cards: near-white paper `#FFFDF7`, thin warm border, small offset paper shadow.
- Selected/featured cards: one pastel accent fill, not a gradient.
- Section headers may use a tiny paper label, stitched line, or washi-tape corner.
- Use `border-radius` with restraint: mix modest rounded corners with occasional clipped/angled paper shapes. Avoid making every component a pill.

### CSS texture patterns
Use CSS backgrounds or inline SVG for low-cost patterns:
- Tiny dots for notebook paper.
- Dashed/stitch borders for pinned or selected cards.
- Sparse stars in onboarding transitions or empty states.
- Stripes/washi tape for section labels.
- Subtle grid only on the graph workspace.
Textures should be low contrast and never sit behind dense text.

### Shape vocabulary
Create a reusable `Shape` component or small SVG library:
- Circle
- Rounded square
- Rectangle / paper strip
- Five-point star
- Triangle
- Arch / half-circle
- Small bulb
- Paper clip
- Thread/connector
- Sticker burst

Shapes need variants, not arbitrary one-off implementations. Suggested props: `shape`, `tone`, `size`, `rotation`, `interactive`, `decorative`, `motion`, `label`. Decorative shapes must be `aria-hidden="true"`.

### Shadows and depth
Use layered paper depth, not floating glass cards:
- Small shadow: `0 2px 0 rgba(38,52,59,.08), 0 4px 12px rgba(38,52,59,.05)`
- Lifted interactive card: `0 3px 0 rgba(38,52,59,.10), 0 10px 22px rgba(38,52,59,.08)`
- Focus ring must be clear and not replaced by shadow.

## 5. Typography

Use a readable modern sans-serif for product UI and an optional expressive display face for a few short headings only.

Suggested pairing:
- UI/body: **DM Sans**, **Inter**, or existing project font if already bundled.
- Display accent: **Fraunces** or **DM Serif Display** used sparingly for short emotional headings.
- Do not use novelty fonts for long content, labels, numbers, or form inputs.

Scale:
- Page title: 30–36 px desktop; 26–30 px mobile.
- Section title: 20–24 px.
- Card title: 16–18 px.
- Body: 14–16 px, line-height 1.5–1.65.
- Helper text: 12–14 px; never below 12 px for meaningful information.
- Button labels: 14–15 px, medium/semibold.

Use sentence case, plain language, and friendly microcopy. Avoid overusing exclamation marks.

## 6. Motion system

Motion should make the interface feel tactile, but the app must remain calm and usable.

### Timing tokens
```css
--motion-quick: 140ms;
--motion-standard: 220ms;
--motion-delight: 420ms;
--motion-float: 2.8s;
--ease-spring: cubic-bezier(.2, .85, .25, 1.15);
--ease-soft: cubic-bezier(.22, 1, .36, 1);
```

### Allowed signature animations
1. **Intro star sprinkle:** 5–9 small stars fall briefly on the first onboarding screen; stop after the entrance.
2. **Rolling square:** one square rolls into position on onboarding transitions or successful completion.
3. **Dangling bulb:** a small lamp hangs from a short thread and gently swings when first revealed; stops or becomes nearly still afterward.
4. **Proximity light:** bulb lights up when the pointer approaches or when the associated item receives keyboard focus. Use distance/proximity only as progressive enhancement; always provide an explicit focus/selected state.
5. **String draw:** graph connections draw in with a short stroke animation when the graph first appears or a new relationship is added.
6. **Shape response:** selected nodes gently lift, rotate 2–4 degrees, or wobble once.
7. **Card reveal:** staggered entrance of content cards by 30–50 ms, limited to the initial page load.
8. **Completion moment:** a small star burst and paper confetti (CSS/SVG) after onboarding is completed. Keep it short and provide a reduced-motion alternative.

### Motion rules
- No infinite bouncing, perpetual falling stars, or all-card floating animations.
- Avoid parallax and large zooms.
- Most interactions should complete in 140–300 ms.
- Keep decorative motion out of the user’s reading path.
- Respect `prefers-reduced-motion: reduce`; replace movement with opacity or instant state changes.
- Never animate layout in a way that moves a focused control unexpectedly.
- Do not require a pointer or hover to use any feature.

## 7. Interaction components

Build reusable components that fit the current React architecture rather than duplicating CSS per page.

### `PaperCard`
- Paper-white background, warm thin border, subtle offset shadow.
- Optional `tone="blue|coral|yellow|neutral"`.
- Optional small taped corner or stitched edge.
- Hover/focus: slight lift, not a dramatic scale.
- Supports loading, empty, and error states.

### `ShapeButton`
- Button presented as a circle, square, star, or rounded rectangle.
- Must still have a clear accessible name and at least a 44×44 px touch target.
- Star-shaped buttons should be reserved for playful, low-frequency actions; primary actions should remain legible and conventional.

### `WashiLabel`
- Small paper strip behind a section label or category.
- Never use as the only label for a form field.
- Limit to one or two per card.

### `ThreadConnector`
- SVG path or CSS/SVG line with subtle irregularity.
- Used to show real relationships between interest nodes.
- Provide a non-visual/accessible relationship description and an alternative list view.
- Avoid crossing text or controls.

### `Bulb`
- Small SVG lamp with a thread and warm yellow glow.
- States: `idle`, `near`, `focused`, `active`.
- `near` may use pointer position if feasible; keyboard focus must produce the same visible response.
- Glow should be subtle and not create a large blur layer.

### `Sticker`
- A small icon-like decorative object with controlled rotation and border.
- Use only for emphasis, empty states, onboarding, and occasional milestones.
- Decorative stickers are hidden from assistive technology.

### `ProgressTrack`
- A line, string, or row of geometric markers rather than a generic gradient bar.
- Always show a textual progress label or number as well.
- Avoid implying a person’s worth or ability is measurable by the progress value.

### `PageTransition`
- Small opacity/vertical transition; no elaborate route animation.
- Must not delay access to content.

## 8. Application shell and navigation

**Preserve the existing navigation destinations and page organisation.** Improve their visual treatment rather than changing the product architecture.

### Desktop
- Keep the current sidebar-based shell if present.
- Paper-neutral canvas; sidebar separated by a thin stitched/dashed divider or warm border.
- Brand mark: simple geometric motif (three shapes connected by a thread), not a complex illustration.
- Active navigation item: pale blue or coral paper tab with clear text and a small geometric marker.
- Hover: gentle background shift and tiny icon movement.
- Keep navigation icons consistent in stroke weight and size.
- Account/profile and sign-out actions should remain easy to find.

### Mobile
- Preserve the current mobile navigation model if it works.
- Ensure labels remain readable and active states are clear.
- Do not use tiny decorative shapes as the only icon.
- On narrow screens, reduce textures and floating decorations.
- Graph canvas should support touch, zoom, pan, and a list-based alternative.

### Global behaviour
- Maintain existing route paths and route protection.
- Preserve loading, authentication, error, and redirect behaviour.
- Use the existing query/cache strategy. Do not duplicate fetches in local component state without a reason.
- Keep keyboard focus visible and ensure overlays/dialogs are accessible.

## 9. Onboarding — highest-priority experience

The first-run onboarding should feel like an interactive, full-page journey. Each question gets the user’s attention without making the process feel like a long form.

### Core requirement
**Ask every question first. Do not show the editable final profile summary until all onboarding questions have been answered.** Editing is available on that final review screen, and the user can revisit/edit information later from the appropriate profile/settings area.

Do not expose an “edit previous answers” control during the question sequence unless the existing product flow explicitly requires it. The user should be able to move forward with clear next/back behaviour if supported by the current flow, but the summary/edit mode appears only at the end.

### Screen structure
- Full viewport, warm paper background, minimal chrome.
- A small brand mark and discreet progress indicator.
- One question per screen, with the question as the dominant element.
- One concise helper sentence at most.
- Answer area visually distinct, using paper cards, geometric choice tiles, text input, chips, or other controls appropriate to the question type.
- Large clear `Continue` action and a secondary `Back` action where appropriate.
- Keyboard support: Enter continues only when safe; textarea Enter should create a new line unless a deliberate shortcut is indicated.
- Progress should communicate approximate completion without making users feel rushed.
- Persist draft state using the existing onboarding mechanisms. Do not invent a separate persistence system unless needed.

### Opening moment
- Show a short entrance: 5–9 small stars drift/fall into place and a square rolls in.
- One friendly line of copy, such as: “Let’s make a little map of what makes you, you.”
- Motion lasts under 1.5 seconds and must not block interaction.
- Skip the decorative entrance when reduced motion is enabled or when the user has already seen it in the current session.

### Question presentation
- Use large display text and generous whitespace.
- Animate question changes with a quick paper-slide, soft fade, or shape transition.
- Give answer options distinct geometric containers: squares, circles, or rectangles, but keep the control easy to understand.
- Selected options should visibly “press” or lift and show a check/selected indicator.
- Use playful motion only on selection/transition, not on every idle element.
- Free-text answers use large paper-like fields with strong focus styling.

### Final review
Only after the question flow is complete:
- Show a scrapbook-style summary of the user’s answers.
- Use clearly labelled sections, not a collage that obscures information.
- Each section has a small `Edit` action.
- Editing opens the appropriate inline editor or returns to the relevant step, then returns the user to the review screen.
- Keep the final submit/complete action obvious.
- Make clear that users can edit their information later.
- On success: a short string-draw animation, bulb glow, and a few falling stars; then route to the existing post-onboarding destination.
- Prevent duplicate submissions and show a recoverable error if completion fails.
- Never claim onboarding is complete before the backend confirms success.

### Existing integration constraints
- Inspect the active onboarding page and backend service before implementing.
- Preserve the existing question order, schemas, validation, and draft/completion API contracts unless a separate backend change is explicitly approved.
- Do not create a new onboarding endpoint just to support animations.
- Keep analytics/events only if they already exist or are explicitly added as part of a reviewed implementation.

## 10. Dashboard / Home

Keep the existing dashboard information architecture and its metrics, lists, and suggestions. Improve the visual hierarchy and emotional quality.

### Layout
1. Personalised greeting and short context line.
2. One featured “continue exploring” or next-action area, based on actual available data.
3. Existing summary metrics arranged as tactile paper tiles.
4. Existing learning pathway and goal sections.
5. Existing suggestions or recent activity.
6. Empty states for users who have not created interests/goals/pathways yet.

### Visual treatment
- Use one main accent family per card.
- Metric cards can use geometric corner shapes or a small icon badge.
- The main featured action may have a small hanging bulb or star marker.
- Add subtle card entrance staggering once on initial load.
- Avoid animating numbers continuously or inventing metrics.
- Keep numbers, labels, and actions legible.
- Use consistent spacing and card heights; avoid a random masonry layout if it harms scanning.

### Behaviour
- All current links and actions must remain functional.
- Keep existing React Query keys and invalidation behaviour unless a verified issue requires a change.
- Skeletons should resemble the final paper cards.
- Empty states should suggest one meaningful next action without overwhelming the user.

## 11. Explore / Interest network

This is the signature visual surface and should feel like a connected collection of ideas in a handmade playroom.

### Canvas
- Warm paper or pale blue canvas with a very faint grid/dot texture.
- Nodes look like tangible cut-paper blocks, not standard white circles.
- Shapes may represent different interest types: circles, squares, rounded rectangles, stars, and triangles.
- Keep the shape-to-meaning mapping consistent and include a legend. Never encode important meaning by shape alone.
- Labels remain readable at common zoom levels; provide a details panel/list for small screens and assistive technology.

### Connections
- Use SVG thread/string paths with slightly organic curves.
- Draw paths in on initial load and when a new relationship is created.
- Use subtle dashed or stitched styling for suggested/unconfirmed connections if the data model supports this distinction.
- Distinguish saved relationships from AI suggestions.
- Avoid spaghetti: use layout, edge routing, and selection highlighting to keep relationships readable.
- Do not imply a relationship exists unless it is stored or explicitly presented as a suggestion.

### Node interactions
- Hover/focus: tiny lift or 2–4° rotation, plus a small bulb glow.
- Selected node: clear border and stable details panel.
- Click/tap: show current details and available actions.
- Dragging must not trigger accidental navigation.
- Preserve current graph editing and layout persistence.
- Provide zoom controls, fit-to-view, reset layout if supported, and a list/keyboard alternative.
- Respect reduced motion.

### Details panel
- Interest name and description.
- Related interests and relationship context, based on returned data.
- Existing edit/delete actions.
- Existing AI suggestion action.
- Relevant goals or learning links only when real data and supported routes exist.
- Do not add fabricated “AI confidence” percentages.

### Performance
- Avoid applying expensive blur filters to every node.
- Use SVG/CSS transforms for motion.
- Test with a large interest network and on mobile.

## 12. Learn / learning pathways

### Visual direction
- Course/pathway cards resemble neatly arranged paper index cards with one coloured edge or small geometric marker.
- Show title, short description, progress, status, and primary action in a consistent hierarchy.
- Use string-like progress tracks with labelled milestones, but preserve a numeric/textual indicator.
- Completed items may receive a small star sticker; avoid confetti on every completion.

### Interactions
- Preserve existing generation, enrolment, progress update, regeneration, archive, and resource refresh operations.
- Show a clear pending/loading state during generation.
- Disable duplicate generation requests while one is in progress.
- Distinguish “no resources found” from a failed resource request.
- Keep source URLs and external links clear and safe.
- If the backend returns a proposal or plan that requires approval, make the approval state explicit.

## 13. Goals

### Visual direction
- Goals as paper cards pinned to a simple path or board.
- Milestones as geometric markers connected by a thin line/string.
- Completed milestones change state calmly and receive a small visual acknowledgement.
- Dates and status remain readable; decorative string is secondary.

### Interactions
- Preserve current create, plan, edit, status, milestone-add, milestone-complete, and check-in operations.
- Add milestone deletion only if the backend operation is verified and the product decision is approved.
- Optimistic UI updates must roll back or show an error if the request fails.
- Keep destructive actions behind a confirmation or undo pattern where appropriate.
- Empty state should encourage one small, realistic goal rather than a long planning process.

## 14. Earn / opportunities and salary research

### Visual direction
- Keep this page more practical and less decorative than onboarding or Explore.
- Job/opportunity cards use neutral paper surfaces and a single accent tab.
- Make role, company/source, location, work mode, and status easy to scan.
- Use stickers sparingly for “new” or “saved”; avoid gamifying job applications.

### Interactions
- Preserve search, fit assessment, save/track, status update, salary report, and earning-plan capabilities.
- Expose location input if supported by the active backend schema.
- Show filter state clearly and provide a simple way to clear filters.
- Validate status payloads against the backend schema; send only allowed fields.
- Distinguish provider errors, empty search results, and no configured provider.
- Never invent job listings, salary ranges, or source citations.
- External opportunities should clearly identify their source and link destination.

## 15. Chat / AI assistant

### Visual direction
- Chat should feel like a conversation on a clean notebook page, not a robot control panel.
- User messages may have a pale accent strip; assistant messages remain high contrast and calm.
- Source citations should be visually distinct and clickable.
- Use tiny geometric marks for tool/activity states; do not animate every token or message.

### Interactions
- Preserve conversation list, create/open conversation, send message, retry, delete, and proposal accept/dismiss behaviour.
- Clearly distinguish a proposal awaiting user approval from an action already completed.
- Keep a visible loading/thinking state, but avoid fake “thinking” messages.
- Errors should preserve the user's unsent text.
- Support keyboard submission and accessible message announcements.
- On mobile, the composer must remain usable with the virtual keyboard open.
- Do not imply that the assistant has updated a profile, goal, or course until the backend confirms the action.

## 16. Documents

### Visual direction
- Documents as tidy paper sheets with file-type markers and restrained paperclip/sticker details.
- Make upload state, processing state, extracted facts, and confirmation status easy to distinguish.
- Keep the page more functional than decorative.

### Interactions
- Preserve current upload, list, delete, extraction, and fact-confirmation workflows.
- Show progress where the existing upload mechanism exposes it; otherwise show a truthful pending state.
- Handle unsupported file types and size limits clearly.
- Confirm destructive deletion.
- Explain which extracted facts are pending confirmation.
- Do not display document contents or extracted personal information in decorative overlays.
- Make it clear how to retry if processing fails.

## 17. Insights / analytics

### Visual direction
- Use paper charts, simple lines, dot plots, and geometric markers.
- Keep the data-to-ink ratio high: charts should be clear, not ornamental.
- Avoid 3D charts, excessive gridlines, gradient fills, or decorative charts without a real metric.
- Use the three colour families consistently and include labels/legends.

### Interactions
- Preserve current overview, interest analytics, and activity queries.
- Provide a useful empty state when there is insufficient history.
- State the period or basis of each metric.
- Do not imply causation from correlation.
- Avoid arbitrary scores or personality labels.
- Charts must have accessible summaries or a table/list alternative.

## 18. Profile and settings

### Visual direction
- A personal scrapbook index: clear sections, editable values, calm forms.
- Decorative shapes only in the header or section labels.
- Form fields should be conventional and accessible even when surrounded by playful styling.

### Interactions
- Preserve profile retrieval/update, constraints/preferences, fact confirmation/edit/delete, and sign-out.
- Show unsaved changes clearly.
- Confirm destructive account-data actions and explain their scope.
- Distinguish deleting application data from deleting the authentication account if those operations differ.
- Keep editing available after onboarding.
- Avoid forcing users to repeat onboarding to change a single preference.

## 19. Shared states and microcopy

Every page must include designed states for:
- Initial loading / skeleton.
- Empty data.
- Recoverable API error with retry.
- Form validation error.
- Mutation in progress.
- Mutation success.
- Disabled action with explanation where needed.
- No network / unavailable service where detectable.

Microcopy style:
- Warm, clear, concise, respectful.
- Prefer “Try again” over “Retry operation.”
- Prefer “Nothing here yet” plus one next action over a blank screen.
- Do not blame the user.
- Do not overuse “magical,” “unlock,” “superpower,” or exaggerated praise.
- Never promise a result that depends on an external provider.

## 20. Accessibility and responsive requirements

- WCAG AA contrast for body text and controls.
- Minimum 44×44 px touch targets where practical.
- Full keyboard navigation; visible focus ring.
- Correct heading hierarchy and labels for every form field.
- Dialog focus management and Escape behaviour where appropriate.
- `aria-live` for important async updates, used sparingly.
- Reduced-motion support across all animations.
- Do not use colour, shape, or position as the only signal.
- At 320 px wide, no horizontal overflow in ordinary pages.
- On mobile, graph has pan/zoom plus a non-canvas alternative.
- Test 200% browser zoom.
- Avoid hover-only information and interactions.

## 21. Technical implementation guidance for Cursor

### First inspect, then change
Before implementation, inspect:
- `frontend/src/pages/`
- `frontend/src/components/`
- `frontend/src/services/api.ts`
- `frontend/src/api/client.ts` and determine whether it is legacy
- current global styles and component styles
- router, auth, and query-client configuration
- active backend schemas for every mutation being touched

### Preserve
- Existing routes and route guards.
- Existing backend endpoints and request/response contracts.
- Existing data model and Supabase integration.
- Existing React Query cache keys and invalidation semantics unless a verified bug is fixed.
- Existing user-facing feature coverage.
- Current dashboard organisation.

### Prefer
- Reusable CSS variables and component variants.
- CSS transforms and SVG for geometric decoration.
- Inline SVG for custom stars, bulbs, thread, and simple shapes.
- Existing dependencies before adding new ones.
- Small, focused components over a giant design-system file.
- Reduced-motion CSS and accessible states from the beginning.
- Responsive CSS rather than separate duplicated pages.

### Avoid
- Rewriting the backend for a visual-only redesign.
- Replacing React Flow or existing graph logic without a demonstrated need.
- Adding dependencies just for simple stars/shapes.
- Creating placeholder API calls or mock data in production paths.
- Swallowing errors to make the interface appear successful.
- Replacing actual content with decorative cards.
- Large refactors mixed with visual changes that make regressions hard to trace.

### Suggested component organisation
Adapt to the existing repository; do not move files unnecessarily.
```text
components/
  scrapbook/
    PaperCard.tsx
    Shape.tsx
    ShapeButton.tsx
    WashiLabel.tsx
    Sticker.tsx
    Bulb.tsx
    ThreadConnector.tsx
    ProgressTrack.tsx
    PageTransition.tsx
    EmptyState.tsx
    LoadingState.tsx
```

### Suggested CSS token file
Create or extend the existing global token stylesheet rather than duplicating values.
```css
:root {
  --color-blue: #5C91B7;
  --color-blue-soft: #A9C9D7;
  --color-blue-pale: #DCEAF0;
  --color-coral: #E87968;
  --color-coral-soft: #F1B0A4;
  --color-coral-pale: #F8DFD9;
  --color-yellow: #E8BD55;
  --color-yellow-soft: #F2D993;
  --color-yellow-pale: #FBF0CD;
  --color-paper: #F7F3E8;
  --color-paper-white: #FFFDF7;
  --color-paper-deep: #E8E0D0;
  --color-ink: #26343B;
  --color-ink-soft: #52636A;
  --color-line: #D7D0C2;

  --radius-card: 12px;
  --radius-control: 9px;
  --shadow-paper: 0 2px 0 rgba(38, 52, 59, .08),
                  0 4px 12px rgba(38, 52, 59, .05);
  --shadow-lifted: 0 3px 0 rgba(38, 52, 59, .10),
                   0 10px 22px rgba(38, 52, 59, .08);

  --motion-quick: 140ms;
  --motion-standard: 220ms;
  --motion-delight: 420ms;
  --ease-soft: cubic-bezier(.22, 1, .36, 1);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
```

## 22. Implementation sequence

Implement in small, verifiable phases.

### Phase 0 — baseline and safety
- Identify the active frontend implementation and legacy files.
- Run existing lint, typecheck, tests, and build.
- Capture screenshots of all current pages at desktop and mobile widths.
- Do not change APIs or remove features.

### Phase 1 — design tokens and primitives
- Add the palette, typography, shadows, border, spacing, and motion tokens.
- Build PaperCard, Shape, WashiLabel, Bulb, Sticker, and empty/loading states.
- Verify contrast, reduced motion, focus, and touch targets.

### Phase 2 — application shell and dashboard
- Restyle the shell and navigation while preserving routes.
- Restyle the dashboard cards and hierarchy.
- Verify that all links, queries, and actions remain functional.

### Phase 3 — onboarding
- Implement full-page one-question-at-a-time presentation.
- Keep the final editable summary hidden until all questions are completed.
- Preserve the active onboarding backend contracts.
- Verify resume, validation, back/continue, final edit, completion, and error states.

### Phase 4 — Explore graph
- Restyle graph canvas, nodes, edges, selected state, details panel, and controls.
- Add string-draw and bulb interactions.
- Verify saved positions and graph actions still work.
- Test large graphs, mobile, keyboard use, and reduced motion.

### Phase 5 — remaining pages
- Apply the visual system to Learn, Goals, Earn, Chat, Documents, Insights, and Profile.
- Prioritise clarity and functional states over decorative effects.

### Phase 6 — regression and polish
- Run frontend lint/typecheck/tests/build and backend tests.
- Exercise each page’s primary workflows.
- Check browser console and network requests.
- Compare before/after screenshots at consistent viewport sizes.
- Fix visual inconsistencies and regressions.

## 23. Acceptance checklist

### Design
- [ ] The app visibly feels like a clean scrapbook / geometric toy-house.
- [ ] Blue, coral, and yellow are the only dominant accent families.
- [ ] Warm paper neutrals preserve readability.
- [ ] Shapes and textures are consistent and reusable.
- [ ] Decorative elements do not obscure content.
- [ ] The interface is playful without feeling chaotic or overly childish.

### Onboarding
- [ ] One question fills the page at a time.
- [ ] Intro motion is short and does not block interaction.
- [ ] The final editable summary appears only after all questions.
- [ ] Editing is available in final review and after onboarding through profile/settings.
- [ ] Draft persistence and completion use existing API contracts.
- [ ] Errors do not lose answers.
- [ ] Reduced-motion mode is respected.

### Interactions
- [ ] Stars, rolling square, bulbs, and strings are used sparingly and consistently.
- [ ] Bulbs respond to pointer proximity where feasible and to keyboard focus.
- [ ] Graph relationships are represented by thread-like connectors.
- [ ] Hover effects have equivalent keyboard/touch states.
- [ ] Motion never blocks a control or makes content jump unexpectedly.

### Functionality
- [ ] Every current route remains accessible.
- [ ] Every existing primary action still works.
- [ ] No API request schema is changed accidentally.
- [ ] Loading, empty, error, and success states exist on all data-driven pages.
- [ ] No fake data or unsupported capability is introduced.
- [ ] Existing tests and builds pass, or any pre-existing failures are documented.

### Accessibility and responsive
- [ ] Keyboard-only flows work.
- [ ] Contrast is checked.
- [ ] Reduced motion works.
- [ ] Mobile layouts do not overflow.
- [ ] Graph has an accessible alternative.
- [ ] Forms and dialogs are properly labelled and focus-managed.

## 24. Cursor master instruction

Use this README as the design contract for the PlotPlanner frontend redesign.

**Do not implement everything in one massive change.** First inspect the current active frontend and report the files/components that will change. Then implement Phase 0 and Phase 1, run checks, and continue phase by phase. Preserve the current dashboard structure, routes, backend APIs, authentication, data model, and product functionality. The goal is a visual and interaction redesign, not a product rewrite.

When touching an endpoint-backed action, verify its request schema and response type against the active FastAPI backend. If a feature is missing or an endpoint is unused, explain the gap before deciding to connect it. Do not invent APIs, hide failures, or substitute mock data for real integrations.

The finished result should feel like **a calm, tactile, interactive scrapbook of a person’s interests**: three softened primary colours, paper surfaces, geometric blocks, stars, dangling bulbs, and thread-connected ideas—playful, surprising in small moments, and consistently easy to use.
