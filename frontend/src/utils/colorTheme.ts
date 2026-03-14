export type ColorThemeName = 'emerald' | 'blue' | 'violet' | 'orange' | 'rose' | 'custom';

const PALETTES: Record<Exclude<ColorThemeName, 'custom'>, Record<number, string>> = {
  emerald: {
    50:  '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981',
    600: '#059669',
    700: '#047857',
    800: '#065f46',
    900: '#064e3b',
    950: '#022c22',
  },
  blue: {
    50:  '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
    950: '#172554',
  },
  violet: {
    50:  '#f5f3ff',
    100: '#ede9fe',
    200: '#ddd6fe',
    300: '#c4b5fd',
    400: '#a78bfa',
    500: '#8b5cf6',
    600: '#7c3aed',
    700: '#6d28d9',
    800: '#5b21b6',
    900: '#4c1d95',
    950: '#2e1065',
  },
  orange: {
    50:  '#fff7ed',
    100: '#ffedd5',
    200: '#fed7aa',
    300: '#fdba74',
    400: '#fb923c',
    500: '#f97316',
    600: '#ea580c',
    700: '#c2410c',
    800: '#9a3412',
    900: '#7c2d12',
    950: '#431407',
  },
  rose: {
    50:  '#fff1f2',
    100: '#ffe4e6',
    200: '#fecdd3',
    300: '#fda4af',
    400: '#fb7185',
    500: '#f43f5e',
    600: '#e11d48',
    700: '#be123c',
    800: '#9f1239',
    900: '#881337',
    950: '#4c0519',
  },
};

const LS_KEY = 'colorTheme';

function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0, s = 0;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / d + 2) / 6;
    else h = ((r - g) / d + 4) / 6;
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
}

function hslToHex(h: number, s: number, l: number): string {
  const sl = s / 100, ll = l / 100;
  const a = sl * Math.min(ll, 1 - ll);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = ll - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

export function applyCustomColor(hex: string): void {
  const [h, s] = hexToHsl(hex);
  const shadeToLightness: [number, number][] = [
    [50, 97], [100, 94], [200, 87], [300, 75], [400, 62],
    [500, 50], [600, 42], [700, 35], [800, 27], [900, 20], [950, 12],
  ];
  const root = document.documentElement;
  for (const [shade, lightness] of shadeToLightness) {
    root.style.setProperty(`--p-primary-${shade}`, hslToHex(h, Math.min(s, 85), lightness));
  }
  localStorage.setItem(LS_KEY, 'custom');
  localStorage.setItem('customColor', hex);
}

export function applyColorTheme(name: Exclude<ColorThemeName, 'custom'>): void {
  const palette = PALETTES[name];
  const root = document.documentElement;
  for (const [shade, value] of Object.entries(palette)) {
    root.style.setProperty(`--p-primary-${shade}`, value);
  }
  localStorage.setItem(LS_KEY, name);
}

export function loadColorTheme(): void {
  const saved = localStorage.getItem(LS_KEY) as ColorThemeName | null;
  if (saved === 'custom') {
    const hex = localStorage.getItem('customColor');
    if (hex) applyCustomColor(hex);
    return;
  }
  if (saved && saved in PALETTES) {
    applyColorTheme(saved as Exclude<ColorThemeName, 'custom'>);
  }
}

export function getSavedTheme(): ColorThemeName {
  const saved = localStorage.getItem(LS_KEY) as ColorThemeName | null;
  if (saved === 'custom') return 'custom';
  return saved && saved in PALETTES ? saved : 'emerald';
}
