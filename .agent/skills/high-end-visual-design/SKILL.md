---
name: high-end-visual-design
description: Awwwards/Linear/Apple-tier visual design system. Use when building any new screen, panel, or component in Splic. Enforces double-bezel card architecture, spatial rhythm, haptic microinteractions, GPU-safe scroll animations, and the variance engine for non-repetitive premium output.
category: ui-design
risk: safe
source: sickn33/agentic-awesome-skills (Leonxlnx/taste-skill)
date_added: "2026-11-12"
author: Leonxlnx
tags: [premium-ui, visual-design, motion, awwwards, apple-tier, timeline-studio]
tools: [antigravity, claude-code, cursor, gemini-cli]
---

# High-End Visual Design — Awwwards-Tier UI for Splic

Covers the full visual language for any new Timeline Studio surface. Every component must read as "$150k agency build", not "template with nice fonts."

---

## 1. The Absolute Zero Directive (Hard Bans)

If generated code includes any of the following, the design **instantly fails**:

| Banned | Why |
| :--- | :--- |
| **Emojis anywhere in UI chrome** | Use `lucide-react` icons with `strokeWidth={1.25}` exclusively |
| Fonts: Inter, Roboto, Arial, Open Sans | Generic AI defaults. Use `-apple-system` / `'Geist'` / `'Plus Jakarta Sans'` |
| Icons: thick-stroked Lucide / Material | Use only `lucide-react` with `strokeWidth={1.25}` — no emojis ever |
| Borders: `1px solid gray` solid borders | Use gradient hairlines or `border-white/8` vibrancy borders |
| Shadows: `shadow-md`, `rgba(0,0,0,0.3)` | Use ambient soft-diffuse: `0 32px 64px rgba(0,0,0,0.52)` |
| Motion: `linear`, `ease-in-out`, instant | Use custom cubic-beziers or spring physics at all times |
| Layouts: edge-to-edge navbars, Bootstrap 3-col grids | Use floating islands, bento grids, asymmetric splits |

---

## 2. The Double-Bezel Card Architecture (Mandatory for All Cards)

Every card, panel, popover, and input must use nested enclosure — like a glass plate in an aluminum tray:

```tsx
{/* Outer Shell — the aluminum tray */}
<div className="rounded-[2rem] p-[1.5px] bg-gradient-to-b from-white/10 to-white/[0.03] shadow-[0_32px_64px_rgba(0,0,0,.52)]">
  {/* Inner Core — the glass surface */}
  <div className="rounded-[calc(2rem-1.5px)] bg-zinc-900/80 backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,.08)] px-6 py-5">
    {children}
  </div>
</div>
```

---

## 3. Spatial Rhythm & Breathing Room

Timeline Studio is a pro tool. Its UI must feel **spacious and uncluttered**, not cramped:

- Section padding: minimum `py-6` for inline toolbar areas, `py-10` for dedicated panels.
- Component gaps: `gap-3` for tight clusters, `gap-5` for panel sections.
- Never stack interactive controls at less than `gap-2` apart.
- Eyebrow labels (like track type tags): `text-[10px] uppercase tracking-[0.18em] font-medium text-white/40`

---

## 4. Scroll & Viewport Entry Animations

No element should appear statically. Use Framer Motion `whileInView` — never `window.addEventListener('scroll')`:

```tsx
<motion.div
  initial={{ opacity: 0, y: 12, filter: 'blur(4px)' }}
  whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
  viewport={{ once: true, margin: '-40px' }}
  transition={{ duration: 0.5, ease: [0.32, 0.72, 0, 1] }}
>
```

For staggered groups (e.g., track items appearing):
```tsx
transition={{ duration: 0.4, delay: index * 0.06, ease: [0.32, 0.72, 0, 1] }}
```

---

## 5. GPU-Safe Animation Guardrails

| ✅ Animate These | ❌ Never Animate These |
| :--- | :--- |
| `transform` (translate, scale, rotate) | `top`, `left`, `width`, `height` |
| `opacity` | `box-shadow`, `border-radius` continuously |
| `filter: blur()` for reveal only | `background-color` on large surfaces |

- `will-change: transform` only on elements *actively animating* — remove afterward.
- `backdrop-blur` only on `position: fixed` or `position: sticky` elements. Never on scrolling containers.

---

## 6. The Magnetic Button (Hover Physics)

Primary CTAs must feel alive on hover:

```tsx
<motion.button
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.97 }}
  transition={{ type: 'spring', stiffness: 400, damping: 25 }}
  className="group ..."
>
  <span>Label</span>
  {/* Trailing icon with kinetic tension */}
  <motion.span
    className="w-6 h-6 rounded-full bg-white/8 flex items-center justify-center"
    whileHover={{ x: 2, y: -1, scale: 1.1 }}
    transition={{ type: 'spring', stiffness: 500, damping: 20 }}
  >
    <ArrowUpRight size={12} strokeWidth={1.5} />
  </motion.span>
</motion.button>
```

---

## 7. Pre-Output Checklist

Before shipping any UI component, verify:
- [ ] No banned fonts, icons, borders, shadows, or motion from Section 1
- [ ] All cards use Double-Bezel nested architecture
- [ ] Buttons use magnetic hover + trailing icon pattern
- [ ] All motion uses `transform`/`opacity` only — no layout-triggering properties
- [ ] `backdrop-blur` only on fixed/sticky elements
- [ ] Entry animations present — nothing appears statically
- [ ] Design reads as "pro video tool" not "generic SaaS dashboard"
