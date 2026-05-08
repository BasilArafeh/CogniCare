import { formatTime, getGreeting, todayLabel } from '../../utils/time';

describe('formatTime', () => {
  test('converts afternoon time correctly', () => {
    expect(formatTime('14:05')).toBe('2:05 PM');
  });

  test('converts midnight correctly', () => {
    expect(formatTime('00:00')).toBe('12:00 AM');
  });

  test('converts noon correctly', () => {
    expect(formatTime('12:00')).toBe('12:00 PM');
  });

  test('converts morning time correctly', () => {
    expect(formatTime('08:30')).toBe('8:30 AM');
  });

  test('pads single-digit minutes', () => {
    expect(formatTime('09:05')).toBe('9:05 AM');
  });

  test('handles 23:59', () => {
    expect(formatTime('23:59')).toBe('11:59 PM');
  });

  test('returns empty string for empty input', () => {
    expect(formatTime('')).toBe('');
  });
});

describe('getGreeting', () => {
  const RealDate = Date;

  afterEach(() => {
    (globalThis as any).Date = RealDate;
  });

  function mockHour(hour: number) {
    (globalThis as any).Date = class extends RealDate {
      getHours() { return hour; }
    } as unknown as typeof Date;
  }

  test('returns Good morning before noon', () => {
    mockHour(9);
    expect(getGreeting()).toBe('Good morning');
  });

  test('returns Good afternoon between noon and 17:00', () => {
    mockHour(14);
    expect(getGreeting()).toBe('Good afternoon');
  });

  test('returns Good evening at 17:00 and later', () => {
    mockHour(19);
    expect(getGreeting()).toBe('Good evening');
  });

  test('returns Good morning at exactly midnight (hour 0)', () => {
    mockHour(0);
    expect(getGreeting()).toBe('Good morning');
  });

  test('returns Good afternoon at exactly noon (hour 12)', () => {
    mockHour(12);
    expect(getGreeting()).toBe('Good afternoon');
  });
});

describe('todayLabel', () => {
  test('returns a non-empty string', () => {
    expect(typeof todayLabel()).toBe('string');
    expect(todayLabel().length).toBeGreaterThan(0);
  });

  test('contains the current day name', () => {
    const dayName = new Date().toLocaleDateString('en-US', { weekday: 'long' });
    expect(todayLabel()).toContain(dayName);
  });
});
