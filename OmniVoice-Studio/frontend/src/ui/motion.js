// Motion constants — single source of truth for animation timing.
// Mirrors the CSS tokens in ui/tokens.css. Import in JS when passing to
// react-spring, Framer Motion, or element-style transitions.

export const DURATION = {
  instant: 80,
  fast:    120,
  base:    200,
  slow:    300,
  xslow:   500,
};

export const EASING = {
  out:     'cubic-bezier(0.4, 0, 0.2, 1)',
  inOut:   'cubic-bezier(0.4, 0, 0.6, 1)',
  spring:  'cubic-bezier(0.34, 1.56, 0.64, 1)',
  bounce:  'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
};

// Convenience: inline-style transition builder.
// usage: style={{ transition: tx('opacity', 'background') }}
export function tx(...props) {
  return props.map(p => `${p} ${DURATION.base}ms ${EASING.out}`).join(', ');
}
