---
name: ios-premium-ui
description: Apple HIG + iOS 18 Liquid Glass premium UI system for Timeline Studio. Use when building any new UI surface — buttons, panels, overlays, modals, status bars. Enforces squircle geometry, Dynamic Island-style spring physics, SF Pro typescale, and haptic-grade microinteractions.
category: ui-design
risk: safe
source: sickn33/agentic-awesome-skills + apple-hig
date_added: "2026-11-12"
tags: [ios, apple, premium-ui, glassmorphism, motion, timeline-studio]
tools: [antigravity, claude-code, cursor, gemini-cli]
---

# iOS Premium UI — Apple-Grade Design System for Splic

Enforces Apple Human Interface Guidelines, iOS 18 Liquid Glass aesthetics, and Dynamic Island-class spring physics inside Timeline Studio's dark creator environment.

---

## 0. Absolute UI Rule — No Emojis, Lucide Only

**NEVER** use emojis in any UI element — buttons, labels, tooltips, toasts, panel titles, status text, track headers, or any other interface chrome. This is a hard ban with no exceptions.

**ALWAYS** use `lucide-react` for all iconography:
```tsx
import { Zap, Scissors, ChevronRight, Loader2, Check, X } from 'lucide-react'
// strokeWidth={1.25} for all icons — matches the ultra-light premium aesthetic
<Zap size={14} strokeWidth={1.25} className="text-amber-400" />
```

**Exception:** Emojis are allowed only inside video content that gets burned into the exported MP4 (e.g. karaoke caption text, sticker overlays). Never in UI chrome.

---

## 1. The Three Non-Negotiables (Always)

1. **Squircles, not circles**: All rounded corners use `border-radius: 28px` (card) / `22px` (button) / `16px` (chip) with the iOS continuous-curve squircle formula. In Tailwind: `rounded-[28px]`. Never use `rounded-xl` for primary UI chrome.
2. **Spring Physics, not CSS eases**: Every state transition uses spring curves. Use Framer Motion `spring({ stiffness: 400, damping: 28 })` for interactions, `spring({ stiffness: 280, damping: 22 })` for modal/panel entrances. The iOS drawer curve: `cubic-bezier(0.32, 0.72, 0, 1)`.
3. **Layered Vibrancy, not flat dark**: UI chrome must feel like frosted glass over the timeline canvas (video content), not opaque panels pasted on top.

---

## 2. The Splic Dark Glass Palette

Match Timeline Studio's existing dark zinc base. All new surfaces sit *above* it as translucent glass layers:

```css
/* Background Layers (never change these) */
--surface-base:     #09090b;          /* zinc-950 — editor background */
--surface-elevated: rgba(24,24,27,.82); /* zinc-900/82 — floating panels */
--surface-glass:    rgba(255,255,255,.06); /* frosted card surfaces */
--surface-glass-hi: rgba(255,255,255,.10); /* hover / active state */

/* Borders — always hairline vibrancy, not solid */
--border-subtle:    rgba(255,255,255,.08);
--border-active:    rgba(255,255,255,.18);

/* Accent — Splic's amber/orange for Desi Auto-Cut actions */
--accent-desi:      #f59e0b;           /* amber-500 */
--accent-desi-glow: rgba(245,158,11,.20);

/* Text */
--text-primary:     rgba(255,255,255,.92);
--text-secondary:   rgba(255,255,255,.52);
--text-tertiary:    rgba(255,255,255,.32);
```

---

## 3. The Glass Card System (Liquid Glass)

Every new floating panel, popover, or status overlay uses this exact shell structure:

```tsx
/* Outer Shell — acts like the aluminum bezel */
<div className="
  rounded-[28px] p-[1px]
  bg-gradient-to-b from-white/12 to-white/4
  shadow-[0_32px_64px_rgba(0,0,0,.52),0_1px_1px_rgba(255,255,255,.06)_inset]
">
  {/* Inner Core — the actual glass surface */}
  <div className="
    rounded-[27px] px-5 py-4
    bg-zinc-900/80 backdrop-blur-2xl
    shadow-[inset_0_1px_1px_rgba(255,255,255,.08)]
  ">
    {children}
  </div>
</div>
```

**Rules:**
- `backdrop-blur-2xl` only on fixed/floating elements. Never on scrolling containers.
- The 1px gradient outer ring simulates the iOS specular edge highlight.
- Inner radius = outer radius − 1 (hence 27px inside 28px).

---

## 4. The "Desi Auto-Cut" Button (Primary CTA)

This is the most critical UI piece. It must feel as premium as a Dynamic Island interaction. Use `lucide-react`'s `Zap` icon — never the ⚡ emoji:

```tsx
import { Zap, ChevronRight } from 'lucide-react'

<button
  className="
    group relative flex items-center gap-2.5
    rounded-full px-4 py-2
    bg-gradient-to-b from-amber-400/20 to-amber-500/10
    border border-amber-500/25
    shadow-[0_0_20px_rgba(245,158,11,.12),inset_0_1px_0_rgba(255,255,255,.08)]
    text-amber-300 text-[13px] font-semibold tracking-[-0.01em]
    transition-all duration-150
    hover:border-amber-400/40 hover:shadow-[0_0_28px_rgba(245,158,11,.22)]
    active:scale-[0.97]
  "
  style={{ transition: 'all 150ms cubic-bezier(0.32,0.72,0,1)' }}
>
  <Zap size={13} strokeWidth={1.5} className="text-amber-400 fill-amber-400/30" />
  <span>Desi Auto-Cut</span>
  {/* Nested trailing icon — Apple Button-in-Button pattern */}
  <span className="
    w-5 h-5 rounded-full
    bg-amber-500/15 border border-amber-500/20
    flex items-center justify-center
    group-hover:translate-x-0.5 group-hover:bg-amber-500/25
    transition-all duration-150
  ">
    <ChevronRight size={11} strokeWidth={1.5} className="text-amber-300" />
  </span>
</button>
```

---

## 5. Status Pill (Pipeline Progress)

Replaces any spinner with a Dynamic Island-inspired pill that morphs between states:

```tsx
// Pill morphs width via spring animation (Framer Motion layout animation)
<motion.div
  layout
  className="
    flex items-center gap-2 overflow-hidden
    rounded-full px-3.5 py-1.5
    bg-zinc-900/90 backdrop-blur-xl
    border border-white/10
    shadow-[0_8px_24px_rgba(0,0,0,.4)]
    text-[12px] text-white/70 font-medium
  "
  transition={{ type: 'spring', stiffness: 400, damping: 28 }}
>
  <motion.div
    className="w-2 h-2 rounded-full bg-amber-400"
    animate={{ scale: [1, 1.4, 1] }}
    transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
  />
  <motion.span layout="position">{statusText}</motion.span>
</motion.div>
```

---

## 6. Typography Scale (SF Pro Equivalent)

Use `font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif` — the system font on macOS/iOS IS SF Pro. Never specify Inter directly for heading text; let the platform serve its native font.

| Role | Size | Weight | Tracking | Use |
| :--- | :--- | :--- | :--- | :--- |
| Label | 11px | 500 | +0.08em | Chip labels, metadata |
| Body | 13px | 400 | -0.01em | Descriptions, list items |
| Headline | 15px | 600 | -0.02em | Panel titles |
| CTA | 13px | 600 | -0.01em | Buttons, action text |

---

## 7. Motion Timing Reference

| Interaction | Duration | Curve |
| :--- | :--- | :--- |
| Button press / chip tap | 120ms | `cubic-bezier(0.32,0.72,0,1)` |
| Popover / tooltip open | 180ms | `spring(stiffness:400, damping:28)` |
| Panel / sheet slide-in | 340ms | `spring(stiffness:280, damping:22)` |
| Status pill morph | spring | `spring(stiffness:400, damping:28)` |
| Toast enter/exit | 280ms | `cubic-bezier(0.32,0.72,0,1)` |

**Hard rule:** Never use `ease-in` on any entering element. It frontloads the slowest part of the animation exactly when the user is looking. Always `ease-out` or spring for entrances.
