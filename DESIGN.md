---
version: alpha
name: PlayStreet v2
description: Playful-premium sneaker design OS — PlayQ energy meets streetwear catalog.
colors:
  primary: "#00C4FF"
  secondary: "#0B1B2B"
  tertiary: "#FF3D9A"
  accent-yellow: "#FFE566"
  accent-lime: "#B8F24A"
  accent-coral: "#FF6B4A"
  neutral: "#F4FBFF"
  surface: "#FFFFFF"
  ink: "#0F1A2E"
  muted: "#4A5B6A"
  teal-deep: "#0090B8"
  cyan-bright: "#00E5FF"
  magenta: "#ED007F"
  pink-soft: "#FF8FD6"
typography:
  h1:
    fontFamily: Nunito
    fontSize: 3.5rem
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  h2:
    fontFamily: Nunito
    fontSize: 2.25rem
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  h3:
    fontFamily: Nunito
    fontSize: 1.35rem
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  body-md:
    fontFamily: Nunito Sans
    fontSize: 1rem
    fontWeight: 500
    lineHeight: 1.6
  body-sm:
    fontFamily: Nunito Sans
    fontSize: 0.875rem
    fontWeight: 500
    lineHeight: 1.5
  label:
    fontFamily: Nunito Sans
    fontSize: 0.75rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
rounded:
  sm: 10px
  md: 16px
  lg: 24px
  xl: 32px
  pill: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  2xl: 64px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.lg}"
    padding: 16px
  button-primary-hover:
    backgroundColor: "{colors.magenta}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.teal-deep}"
    rounded: "{rounded.lg}"
    padding: 16px
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 12px
  card-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 20px
  badge-live:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.teal-deep}"
    rounded: "{rounded.pill}"
    padding: 8px
  nav-pill-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: 10px
---

## Overview

**PlayStreet v2** = *sneaker design OS with playground energy*.

Not corporate SaaS. Not sterile Pinterest white. Closer to **PlayQ**: bright cyan skies, bold friendly type, soft 3D/2.5D shapes, micro-bounce motion — but rooted in **streetwear / sneaker culture** (urban, creative, catalog-first).

**One-liner vibe:** *“Design sneakers like you’re in a colorful studio arcade.”*

**Brand tensions to hold:**
- Playful ≠ childish (premium materials, tight spacing, real product photos)
- Street ≠ dark-only (light cyan world is default; dark mode = night studio)
- Energy ≠ chaos (1–2 accents per view max)

---

## Colors

### Core palette

| Token | Hex | Role |
|-------|-----|------|
| **primary** | `#00C4FF` | Sky cyan — hero gradients, active states, brand wash |
| **cyan-bright** | `#00E5FF` | Highlight / glow edge |
| **teal-deep** | `#0090B8` | Secondary CTA text, links on light surfaces |
| **tertiary / hot pink** | `#FF3D9A` | Primary CTA fill (PlayQ pop) |
| **magenta** | `#ED007F` | CTA hover / brand mark kinship with Workflow Planner Z |
| **accent-yellow** | `#FFE566` | Badges, sparklines, “new” chips |
| **accent-lime** | `#B8F24A` | Success / Finish status |
| **accent-coral** | `#FF6B4A` | Warning / attention (use sparingly) |
| **ink** | `#0F1A2E` | Headlines on light / cyan |
| **muted** | `#4A5B6A` | Body secondary |
| **surface** | `#FFFFFF` | Cards, nav glass |
| **neutral** | `#F4FBFF` | Soft app chrome (ice) |
| **secondary** | `#0B1B2B` | Dark mode base / night studio |

### Gradients (signature)

```css
/* Hero sky — PlayQ energy */
--grad-hero: linear-gradient(165deg, #00E5FF 0%, #00C4FF 35%, #00A8D8 70%, #0088B8 100%);

/* Card glow */
--grad-card-edge: linear-gradient(135deg, rgba(0,229,255,0.4), rgba(255,61,154,0.25));

/* Night studio (dark mode) */
--grad-night: linear-gradient(165deg, #0B1B2B 0%, #123047 50%, #0A2233 100%);

/* CTA shine */
--grad-cta: linear-gradient(135deg, #FF3D9A 0%, #ED007F 100%);
```

### Status (keep semantic, make playful)

| Status | Fill | Text |
|--------|------|------|
| Draft | `#FFE566` | `#0F1A2E` |
| Proses | `#00C4FF` | `#0F1A2E` |
| Finish | `#B8F24A` | `#0F1A2E` |

### Do / Don’t

- **Do** put black/ink text on cyan hero (max contrast).
- **Do** use pink only for *one* primary action per screen.
- **Don’t** stack pink + yellow + lime CTAs together.
- **Don’t** use pure gray `#6b7280` body on cyan — use `#0F1A2E` / `#222` / white.

---

## Typography

### Stack

| Role | Family | Why |
|------|--------|-----|
| **Display / H1–H3** | **Nunito** 700–800 | Rounded, friendly, bold — closer to PlayQ than Sora’s tech-sharp |
| **UI / body** | **Nunito Sans** 500–700 | Matches display, excellent UI density |
| **Fallback** | system-ui, sans-serif | |

*Migration path from current Sora + Inter: swap Google Fonts import; keep scale clamps.*

### Scale

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| display | clamp(2.5rem, 7vw, 4.25rem) | 800 | Welcome H1 |
| h2 | clamp(1.75rem, 4vw, 2.5rem) | 800 | Section titles |
| h3 | 1.25–1.5rem | 700 | Cards |
| body | 1rem / 1.6 | 500 | Subtitles, descriptions |
| body-sm | 0.875rem | 500 | Meta, timestamps |
| label | 0.6875–0.75rem | 700 | Badges, filters (slight tracking) |
| stat | 1.75rem | 800 | Hero stats |

**Voice in type:** short punchy headlines, sentence-case UI (not ALL CAPS walls), status pills OK uppercase.

---

## Layout & Spacing

- **Page gutters:** 16px mobile · 24–32px desktop
- **Section rhythm:** 32–48px (tighter than enterprise — less “empty SaaS”)
- **Hero padding:** 24px top (keep King’s density preference — no huge whitespace)
- **Card padding:** 16–20px
- **Grid gallery:** denser masonry feel, gap 10–12px mobile / 14–16px desktop
- **Max content:** 1200px features · full-bleed hero sky

---

## Elevation & Depth

PlayQ depth = **soft blobs + floating cards**, not hard Material shadows.

```css
--shadow-float: 0 12px 40px rgba(0, 80, 120, 0.18);
--shadow-card: 0 8px 24px rgba(15, 26, 46, 0.08);
--shadow-cta: 0 8px 28px rgba(237, 0, 127, 0.35);
--shadow-pop: 0 4px 0 #0F1A2E; /* optional sticker / comic edge */
```

- Orbs: large blurred circles (cyan + pink + yellow @ 12–20% opacity)
- Optional **sticker edge** on hero badge (`box-shadow: 3px 3px 0 #0F1A2E`)
- Cards lift `-4px` on hover with bounce easing

---

## Shapes

| Token | Value | Use |
|-------|-------|-----|
| sm | 10px | inputs, small chips |
| md | 16px | buttons, filters |
| lg | 24px | cards, modals |
| xl | 32px | hero panels |
| pill | 999px | badges, nav active |

**Motif:** slightly chunkier radii than current 10–12px → more toy/arcade, still premium.

---

## Motion

```css
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
--ease-soft: cubic-bezier(0.22, 1, 0.36, 1);
--dur-fast: 150ms;
--dur-med: 280ms;
```

| Interaction | Motion |
|-------------|--------|
| Button hover | `translateY(-2px) scale(1.02)` + bounce ease |
| Card hover | `translateY(-4px)` + stronger float shadow |
| Page enter | fade + 12px up, 400ms soft |
| Badge live | soft pulse (green/magenta dot) |
| Filter pill | scale 0.96 → 1 on press |
| Theme toggle | 200ms icon swap, no layout jump |

**Rule:** delightful, never blocking. Respect `prefers-reduced-motion`.

---

## Components (what must change)

### 1. Navigation
- **From:** flat gray bar + red underline  
- **To:** frosted white / ice bar on cyan world; **active = cyan pill** or magenta underline 3px rounded  
- Logo Z stays magenta/red mark  
- Theme + ADMIN stay right-clustered, more “toy toggle” (chunky track)

### 2. Hero (`/welcome`)
- Full **sky gradient** (cyan family) fixed  
- H1 ink black, no gradient-fill text  
- Badge: white sticker + yellow or magenta dot  
- Primary CTA: **pink gradient pill**  
- Secondary: white + teal text  
- Stats: glass or deep-teal capsule with white numbers  
- Optional: 1 floating 2.5D sneaker / blob illustration (CSS or static PNG later)

### 3. Buttons
| Variant | Style |
|---------|--------|
| primary | `#FF3D9A` → hover `#ED007F`, white text, `rounded-2xl`, pink glow |
| secondary | white, teal text, light border |
| tertiary / ghost | transparent, ink text, hover ice fill |
| danger | coral fill, rare |

### 4. Cards (tasks + gallery)
- White surface, `rounded-2xl`–`3xl`  
- Border: ice or 1px cyan @ 15%  
- Hover: lift + cyan/pink edge glow  
- Status pills: yellow / cyan / lime (not muted gray)  
- Gallery image cards: keep dark gradient caption strip for photo contrast  

### 5. Filters
- Inactive: white/ice chip  
- Active: cyan fill + ink text (or pink for “selected count”)  
- Slightly larger hit targets (min 40px)

### 6. Forms / modals
- Ice background, thick soft border  
- Focus ring: cyan 2–3px  
- Submit = primary pink  

### 7. Empty / loading
- Playful illustration placeholder + short line (“No kicks in this lane yet”)  
- Skeleton: cyan shimmer, not gray pulse only  

### 8. Footer version badge
- Pill ice/teal, not pure dark corporate  

### 9. Dark mode
- Night studio gradient (navy-teal)  
- Cards elevated slate  
- Pink CTA retained (still pops)  
- Status pills keep chroma  

---

## Illustration direction (PlayQ DNA)

**P3 shipped (DEV):** pure CSS 2.5D system — no image assets.

| Class | What |
|---|---|
| `.zen-art` | Stage (sneaker + sole + palette + sparks + dashed ring) |
| `.zen-empty` / `.zen-empty-sm` | Empty card + copy + pink CTA |
| `.zen-welcome-props` | Floating props L/R on Welcome (desktop ≥900px) |

Wired empty states: tasks empty, task search no-results, gallery empty, In Work empty, Finished empty, Proses empty lane.

Tone: adventurous creative studio — not baby cartoon. Sneaker photo gallery remains the hero of real content.

---

## Implementation map (codebase)

| Layer | File / target |
|-------|----------------|
| Tokens | `:root` + `html[data-theme]` in `static/index.html` |
| Welcome skin | `body[data-page="welcome"]` + `.zen-welcome-props` |
| Global light BG | ice/cyan system (P1) |
| Fonts | Nunito + Nunito Sans |
| Components | `.premium-*`, `.task-card`, `.img-tile`, `.status-filter-btn`, nav, `.zen-empty` |

**Phased rollout (DEV):**
1. **P0** — Welcome PlayStreet ✅  
2. **P1** — Global tokens + fonts + buttons + filters ✅  
3. **P2** — Cards, gallery chrome, motion, nav ✅  
4. **P3** — CSS 2.5D art + empty states ✅  

Prod: not shipped until King says go.

---

## Do's and Don'ts

**Do**
- Lead with cyan sky + one hot CTA  
- Keep sneaker photography hero of gallery  
- Dense, useful layouts (King: less empty air)  
- High contrast text on color fields  

**Don't**
- Copy PlayQ game characters into product UI  
- Turn every page into a carnival  
- Lose status color semantics  
- Break dark-mode persistence (`workflow-theme`)  

---

## Tailwind quick map

```js
// conceptual theme.extend.colors
workflow: {
  cyan:    { DEFAULT: '#00C4FF', bright: '#00E5FF', deep: '#0090B8' },
  pink:    { DEFAULT: '#FF3D9A', hot: '#ED007F' },
  yellow:  '#FFE566',
  lime:    '#B8F24A',
  coral:   '#FF6B4A',
  ink:     '#0F1A2E',
  ice:     '#F4FBFF',
  night:   '#0B1B2B',
}
```

```html
<!-- Primary CTA -->
<a class="rounded-2xl bg-[#FF3D9A] hover:bg-[#ED007F] text-white font-bold px-7 py-3.5 shadow-[0_8px_28px_rgba(237,0,127,0.35)] transition duration-300 hover:-translate-y-0.5">
  Explore Tasks
</a>
```
