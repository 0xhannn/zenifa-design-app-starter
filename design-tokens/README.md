# PlayStreet Design Tokens

PlayQ-inspired tokens for Workflow Planner.

## Files
| File | Use |
|---|---|
| `playstreet.tailwind.js` | `theme.extend` for Tailwind config |
| `playstreet.components.css` | Standalone button/card/badge/toggle CSS |
| `../DESIGN.md` | Narrative system + rollout |
| `../static/index.html` | **Live** CSS vars + components (DEV :3888) |

## Palette snapshot
| Role | Hex |
|---|---|
| Primary cyan | `#00D4FF` → `#00A3CC` |
| CTA pink | `#FF3D9A` / hover `#ED007F` |
| Yellow | `#FFE566` |
| Orange/coral | `#FF6B4A` |
| Soft purple | `#9B6DFF` |
| Lime (finish) | `#B8F24A` |
| Ink navy | `#0F1A2E` |
| Ice / off-white | `#F4FBFF` |
| Night | `#0B1B2B` |

## Tailwind wire-up
```js
// tailwind.config.js
const playstreet = require('./design-tokens/playstreet.tailwind.js');

module.exports = {
  darkMode: ['selector', '[data-theme="dark"]'], // or invert: light = data-theme="light"
  theme: { extend: playstreet },
  // ...
};
```

## Class map (components.css)
| Class | Role |
|---|---|
| `.z-btn-primary` | Pink CTA |
| `.z-btn-secondary` | White/cyan |
| `.z-btn-ghost` | Ice wash |
| `.z-btn-cyan` | Brand chip button |
| `.z-card` / `.z-card-glass` | Surface + hover lift + cyan glow |
| `.z-badge-live` | Sticker badge |
| `.z-tag` / `.z-tag-pink`… | Soft tags |
| `.z-status-draft\|proses\|finish` | Workflow pills |
| `.z-chip` + `.is-active` | Filters |
| `.z-theme-toggle` | Fun sun/moon switch |

## Dark mode contract
- Persist: `localStorage['workflow-theme']` = `'light' | 'dark'`
- Light: `html[data-theme="light"]`
- Dark: **no** data-theme (or remove attr) — matches current app init
- Toggle must save the **same** value as visual state (bug fixed 2026-07)

## Rules
1. **One** hot pink CTA per screen  
2. Ink/black text on cyan fields  
3. Status colors stay semantic (yellow/cyan/lime)  
4. Density: hero pad ~24px, cards ~20px — no empty SaaS air  
