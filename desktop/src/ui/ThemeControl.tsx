import { Radio } from "antd";
import type { ReactNode } from "react";
import type { ThemePref } from "./theme";

// Sun / moon / monitor glyphs ported from the styleguide's Theme Selector
// (design/styleguide/src/phase7/Phase7Settings.tsx). 24-grid outline, tokens
// via currentColor.
const GLYPHS: Record<ThemePref, ReactNode> = {
  light: (
    <>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v2.5M12 19.5V22M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8l1.8-1.8M18 6l1.8-1.8" />
    </>
  ),
  dark: <path d="M20 14.5A8.5 8.5 0 1110 4a6.8 6.8 0 0010 10.5z" />,
  system: (
    <>
      <rect x="3" y="4" width="18" height="13" rx="1.5" />
      <path d="M8 21h8M12 17v4" />
    </>
  ),
};

const OPTIONS: { value: ThemePref; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

function Glyph({ name }: { name: ThemePref }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ marginInlineEnd: 6, verticalAlign: "-0.125em" }}
    >
      {GLYPHS[name]}
    </svg>
  );
}

export function ThemeControl({
  value,
  onChange,
}: {
  value: ThemePref;
  onChange: (pref: ThemePref) => void;
}) {
  return (
    <Radio.Group
      aria-label="Theme"
      optionType="button"
      value={value}
      onChange={(e) => onChange(e.target.value as ThemePref)}
    >
      {OPTIONS.map((o) => (
        <Radio.Button key={o.value} value={o.value}>
          <Glyph name={o.value} />
          {o.label}
        </Radio.Button>
      ))}
    </Radio.Group>
  );
}
