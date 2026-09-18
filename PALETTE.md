# Infralytix Design Palette & Accessibility Audit

## 1. Palette Tokens

| Token | CSS Variable | Hex | Semantic Role |
| :--- | :--- | :--- | :--- |
| **Base Background** | `--color-bg-base` | `#242547` | Deep dark foundation; root viewport, container canvas |
| **Elevated Background** | `--color-bg-elevated` | `#36136E` | Glass card elevation, panel surfaces, ambient glows |
| **Primary Accent** | `--color-accent-primary` | `#882ECA` | Active navigation, focus rings, interactive highlights, scan beams |
| **Muted Text / Accent** | `--color-text-muted` | `#B495A4` | Subtitles, axis labels, metadata chips, non-text decorative chrome |
| **Accessible Muted Text** | `--color-text-muted-accessible` | `#C7ADB9` | Lightened high-contrast variant for micro-typography (≤ 11px) and WCAG AAA compliance |
| **Success State** | `--color-success` | `#61D29A` | Lowest-cost badge, completed stages, positive indicators |

---

## 2. WCAG Contrast Audit

Evaluated against standard WCAG 2.1 relative luminance formulations:

$$L = 0.2126 \times R + 0.7152 \times G + 0.0722 \times B$$

$$\text{Contrast Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05}$$

### Luminance Values
- `--color-bg-base` (`#242547`): **0.0215**
- `--color-bg-elevated` (`#36136E`): **0.0238**
- `--color-text-muted` (`#B495A4`): **0.3388**
- `--color-text-muted-accessible` (`#C7ADB9`): **0.4553**

### Contrast Ratios & Compliance

| Foreground Token | Background Token | Ratio | WCAG AA Normal Text (≥ 4.5:1) | WCAG AAA Normal Text (≥ 7:1) |
| :--- | :--- | :--- | :--- | :--- |
| `--color-text-muted` (`#B495A4`) | `--color-bg-base` (`#242547`) | **5.44 : 1** | **PASS** | Large text only |
| `--color-text-muted` (`#B495A4`) | `--color-bg-elevated` (`#36136E`) | **5.27 : 1** | **PASS** | Large text only |
| `--color-text-muted-accessible` (`#C7ADB9`) | `--color-bg-base` (`#242547`) | **7.06 : 1** | **PASS** | **PASS** |
| `--color-text-muted-accessible` (`#C7ADB9`) | `--color-bg-elevated` (`#36136E`) | **6.85 : 1** | **PASS** | Near AAA (passes large) |

### Audit Conclusion & Guidance
- `--color-text-muted` (`#B495A4`) strictly satisfies WCAG AA guidelines for normal body text (5.44:1 vs base, 5.27:1 vs elevated).
- `--color-text-muted-accessible` (`#C7ADB9`) is provided as an enhanced-contrast variant for dense metadata, small captions (10px–11px), or high-contrast preference, achieving up to 7.06:1.
- `#B495A4` is retained for default body text, chart axis labels, and non-text decorative borders.

---

## 3. Provider Brand Preservation Rule

Per core system design principles, the following brand colors are strictly isolated from theme recoloring:
- **AWS**: `#FF9900` (AWS Orange)
- **Azure**: `#0089D6` / `#0078D4` (Azure Blue)
- **GCP**: `#4285F4` (Google Cloud Blue)
