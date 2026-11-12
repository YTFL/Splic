---
name: emil-design-eng
description: Emil Kowalski-grade design engineering for Splic. Enforces purposeful animation, correct easing physics, interaction feedback, and the "unseen details compound" philosophy for every Timeline Studio UI surface.
category: ui-design
risk: safe
source: sickn33/agentic-awesome-skills (emilkowalski/skills, MIT)
date_added: "2026-11-12"
author: Emil Kowalski
tags: [design-engineering, motion, interaction, polish, timeline-studio]
tools: [antigravity, claude-code, cursor, gemini-cli]
---

# Design Engineering — Emil Kowalski's Craft Philosophy for Splic

> "All those unseen details combine to produce something that's just stunning, like a thousand barely audible voices all singing in tune." — Paul Graham

Applied to every interactive surface in Timeline Studio. Beauty is leverage. The editor that *feels* right gets used more.

---

## 1. The Animation Decision Gate (Answer in Order)

Before writing **any** animation code:

### Q1: How often will users see this?

| Frequency | Decision |
| :--- | :--- |
| 100+ times/day — scrubbing timeline, cutting clips, keyboard shortcuts | **No animation. Ever.** |
| Tens of times/day — track hover, button focus, drag handle | Remove or use `< 100ms` micro-feedback only |
| Occasional — opening panels, running auto-cut, export modal | Standard spring animation |
| Rare / first-time — onboarding, first auto-cut success | Full delight animation allowed |

**Rule:** Raycast has no open/close animation. That is the correct answer for anything invoked with a keyboard shortcut in Timeline Studio.

### Q2: What is the purpose?

Valid purposes:
- **Spatial consistency** — the status pill enters/exits from the same edge every time
- **State feedback** — the auto-cut button presses down physically confirming the action
- **Explanation** — the first-run animation shows what tracks are being populated
- **Preventing jarring jumps** — a track appearing without transition looks broken

If the answer is "it looks cool" and users see it often → **don't animate.**

---

## 2. The Easing Canon

**Never use browser default easings.** They are too weak:

```css
/* Use these exact curves — always */
--ease-out-expo:   cubic-bezier(0.16, 1, 0.3, 1);     /* Entrances */
--ease-in-out-expo: cubic-bezier(0.87, 0, 0.13, 1);   /* On-screen movement */
--ease-ios-drawer: cubic-bezier(0.32, 0.72, 0, 1);    /* Panels, sheets, pills */
--ease-spring-snappy: spring(stiffness: 400, damping: 28); /* Press feedback */
```

**Never use `ease-in` on any entering element.** It starts slow at the exact moment the user is watching hardest. A `300ms ease-in` feels slower than `300ms ease-out` even though the duration is identical.

---

## 3. Duration Reference for Timeline Studio

| Interaction | Duration | Curve |
| :--- | :--- | :--- |
| Button/chip press response | 100–140ms | `ease-out-expo` |
| Tooltip / small popover | 150ms | `ease-out-expo` |
| Status pill width morph | spring | `stiffness:400, damping:28` |
| Panel / modal entrance | 280–340ms | `ease-ios-drawer` |
| Auto-cut progress step transition | 220ms | `ease-out-expo` |
| Track item stagger (batch insert) | 60ms per item | `ease-out-expo` |
| Toast notification | 240ms enter / 180ms exit | `ease-ios-drawer` |

**UI animations must stay under 300ms.** A 180ms panel feels more responsive than 400ms — even if the user knows nothing changed.

---

## 4. Interaction Feedback (Every Control Must Respond)

Every clickable element needs a physical response. No exceptions:

```tsx
// The minimum viable press response — 3 lines, transforms everything
<motion.button
  whileTap={{ scale: 0.96 }}
  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
>

// For drag handles on timeline tracks — magnetic resistance feel
<motion.div
  whileHover={{ scaleY: 1.4 }}
  transition={{ type: 'spring', stiffness: 600, damping: 35 }}
  className="w-1 h-6 rounded-full bg-white/20 cursor-col-resize"
>
```

**States every interactive element must have:**
- `default` — resting, subdued
- `hover` — slight lift or glow intensification
- `active/pressed` — `scale(0.96–0.98)` physical depression
- `disabled` — `opacity-40 cursor-not-allowed` — never just grayed text

---

## 5. The UI Review Table Format

When reviewing existing Timeline Studio UI, always output a markdown table:

| Location | Before | After | Why |
| :--- | :--- | :--- | :--- |
| Auto-Cut button | `transition: all 300ms` | `transition: transform 140ms cubic-bezier(0.16,1,0.3,1)` | Specify properties; `all` causes layout recalculations |
| Status text change | Instant swap | `AnimatePresence` with `y: 4 → 0, opacity: 0 → 1` | Text appearing from nothing looks broken |
| Track drag handle | No hover state | `scaleY: 1.4` spring on hover | Users need affordance that it's draggable |
| Modal close | `opacity: 0` | `scale: 0.96, opacity: 0` | Nothing in real world disappears — it retreats |

---

## 6. The Perceived Performance Tricks

Speed perception matters as much as actual speed for a video editor:

- **Status pill pulsing dot**: A breathing amber dot makes the 3-second Sarvam API call *feel* active, not frozen.
- **Optimistic track insertion**: Insert skeleton caption tracks immediately on button click, fill real data as it arrives — never show a blank timeline waiting.
- **Staggered batch rendering**: When 30 caption blocks load, stagger them `60ms` apart so the timeline *feels* like it's being assembled deliberately, not dumped.
- **Instant hover response**: Hover states at `< 100ms` make the entire tool feel snappier, even if export takes 10 seconds.
