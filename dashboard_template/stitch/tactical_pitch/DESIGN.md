# Design System Document: Tactical Precision & Cinematic Analytics

## 1. Overview & Creative North Star: "The Tactical Blueprint"
The goal of this design system is to move beyond the "spreadsheet" feel of traditional sports data and into the realm of elite, high-performance coaching tools. Our Creative North Star is **The Tactical Blueprint**. 

This system rejects the "template" look of standard dashboards by prioritizing atmospheric depth over rigid lines. We treat the UI as a high-contrast, head-up display (HUD) found in professional broadcast suites. By utilizing intentional asymmetry within a bento-box framework, we create a sense of focused energy. We break the grid's monotony by layering semi-transparent glass modules over deep, charcoal voids, ensuring that the data doesn't just sit on the screen—it commands it.

---

## 2. Colors: Depth and Luminance
We define space through tonal shifts rather than lines. The palette is anchored in deep charcoals to reduce eye strain during long-form analysis, while the vibrant accents provide "glanceable" hierarchy.

### The "No-Line" Rule
**Prohibited:** 1px solid borders for sectioning or card containment. 
**The Standard:** Boundaries are defined strictly by background color shifts. For example, a `surface_container_low` section sits directly on a `surface` background. The change in hex value is the only border required.

### Surface Hierarchy & Nesting
Treat the UI as physical layers of smoked glass. 
- **Base Layer:** `surface` (#0e0e0e)
- **Primary Layout Sections:** `surface_container_low` (#131313)
- **Standard Bento Cards:** `surface_container` (#1a1a1a)
- **Active/Hovered Modules:** `surface_container_highest` (#262626)

### The "Glass & Gradient" Rule
Floating tactical overlays or high-level player stats must utilize **Glassmorphism**. Apply a `surface_variant` at 60% opacity with a `20px` backdrop-blur. 
- **Signature Texture:** Primary CTAs should not be flat. Use a linear gradient from `primary` (#6dfe9c) to `primary_container` (#19be64) at a 135° angle to give action items a "lit" appearance.

---

## 3. Typography: Editorial Authority
We use a dual-font approach to balance technical precision with high-end editorial flair.

*   **Display & Headlines (Manrope):** Used for "Big Data" moments—match scores, player names, and top-level KPIs. The wider apertures of Manrope convey a modern, authoritative tone.
*   **Interface & Data (Inter):** Used for technical stats, labels, and granular table data. Inter’s tall x-height ensures readability at small scales (`label-sm`).

**Hierarchy Strategy:**
- **The "Power Number":** Use `display-lg` for primary metrics (e.g., xG or Possession %) to create a visual anchor.
- **Contextual Labels:** Use `label-md` in `on_surface_variant` (#adaaaa) for secondary metadata to keep the interface from feeling cluttered.

---

## 4. Elevation & Depth: Tonal Layering
In this system, elevation is a measurement of light, not shadow.

*   **The Layering Principle:** Stacking tiers creates "soft lift." A `surface_container_lowest` (#000000) card placed on a `surface_container` (#1a1a1a) section creates a recessed, "etched" look, perfect for data input fields.
*   **Ambient Shadows:** For floating modals, use a shadow with a `40px` blur at 8% opacity, using the `on_surface` color as the tint. This mimics the soft glow of a screen in a dark room.
*   **The "Ghost Border" Fallback:** If accessibility requires a container edge, use a **Ghost Border**: `outline_variant` (#484847) at 15% opacity. Never use 100% opaque outlines.
*   **Refraction:** Glass elements should have a top-left `1px` highlight using `outline` at 10% opacity to simulate light catching the edge of a glass pane.

---

## 5. Components

### Buttons
- **Primary:** Gradient fill (`primary` to `primary_container`), `on_primary` text, `round-md` (0.375rem).
- **Tertiary:** No background. `primary` text with an underline that only appears on hover. Use for "View All" or "Deep Dive" actions.

### Data Bento Cards
- **Construction:** Use `surface_container` with `xl` (0.75rem) rounded corners. 
- **Content:** Forbid divider lines. Separate "Header" from "Data" using a `3` (0.6rem) spacing gap and a change in typography scale from `title-sm` to `display-sm`.

### Performance Chips
- **Status:** Use `primary` for success, `tertiary` (#ffb148) for warnings/cautionary stats, and `error` (#ff716c) for critical failures.
- **Style:** Semi-transparent background (10% opacity of the color) with high-contrast text.

### Pitch Visualization (Custom Component)
- **Background:** `surface_container_lowest`.
- **Markings:** `outline_variant` at 20% opacity.
- **Players:** Use `secondary` (#7799ff) for the home team and `tertiary` (#ffb148) for the away team to ensure color-blind friendly distinction against the green pitch accents.

### Inputs & Search
- **Style:** `surface_container_lowest` background. No border. On focus, apply a `2px` glow using `primary_dim` (#5def8f) at 30% opacity.

---

## 6. Do’s and Don'ts

### Do:
- **Use "Breathing Room":** Use the `10` (2.25rem) spacing token between bento modules to let the charcoal background act as a palette cleanser.
- **Vary Column Widths:** In the bento grid, use asymmetrical widths (e.g., a 2/3 width card next to a 1/3 width card) to create a sophisticated, editorial rhythm.
- **Subtle Motion:** Animate data loading with a "fade and slide" (200ms) to reinforce the high-performance feel.

### Don't:
- **No Pure White:** Never use #FFFFFF for large blocks of text. Use `on_surface` or `on_surface_variant` to prevent "halogen-light" eye fatigue.
- **No Hard Dividers:** Never use a horizontal rule `<hr>` to separate list items. Use a `1.5` (0.3rem) spacing increment or a subtle background shift instead.
- **No Default Shadows:** Avoid the "dropped-from-the-sky" black shadow. Elevation is always tonal or glass-based.