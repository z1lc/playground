import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const coreMatch = html.match(/<script id="calculator-core">([\s\S]*?)<\/script>/);
if (!coreMatch) throw new Error('Inline calculator core was not found');
const sandbox = { Intl, RangeError };
vm.runInNewContext(coreMatch[1], sandbox);

const {
  DEFAULT_ASSUMPTIONS,
  MARGIN_RATE_TIERS,
  calculateBreakEven,
  formatCompactCurrency,
  formatCurrency,
  formatDuration,
  getMarginInterestRate,
} = sandbox.BuyVsRent;

describe('slider configuration', () => {
  it('uses $25k house-value steps and $100 rent steps', () => {
    expect(html).toMatch(/id="house-value"[^>]*step="25000"/);
    expect(html).toMatch(/id="monthly-rent"[^>]*step="100"/);
  });
});

describe('calculateBreakEven', () => {
  it('compounds annual home and rent growth to the stated rates after 12 months', () => {
    const result = calculateBreakEven(700_000, 3_000);

    expect(result.timeline[12].homeValue).toBeCloseTo(700_000 * 1.037, 6);
    expect(result.timeline[12].monthlyRent).toBeCloseTo(3_000 * 1.032, 6);
  });

  it('returns the planned default break-even fixture', () => {
    const result = calculateBreakEven(700_000, 3_000);

    expect(result.breakEvenMonth).toBe(29);
    expect(result.advantageAtBreakEven).toBeCloseTo(1_695.83, 1);
    expect(result.timeline[28].buyerAdvantage).toBeLessThan(0);
    expect(result.timeline[29].buyerAdvantage).toBeGreaterThanOrEqual(0);
    expect(result.chartYears).toBe(10);
    expect(result.timeline).toHaveLength(121);
  });

  it('starts behind by both sides of the transaction', () => {
    const result = calculateBreakEven(700_000, 3_000);

    const expected = -700_000
      * (DEFAULT_ASSUMPTIONS.buyerClosingPct + DEFAULT_ASSUMPTIONS.sellerClosingPct);
    expect(result.initialBuyerAdvantage).toBeCloseTo(expected, 6);
  });

  it('uses cash up to $1M and an interest-only margin loan above it', () => {
    const result = calculateBreakEven(1_500_000, 3_000);

    expect(result.marginLoanBalance).toBe(500_000);
    expect(result.marginInterestRate).toBe(0.045);
    expect(result.marginInterestMonthly).toBe(1_875);
    expect(result.buyerCashOutlay).toBe(1_030_000);
    expect(result.timeline[0].ownerMonthlyCost).toBe(4_875);
    expect(result.timeline[0].netSaleProceeds).toBe(910_000);
    expect(result.initialBuyerAdvantage).toBe(-120_000);
  });

  it('does not use a margin loan at the $1M cash limit', () => {
    const result = calculateBreakEven(1_000_000, 3_000);

    expect(result.marginLoanBalance).toBe(0);
    expect(result.marginInterestRate).toBe(0);
    expect(result.marginInterestMonthly).toBe(0);
    expect(result.buyerCashOutlay).toBe(1_020_000);
  });

  it('returns null when buying does not catch up within 30 years', () => {
    const result = calculateBreakEven(1_500_000, 1_000);

    expect(result.breakEvenMonth).toBeNull();
    expect(result.advantageAtBreakEven).toBeNull();
    expect(result.chartYears).toBe(10);
    expect(result.timeline).toHaveLength(121);
  });

  it('keeps the graph at 10 years when break-even occurs later', () => {
    const result = calculateBreakEven(500_000, 1_000);

    expect(result.breakEvenMonth).toBe(153);
    expect(result.chartYears).toBe(10);
    expect(result.timeline.at(-1).month).toBe(120);
  });

  it('higher rent does not delay break-even', () => {
    for (const houseValue of [200_000, 500_000, 700_000, 1_000_000, 1_500_000]) {
      let previous = Infinity;
      for (const rent of [1_000, 2_000, 3_000, 5_000, 8_000]) {
        const month = calculateBreakEven(houseValue, rent).breakEvenMonth ?? Infinity;
        expect(month).toBeLessThanOrEqual(previous);
        previous = month;
      }
    }
  });

  it('higher house values do not accelerate break-even at a fixed rent', () => {
    for (const rent of [1_000, 2_500, 4_000, 8_000]) {
      let previous = -Infinity;
      for (const houseValue of [200_000, 500_000, 700_000, 1_000_000, 1_500_000]) {
        const month = calculateBreakEven(houseValue, rent).breakEvenMonth ?? Infinity;
        expect(month).toBeGreaterThanOrEqual(previous);
        previous = month;
      }
    }
  });

  it('can break even immediately when all ownership frictions are removed', () => {
    const result = calculateBreakEven(500_000, 2_000, {
      buyerClosingPct: 0,
      sellerClosingPct: 0,
      propertyTaxPct: 0,
      insurancePct: 0,
      maintenancePct: 0,
      rentersInsuranceMonthly: 0,
    });

    expect(result.breakEvenMonth).toBe(0);
    expect(result.chartYears).toBe(10);
    expect(result.timeline).toHaveLength(121);
  });

  it('rejects invalid inputs', () => {
    expect(() => calculateBreakEven(0, 3_000)).toThrow(RangeError);
    expect(() => calculateBreakEven(700_000, -1)).toThrow(RangeError);
    expect(() => calculateBreakEven(700_000, 3_000, { horizonMonths: 1.5 })).toThrow(RangeError);
    expect(() => calculateBreakEven(700_000, 3_000, { cashPurchaseLimit: -1 })).toThrow(RangeError);
  });
});

describe('margin interest tiers', () => {
  it.each([
    [0, 0],
    [50_000, 0.05],
    [50_001, 0.048],
    [100_000, 0.048],
    [100_001, 0.045],
    [1_000_000, 0.045],
    [1_000_001, 0.0425],
    [10_000_000, 0.0425],
    [10_000_001, 0.042],
    [50_000_000, 0.042],
    [50_000_001, 0.0395],
  ])('uses the correct whole-balance rate for a $%i loan', (balance, expectedRate) => {
    expect(getMarginInterestRate(balance)).toBe(expectedRate);
  });

  it('exposes all six documented tiers', () => {
    expect(MARGIN_RATE_TIERS).toHaveLength(6);
  });
});

describe('formatters', () => {
  it('formats money and durations for the UI', () => {
    expect(formatCurrency(700_000)).toBe('$700,000');
    expect(formatCompactCurrency(-1_250_000)).toBe('-$1.3M');
    expect(formatDuration(0)).toBe('immediately');
    expect(formatDuration(29)).toBe('2 years, 5 months');
    expect(formatDuration(null)).toBeNull();
  });
});
