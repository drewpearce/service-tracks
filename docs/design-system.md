# ServiceTracks Design System

The durable reference for how ServiceTracks looks and feels. Every rule here is traceable to a screen in `mockups/`. If a design decision isn't covered below, update the doc — don't invent in the dark.

**Status:** v1 — direction locked, screens mocked. Implementation has not yet consumed this doc.

---

## 1. Principles

Five short statements. When a design choice is ambiguous, fall back to these.

1. **Quiet surface, loud content.** The chrome is cool slate and restrained. Songs, plans, and numbers are what should pull the eye. Never let a button, badge, or decoration compete with the content it frames.
2. **Clarity over decoration.** Every visual element earns its place by making something easier to scan, read, or act on. Gradients, glows, and ornaments appear only in hero regions — never as ambient noise.
3. **Status is semantic.** Teal = action and success. Rose = problems. Amber = pending. Slate = everything else. Don't cross the streams: never use teal for a neutral accent or rose for emphasis.
4. **Monospace means mechanical.** If the user typed it, generated it, or can copy-paste it as a key/code/template — it's JetBrains Mono. Everything else is Inter.
5. **Dense where it matters, airy where it doesn't.** Tables and lists are compact because they're scanned. Hero, empty states, and first-run screens are spacious because they're read.

---

## 2. Color

Cool monochromatic foundation. Slate carries the whole app; teal and rose are the only accents; amber appears only in caution states.

### 2.1 Palette

All values are Tailwind-compatible. Slate, teal, and rose use Tailwind's default scales. The palette is otherwise closed — do not introduce additional hues without updating this doc.

#### Slate — surface & text (full 50→950 scale)

| Token | Hex | Primary use |
|---|---|---|
| `slate-50` | `#F8FAFC` | Page background |
| `slate-100` | `#F1F5F9` | Secondary surface, hover state on ghost buttons |
| `slate-200` | `#E2E8F0` | Card border, divider |
| `slate-300` | `#CBD5E1` | Input border |
| `slate-400` | `#94A3B8` | Placeholder text, disabled icons, sidebar nav idle |
| `slate-500` | `#64748B` | Muted text (helper copy, metadata) |
| `slate-600` | `#475569` | Body text on light surfaces (secondary) |
| `slate-700` | `#334155` | Body text on light surfaces (primary, when `slate-900` is too heavy) |
| `slate-800` | `#1E293B` | Hover surface on `slate-900`, stepper inactive |
| `slate-900` | `#0F172A` | **Inverse surface** (sidebar, primary buttons, hero base), primary text |
| `slate-950` | `#070B14` | Reserved for future deep-dark surfaces |

#### Teal — primary action & success

| Token | Hex | Primary use |
|---|---|---|
| `teal-50` | `#F0FDFA` | Badge background (synced, recommended) |
| `teal-100` | `#CCFBF1` | Soft surface on dark backgrounds (rare) |
| `teal-200` | `#99F6E4` | Badge border |
| `teal-400` | `#2DD4BF` | Inverse-surface accent text (hero eyebrow, inverse icon) |
| `teal-500` | `#14B8A6` | Logo mark, focus ring source, avatar gradient start, stepper active |
| `teal-600` | `#0D9488` | Input focus border, selected radio card border, badge text |
| `teal-700` | `#0F766E` | Badge text (on `teal-50` background) |

#### Rose — warning & errors

| Token | Hex | Primary use |
|---|---|---|
| `rose-50` | `#FFF1F2` | Unmatched alert surface, error input hint background |
| `rose-100` | `#FFE4E6` | Soft rose accent |
| `rose-200` | `#FECDD3` | Badge border |
| `rose-400` | `#FB7185` | Hover state of rose buttons |
| `rose-500` | `#F43F5E` | Rose dot indicators (unmatched), avatar gradient end |
| `rose-600` | `#E11D48` | Danger button, error input border, "Find match" link |
| `rose-700` | `#BE123C` | Badge text, emphasized error text |

#### Amber — caution & pending

Reserved for **token expiry warnings, pending sync states, and draft surfaces**. Never used for primary action.

| Token | Hex |
|---|---|
| `amber-50` | `#FFFBEB` |
| `amber-200` | `#FDE68A` |
| `amber-500` | `#F59E0B` |
| `amber-700` | `#B45309` |

### 2.2 Semantic roles

When coding, prefer the semantic name in comments and Tailwind class arrangement; the direct color token is the implementation.

| Role | Token | Notes |
|---|---|---|
| `surface` | `slate-50` (page), `white` (card) | Two layers is the max |
| `surface-inverse` | `slate-900` | Sidebar, primary button, hero, inverse preview |
| `surface-muted` | `slate-100` | Subtle fill (pill-segment tab track, input disabled) |
| `border` | `slate-200` | Card, divider |
| `border-input` | `slate-300` | Inputs |
| `text-primary` | `slate-900` | Default |
| `text-secondary` | `slate-600` / `slate-700` | Body copy |
| `text-muted` | `slate-500` | Helper, metadata |
| `text-placeholder` | `slate-400` | Input placeholder, disabled text |
| `text-inverse` | `white` (primary) / `slate-300`–`slate-400` (muted) | Text on inverse surfaces |
| `accent` | `teal-500` / `teal-600` | Interactive state, focus, selection |
| `accent-on-dark` | `teal-400` | Eyebrow text on inverse |
| `danger` | `rose-500` / `rose-600` | Errors, unmatched |
| `warning` | `amber-500` | Pending, token expiry |

### 2.3 Hero gradient

Used **only in hero regions** (top of most primary pages, brand panel on Login). Never ambient.

```css
background:
  radial-gradient(60% 60% at 0% 0%, rgba(20, 184, 166, 0.18) 0%, transparent 60%),
  radial-gradient(40% 50% at 100% 0%, rgba(244, 63, 94, 0.14) 0%, transparent 60%),
  #0F172A;
```

Teal glow at top-left (alpha 0.18) + rose glow at top-right (alpha 0.14) + slate-900 base. For smaller surfaces (login panel, card hero), increase alphas slightly (0.22 / 0.16).

### 2.4 Avatar & cover-art gradients

User avatars use the signature gradient — this is the one place teal and rose combine directly:

```css
bg-gradient-to-br from-teal-400 to-rose-500
```

Song cover art uses deterministic gradients derived from the title hash. The palette is limited to four recipes:

```css
linear-gradient(135deg, #14B8A6 0%, #0F766E 50%, #0F172A 100%);  /* teal */
linear-gradient(135deg, #F43F5E 0%, #BE123C 60%, #0F172A 100%);  /* rose */
linear-gradient(135deg, #2DD4BF 0%, #14B8A6 40%, #1E293B 100%);  /* teal light */
linear-gradient(135deg, #FB7185 0%, #F43F5E 40%, #0F172A 100%);  /* rose light */
```

No other hues allowed for cover-art fallback.

### 2.5 Don't

- **Don't introduce blues, greens, or purples.** The palette is closed.
- **Don't use teal for neutral accents.** Teal means "this is an action or a positive state" — reserved.
- **Don't gradient anything except hero, avatars, and cover art.** No gradient buttons, cards, or borders.
- **Don't tint text with color-600+ except for semantic meaning.** A rose-600 "Match →" link means "this is about a problem." Using it for visual variety breaks the system.

---

## 3. Typography

Three typefaces. All three loaded from Google Fonts.

```html
<link
  href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
  rel="stylesheet"
/>
```

### 3.1 Families

| Family | Role | Weights used |
|---|---|---|
| **Space Grotesk** | Display — headings, hero, metric numbers, wordmark | 500, 600, 700 |
| **Inter** | Body — everything else, UI chrome | 400, 500, 600 |
| **JetBrains Mono** | Mechanical — code, credentials, template strings, keyboard shortcuts, technical metadata | 400, 500 |

### 3.2 Type scale

All sizes are in `px` for precision. `leading` is the CSS value.

| Role | Size | Leading | Weight | Tracking | Family | Used for |
|---|---|---|---|---|---|---|
| `display` | 40 | 1.05 | 600 | `-0.01em` (`tracking-tight`) | Space Grotesk | Page-level hero titles. Hero greeting format: single line — "Good morning, **Church Name.**" with the name in `teal-400`. No line break. |
| `h1` | 24 | 1.2 | 600 | `-0.01em` | Space Grotesk | Section titles within a page |
| `h2` | 18 | 1.3 | 600 | `-0.01em` | Space Grotesk | Card titles, subsection headings |
| `h3` | 15 | 1.4 | 600 | normal | Space Grotesk | Minor titles, key labels |
| `eyebrow` | 11 | 1 | 600 | `0.18em` (`uppercase`) | Inter | Sits above a heading; section counters |
| `body` | 14 | 1.6 | 400 | normal | Inter | Running paragraphs, descriptions |
| `small` | 13 | 1.5 | 400 | normal | Inter | Dense UI, card metadata, table cells |
| `micro` | 11 | 1 | 400 | normal | Inter | Timestamps, footnotes, nav hints |
| `mono-body` | 13.5 | 1.5 | 400 | normal | JetBrains Mono | Template fields, credential values |
| `mono-chip` | 11 | 1 | 500 | normal | JetBrains Mono | Inline code tags `{church_name}`, `⌘K` |

### 3.3 Numeric display

Dashboard metrics and plan detail metric rows use Space Grotesk at **28–32px / 600** with `tabular-nums` for alignment. Large decorative zeros in empty-state fallbacks are **40px / 700** in `slate-300`.

### 3.4 Don't

- **Don't mix serifs in.** The direction was explicitly chosen over the serif options.
- **Don't set body copy in Space Grotesk.** It's a display face — reading fatigue at paragraph length.
- **Don't italicize UI copy.** Reserve italics for quoted titles inside body text.
- **Don't use weight 700 in UI chrome.** 600 is the heaviest weight in buttons, labels, headings. 700 appears only in the wordmark.

---

## 4. Spacing & layout

Spacing uses Tailwind's default 4px scale (`space-1` = 4px, `space-2` = 8px, etc.). No custom scale.

### 4.1 Page layout

| Dimension | Value | Notes |
|---|---|---|
| Sidebar width | `256px` (`w-64`) | Fixed, always visible on `lg+` |
| Sidebar padding | `1.5rem` horizontal, `1rem` vertical | |
| Main content left offset | `256px` (`pl-64`) | Matches sidebar |
| Page padding | `2.5rem` horizontal (`px-10`), `2.5rem` vertical (`py-10`) | On top-level `<main>` |
| Max content width | `64rem` (`max-w-4xl` / `max-w-5xl`) | Hero uses `max-w-5xl`, forms use `max-w-4xl`, narrow reading uses `max-w-2xl` |
| Hero height | Grows to content. Minimum padding: `pt-10 pb-8 px-10` | |
| Sidebar item height | `~36px` — `py-2.5` | |

### 4.2 Grid rhythm

Dashboard uses a **4-column grid at `max-w-5xl` with `gap-10`** for settings-style pages (side-nav `col-span-1` + content `col-span-3`), and a **3-column grid with `gap-4`** for plan detail (content `col-span-2` + sidebar `col-span-1`). Metric tile rows use a **4-column grid with `gap-3`**.

### 4.3 Radii

| Token | Tailwind | Use |
|---|---|---|
| `radius-sm` | `rounded-md` (6px) | Small mono chips, keyboard keys |
| `radius-md` | `rounded-lg` (8px) | Inputs, side-nav items, logo chip |
| `radius-lg` | `rounded-xl` (12px) | Dense cards, banners, previews |
| `radius-xl` | `rounded-2xl` (16px) | Major cards (plan cards, setting sections) |
| `radius-full` | `rounded-full` | Buttons, pills, badges, avatars, search inputs |

### 4.4 Borders

**Always 1px, always `slate-200`** for the default card/divider. Exceptions:
- Selected radio card: `border-2 border-teal-500`
- Input default: `border-slate-300`
- Input focus: `border-teal-600 + ring-2 ring-teal-600/20`
- Error input: `border-rose-500 + ring-2 ring-rose-500/20` on focus
- Empty slot placeholder: `border-2 border-dashed border-slate-300`

### 4.5 Shadow

Shadow is used sparingly — **almost everything is bordered, not shadowed**.

- **Card hover lift:** `shadow-[0_8px_24px_-12px_rgba(15,23,42,0.18)]` combined with `translate-y-[-2px]`
- **Sticky save bar:** `shadow-lg` (Tailwind default)
- **Pill segment active tab:** `shadow-sm`
- No shadows on buttons, inputs, badges, or hero surfaces

---

## 5. Components

Each component lists its anatomy, variants, and the minimal HTML needed to build it. Full examples live in `mockups/components.html`.

### 5.1 Button

**Shape:** pill (`rounded-full`). **Font:** Inter 600. **Height:** sizes below. Primary action is **slate-900, not teal** — teal stays reserved for state.

| Variant | Classes |
|---|---|
| Primary | `rounded-full bg-slate-900 text-white px-5 py-2 text-[13px] font-semibold hover:bg-slate-800` |
| Secondary | `rounded-full border border-slate-300 bg-white text-slate-700 px-5 py-2 text-[13px] font-semibold hover:bg-slate-50` |
| Ghost | `rounded-full text-slate-600 px-5 py-2 text-[13px] font-semibold hover:bg-slate-100` |
| Danger | `rounded-full bg-rose-600 text-white px-5 py-2 text-[13px] font-semibold hover:bg-rose-700` |
| Accent | `rounded-full bg-teal-500 text-slate-900 px-5 py-2 text-[13px] font-semibold hover:bg-teal-400` |

**Sizes:** small `px-3 py-1 text-[11px]`, medium (default) `px-5 py-2 text-[13px]`, large `px-6 py-2.5 text-[14px]`.

**States:**
- Hover → `bg-slate-800` (primary), 1 shade lighter (other)
- Focus → add `ring-2 ring-teal-500 ring-offset-2`
- Disabled → `opacity-40 cursor-not-allowed`
- Loading → include a `h-3 w-3 rounded-full border-2 border-white/40 border-t-white animate-spin` before the label

**When to use Accent (teal-on-slate-900 text):** only for highly attention-seeking positive CTAs (e.g. a "Try auto-match" shortcut). Default CTA remains Primary (slate-900).

### 5.2 Input

**Height:** `py-2` → ~36px. **Font:** Inter 13.5px, or JetBrains Mono when the value is code/credentials/template.

```html
<input class="w-full rounded-lg border border-slate-300 bg-white
  px-3.5 py-2 text-[13.5px] text-slate-900 placeholder:text-slate-400
  focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 focus:outline-none" />
```

**Label:** `block text-[13px] font-medium text-slate-700 mb-1.5`
**Helper text:** `mt-1 text-[11px] text-slate-500`
**Error text:** `mt-1 text-[11px] text-rose-600`

**Search input** (special variant): `rounded-full`, `pl-10` (for icon) + `pr-12` (for keyboard hint `kbd`), icon at `left-3.5`, `kbd` at `right-3`.

**Textarea:** same as input plus `resize-none`.

**Select:** same as input; keep the native chevron.

### 5.3 Badge

Three sub-patterns. Always uppercase + tracked for status; sentence-case for labels.

**Status badge** — dot + uppercase label:
```html
<span class="inline-flex items-center gap-1.5 rounded-full bg-teal-50
  border border-teal-200 px-2 py-0.5 text-[10px] font-semibold
  text-teal-700 uppercase tracking-widest">
  <span class="h-1.5 w-1.5 rounded-full bg-teal-500"></span>
  Synced
</span>
```

| State | Surface | Border | Text | Dot |
|---|---|---|---|---|
| Synced | `teal-50` | `teal-200` | `teal-700` | `teal-500` |
| Pending | `amber-50` | `amber-200` | `amber-700` | `amber-500` |
| Unmatched | `rose-50` | `rose-200` | `rose-700` | `rose-500` |
| Draft | `slate-100` | `slate-200` | `slate-600` | `slate-400` |

**Label badge** (no dot): drop the dot, same surfaces. "Recommended" uses `teal-50` / `teal-700`.

**Inverse badge** (for dark surfaces): `bg-slate-900 text-white` — used for "Best match · 98%" overlays.

**Count badge:** circular, `min-w-[18px] h-[18px] px-1.5 text-[10px] font-bold`. `rose-500/white` for problems, `teal-500/slate-900` for positive counts, `slate-200/slate-700` for neutral.

**Mono chip:** for template variables and code:
```html
<span class="inline-flex items-center rounded-md border border-slate-200
  bg-slate-50 px-2 py-0.5 text-[11px] font-mono text-slate-700">{church_name}</span>
```

### 5.4 Card

**Default:** `rounded-2xl bg-white border border-slate-200 p-5`. No shadow at rest.

**Dense card:** `rounded-xl` with `p-4` instead.

**Interactive (whole-card link):** add `cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(15,23,42,0.18)]`.

**Selected:** `border-2 border-teal-500`.

**Inverse:** `rounded-2xl bg-slate-900 text-slate-100 p-5`. Use for preview blocks, mini playlist previews, success toasts inline.

**Attention:** `rounded-2xl bg-rose-50 border border-rose-200 p-5`. Only for surfaces that represent a problem.

**Placeholder (empty slot):** `rounded-2xl border-2 border-dashed border-slate-300 p-5 text-center`. Used when an integration is not connected.

### 5.5 Banner

Horizontal, full-width. One row: icon + stacked title/body + optional action.

| Type | Background | Border | Icon color |
|---|---|---|---|
| Info | `teal-50` | `teal-200` | `teal-600` |
| Warning | `amber-50` | `amber-200` | `amber-600` |
| Error | `rose-50` | `rose-200` | `rose-600` |
| Success toast (inverse) | `slate-900` | — | `teal-400` |

```html
<div class="flex items-start gap-3 rounded-xl bg-teal-50 border border-teal-200 p-4">
  <svg class="h-5 w-5 text-teal-600 shrink-0 mt-0.5">…</svg>
  <div class="flex-1">
    <p class="text-[13.5px] font-semibold text-teal-900">Title.</p>
    <p class="mt-0.5 text-[12.5px] text-teal-800">Body.</p>
  </div>
  <!-- optional action button -->
</div>
```

One banner per section at most. Never stack two banners side by side.

### 5.6 Empty state

Centered. Icon in a rounded-full tinted circle + title + one-line body + **zero or one** CTA. Never two CTAs.

```html
<div class="rounded-2xl bg-white border border-slate-200 p-10 text-center">
  <div class="mx-auto h-12 w-12 rounded-full bg-teal-50 flex items-center justify-center mb-4">
    <svg class="h-6 w-6 text-teal-600">…</svg>
  </div>
  <p class="font-display text-lg font-semibold tracking-tight">All caught up</p>
  <p class="mt-1 text-[13px] text-slate-500 max-w-[32ch] mx-auto">Every song…</p>
  <!-- optional single CTA -->
</div>
```

Icon circle tint maps to state: teal (success), slate (neutral/no-data), rose (error/not-found).

### 5.7 Tabs & navigation

**Underline tabs** — in-page view switching:
```html
<button class="pb-3 text-[13.5px] font-semibold text-slate-900
  border-b-2 border-teal-500 -mb-px">Unmatched <span class="ml-1 text-slate-400">5</span></button>
<button class="pb-3 text-[13.5px] font-medium text-slate-500 hover:text-slate-900">All mappings</button>
```

**Pill segment** — platform/scope toggles, sits inside a section:
```html
<div class="inline-flex rounded-full bg-slate-100 p-1">
  <button class="rounded-full bg-white shadow-sm px-4 py-1.5 text-[12.5px] font-semibold text-slate-900">Spotify</button>
  <button class="rounded-full px-4 py-1.5 text-[12.5px] font-medium text-slate-500">YouTube Music</button>
</div>
```

**Side nav** — multi-section forms (Settings):
```html
<nav class="w-56 space-y-1 text-[13px]">
  <a class="block px-3 py-2 rounded-lg bg-slate-100 text-slate-900 font-medium">Active item</a>
  <a class="block px-3 py-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900">Idle</a>
</nav>
```

**Primary sidebar** (app-wide) — dark surface:
- Active: `bg-slate-800 text-white font-medium`, optional trailing dot `bg-teal-400`
- Idle: `text-slate-400 hover:bg-slate-800 hover:text-white`
- Badge inside nav item: right-aligned count (`ml-auto`), `bg-rose-500 text-white` for problems

**Stepper** — onboarding flows, horizontal pill chain:
- Active step: `bg-teal-500 text-slate-900`
- Inactive / future: `bg-slate-800 text-white`
- Completed: `bg-slate-800 text-white` with leading check icon (`text-teal-400`)
- Connector: `h-px w-6 bg-slate-300`

### 5.8 Avatar

User avatar — always the brand gradient, monogrammed:
```html
<div class="h-8 w-8 rounded-full bg-gradient-to-br from-teal-400 to-rose-500
  flex items-center justify-center text-white text-xs font-bold">JP</div>
```

Sizes: 24px (`h-6 w-6 text-[10px]`), 32px (default, `h-8 w-8 text-xs`), 40px (`h-10 w-10 text-sm`), 48px (`h-12 w-12 text-base`).

### 5.9 Logo mark

Dog-eared teal bulletin with a play triangle and two queued track rows. Reads as "a service plan that's playable" — bridging the church service plan and the streaming playlist. Ships as the `LogoMark` component (`frontend/src/components/ui/LogoMark.tsx`) with a preserved `size` prop API.

```tsx
import LogoMark from "@/components/ui/LogoMark";

<LogoMark />             // md / 32px (default)
<LogoMark size="sm" />   // 24px
<LogoMark size="lg" />   // 48px
```

**Sizes:** 24px (`sm`, favicon / compact), 32px (`md`, sidebar / headers), 48px (`lg`, auth pages / hero).

**Colors:**

| Element | Class / Token | Hex |
| --- | --- | --- |
| Badge body | `fill-current` driven by `text-teal-500` | `#14B8A6` |
| Fold (page peel) | `fill-slate-100/40` | `#F1F5F9` @ 40% |
| Play triangle, track rows | `fill-slate-100` | `#F1F5F9` |

The mark ships with slate-100 interior on teal — which inverts the bar/chip convention from the placeholder. This was deliberate: the dog-ear silhouette + play glyph + two rows are what carry brand recognition, and slate-100 interior preserves the "bulletin cover" feel at every size down to 16px favicon. No inverse variant is needed — the same mark reads correctly on slate-900 and on the cool off-white canvas.

**Full lockup (mark + wordmark):** use the `Logo` component for auth pages, empty states, and headers where the wordmark belongs.

```tsx
import Logo from "@/components/ui/Logo";

<Logo size="lg" />
```

The wordmark uses a Service/Tracks color split — "Service" picks up the ambient foreground, "Tracks" is `text-teal-500` to echo the mark. Uses `font-display` (Space Grotesk) from `@theme`.

**Clear space:** maintain ~25% of the mark's height on all sides.

**Minimum size:** 16px favicon. Below that the play triangle and row detail collapse — no dedicated small-size variant currently exists.

**Favicon assets** (`frontend/public/`):

- `favicon.svg` — primary, modern browsers
- `favicon-16.png`, `favicon-32.png`, `favicon-48.png` — raster fallbacks
- `apple-touch-icon.png` (180×180) — iOS home screen
- `android-chrome-192x192.png`, `android-chrome-512x512.png` — Android / PWA manifest

### 5.10 Song row (composite, plan detail)

Listed because it's the densest repeating pattern in the app. Full structure in `mockups/plan-detail.html`.

- Left: two-digit index (`font-mono text-[11px] text-slate-400 tabular-nums`).
- Cover art: `h-10 w-10 rounded-md` gradient (one of the four approved recipes).
- Middle: title (`text-[14px] font-medium text-slate-900`) + artist (`text-[12px] text-slate-500`).
- Right: duration (`font-mono text-[12px] tabular-nums text-slate-500`) + overflow menu icon on hover.
- Unmatched variant: row background `bg-rose-50/20`, cover placeholder is `border-2 border-dashed border-rose-200`, action is "Find match →" in `text-rose-600`.

### 5.11 Form save bar

Sticky at the bottom of settings-style forms:
```html
<div class="sticky bottom-4 flex items-center justify-between gap-4
  rounded-2xl bg-white border border-slate-200 shadow-lg p-4">
  <div class="flex items-center gap-2 text-[13px] text-slate-500">
    <span class="h-1.5 w-1.5 rounded-full bg-teal-500"></span>
    <span>Unsaved changes</span>
  </div>
  <div class="flex items-center gap-2">
    <!-- Secondary "Discard" + Primary "Save" -->
  </div>
</div>
```

Teal dot pulses subtly only when dirty. Hide the bar when form is pristine.

---

## 6. Motion

Short, purposeful, never decorative. All durations are explicit — no magic `transition` shortcut where it applies to *everything*.

| Purpose | Duration | Easing | Implementation |
|---|---|---|---|
| Hover color/bg swap | `150ms` | `ease-out` | Tailwind `transition-colors` |
| Card lift | `150ms` | `ease-out` | `transition-all` + `translate-y` |
| Modal / drawer enter | `200ms` | `ease-out` | Custom |
| Toast slide-in | `180ms` | `ease-out` | Custom |
| Focus ring | instant | — | No transition; focus should feel immediate |
| Spinner | `1s` | `linear infinite` | `animate-spin` |
| Stepper progress | `300ms` | `ease-in-out` | When the step advances |

**No transitions on:**
- Font size changes
- Layout shifts (width/height of containers)
- Appearance of modals' backdrop (fade-in fine; don't animate backdrop blur)

---

## 7. Iconography

**Library:** [Lucide](https://lucide.dev/) — ships as `lucide-react`, tree-shakable, matches the line-weight aesthetic.

**Sizing:**
- `h-3.5 w-3.5` — inside small buttons
- `h-4 w-4` — sidebar, inline icons, inside inputs
- `h-5 w-5` — banners, cards
- `h-6 w-6` — empty-state icons, large touch targets

**Stroke:** always `stroke-width="2"`. Never fill an icon unless the product is a stock pictogram (`currentColor` on a solid shape) — the logo mark is the only such case.

**Color:**
- Idle UI: `text-slate-400` or `text-slate-500`
- Active UI: `text-slate-900`
- In banners: match banner text tone (`text-teal-600`, `text-amber-600`, `text-rose-600`)
- On inverse surfaces: `text-teal-400` for accent, `text-slate-300` for muted

Don't introduce multi-color icons or icon illustrations. Monoline, current-color only.

---

## 8. Voice & tone

### 8.1 Copy rules

- **Sentence case** everywhere except status badges (which are `UPPERCASE TRACKED`).
- **Verb-first for actions:** "Connect Spotify", "Match song", "Save settings" — not "Spotify connection", "Song matching".
- **No trailing punctuation in buttons, labels, or single-line cells.** Periods only in body copy with multiple sentences.
- **Use contractions.** "We'll retry", "You're all caught up" — not "We will retry", "You are".
- **Quantify when possible.** "3 of 5 songs matched", not "Most songs matched".
- **Avoid app-speak.** No "awesome", "oops", or "uh-oh". Tone is quietly competent, not bubbly.
- **Name the integration partner, don't abstract.** "Reconnect Spotify" beats "Reconnect streaming service" when the platform is known.

### 8.2 Error messages

Two-line max. Line 1 = what happened. Line 2 = what we're doing about it or what the user should do.

> **Sync failed — YouTube rate limit hit.**
> We'll retry automatically in 15 minutes.

Never apologize in errors (no "Sorry, something went wrong"). Never blame the user (no "You entered an invalid…" — prefer "This email isn't valid").

### 8.3 Success messages

Past-tense, declarative. No exclamation marks.

> **Settings saved**
> Your next sync will use the new playlist name template.

### 8.4 Empty states

Positive when they represent a desirable state ("All caught up"), neutral-descriptive when they represent absence ("No plans yet"). Never passive-aggressive ("Nothing to see here…").

### 8.5 Date & number formatting

- **Dates in UI:** `Sun · Apr 19` or `April 19, 2026` depending on space. Use `·` (middle dot) as the separator, not pipe or dash.
- **Relative times:** `2h ago`, `3 days`. Fall back to absolute after 7 days.
- **Counts in nav badges:** bare number, no leading zeros. 99+ collapses to `99+`.
- **Percentages:** integer, no decimals (`98%` not `98.2%`).
- **Durations in song rows:** `M:SS` monospaced, tabular-nums.

---

## 9. Tailwind config

The full set of overrides needed to implement this system. Drop into `tailwind.config.js`:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        slate: {
          50: '#F8FAFC', 100: '#F1F5F9', 200: '#E2E8F0', 300: '#CBD5E1',
          400: '#94A3B8', 500: '#64748B', 600: '#475569', 700: '#334155',
          800: '#1E293B', 900: '#0F172A', 950: '#070B14',
        },
        teal: {
          50: '#F0FDFA', 100: '#CCFBF1', 200: '#99F6E4',
          400: '#2DD4BF', 500: '#14B8A6', 600: '#0D9488', 700: '#0F766E',
        },
        rose: {
          50: '#FFF1F2', 100: '#FFE4E6', 200: '#FECDD3',
          400: '#FB7185', 500: '#F43F5E', 600: '#E11D48', 700: '#BE123C',
        },
        amber: {
          50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A',
          400: '#FBBF24', 500: '#F59E0B', 600: '#D97706', 700: '#B45309',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'sans-serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
};
```

Add the Google Fonts link to `frontend/index.html` (see §3 for the exact tag).

---

## 10. Implementation readiness

This doc and the mockups together should answer any question a developer (or Claude in a follow-up task) has while building real screens. If a decision is needed that isn't covered above:

1. Check `mockups/components.html` — the live reference.
2. Check the relevant screen mockup (`mockups/<screen>.html`) for how a primitive composes in context.
3. If neither has it, **update this doc first**, then build. No orphan decisions.

### Traceability

Every section of this doc maps to at least one mockup:

| Section | Primary mockup |
|---|---|
| Color, gradients | `dashboard-c-refined-3.html`, `login.html` |
| Typography | `plan-detail.html` (metric row), `dashboard-c-refined-3.html` (hero) |
| Button | `components.html`, every screen with a CTA |
| Input | `settings.html`, `setup-pco.html`, `song-match.html` |
| Badge | `dashboard-c-refined-3.html`, `plan-detail.html`, `songs.html` |
| Card | `dashboard-c-refined-3.html` (plan cards), `setup-streaming.html` |
| Banner | `setup-streaming.html`, `components.html` |
| Empty state | `components.html` |
| Tabs / nav | `songs.html`, `settings.html`, `setup-pco.html` |
| Avatar / logo | every screen (sidebar footer + header) |
| Song row | `plan-detail.html` |
| Save bar | `settings.html` |

---

## 11. Open questions & follow-ups

These are deliberately deferred and tracked separately:

- **Real logo** — Task #15. Current mark is a placeholder designed to scale but not to be memorable.
- **Dark mode** — not in v1. The palette is structured to allow it later: slate tokens already span 50→950, and no component depends on an opaque `white`.
- **Illustrations** — out of scope. If marketing needs them, revisit as a separate track.
- **Marketing site** — not covered by this doc. If added, it may extend the palette (carefully).
- **Mobile responsive rules** — the current mockups are desktop-first. Responsive breakpoints need a follow-up pass; at minimum, the sidebar needs to collapse under `lg`.

---

*This doc is the source of truth. Screens in `mockups/` are its illustrations. Pull requests that change the visual system must update this file in the same commit.*
