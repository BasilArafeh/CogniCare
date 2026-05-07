export const colors = {
  primary: '#7C5CBF',
  primaryMuted: '#B8A0E0',
  primaryLight: '#EDE8F8',
  primaryDark: '#5A3F9A',
  secondary: '#7BAE8E',
  secondaryLight: '#E6F2EC',
  secondaryDark: '#4D8A65',
  background: '#F5F3FF',
  textPrimary: '#2D2640',
  textSecondary: '#6B5F82',
  textMuted: '#B0A8C8',
  success: '#2D7A4F',
  warning: '#B45309',
  error: '#B91C1C',
  white: '#FFFFFF',
};

export const fonts = {
  regular: 'NunitoSans_400Regular',
  semiBold: 'NunitoSans_600SemiBold',
  bold: 'NunitoSans_700Bold',
  extraBold: 'NunitoSans_800ExtraBold',
};

/**
 * Convert a hex color + 0–1 alpha to an rgba() string.
 * Works with 6-digit (#RRGGBB) or 3-digit (#RGB) hex values.
 */
export function withAlpha(hex: string, alpha: number): string {
  const clean = hex.replace('#', '');
  let r: number, g: number, b: number;

  if (clean.length === 3) {
    r = parseInt(clean[0] + clean[0], 16);
    g = parseInt(clean[1] + clean[1], 16);
    b = parseInt(clean[2] + clean[2], 16);
  } else {
    r = parseInt(clean.substring(0, 2), 16);
    g = parseInt(clean.substring(2, 4), 16);
    b = parseInt(clean.substring(4, 6), 16);
  }

  const a = Math.min(1, Math.max(0, alpha));
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}
