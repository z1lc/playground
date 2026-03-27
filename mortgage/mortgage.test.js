import { describe, it, expect } from 'vitest';
import { computeMortgage, computeStockComparison, resolveYearlyRates, formatCurrency, formatAxisCurrency, formatPercent, PROPERTY_TAX_RATE, INSURANCE_RATE, PMI_RATE } from './mortgage.js';

// Helper: independently compute monthly payment using the standard amortization formula
function expectedMonthlyPayment(principal, annualRate) {
  const r = annualRate / 100 / 12;
  const n = 360;
  if (r === 0) return principal / n;
  return principal * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
}

// ─── 1. Monthly Payment Formula ────────────────────────────────────────────────

describe('monthly payment calculation', () => {
  const cases = [
    { name: 'baseline $800k/20%/6.5%', price: 800000, down: 20, rate: 6.5, loan: 640000 },
    { name: 'low rate $500k/20%/3.0%', price: 500000, down: 20, rate: 3.0, loan: 400000 },
    { name: 'high rate $1M/10%/9.0%', price: 1000000, down: 10, rate: 9.0, loan: 900000 },
    { name: 'zero down $600k/0%/5.0%', price: 600000, down: 0, rate: 5.0, loan: 600000 },
    { name: 'max down $1M/50%/7.0%', price: 1000000, down: 50, rate: 7.0, loan: 500000 },
    { name: 'zero rate $800k/20%/0%', price: 800000, down: 20, rate: 0, loan: 640000 },
  ];

  for (const c of cases) {
    it(`${c.name}: matches independent formula`, () => {
      const result = computeMortgage(c.price, c.down, c.rate, 3, 10);
      const expected = expectedMonthlyPayment(c.loan, c.rate);
      expect(result.monthlyPayment).toBeCloseTo(expected, 2);
    });

    it(`${c.name}: loan amount is correct`, () => {
      const result = computeMortgage(c.price, c.down, c.rate, 3, 10);
      expect(result.loanAmount).toBe(c.loan);
    });

    it(`${c.name}: down payment is correct`, () => {
      const result = computeMortgage(c.price, c.down, c.rate, 3, 10);
      expect(result.downPayment).toBe(c.price * c.down / 100);
    });
  }

  // Cross-validation against well-known textbook values
  it('$100k at 6% for 30yr = $599.55/mo (textbook reference)', () => {
    // Use a wrapper: price $100k, 0% down, 6% rate
    const result = computeMortgage(100000, 0, 6.0, 0, 30);
    expect(result.monthlyPayment).toBeCloseTo(599.55, 1);
  });

  it('$200k at 4% for 30yr = $954.83/mo (textbook reference)', () => {
    const result = computeMortgage(200000, 0, 4.0, 0, 30);
    expect(result.monthlyPayment).toBeCloseTo(954.83, 1);
  });

  it('$300k at 7.5% for 30yr = $2,097.64/mo (textbook reference)', () => {
    const result = computeMortgage(300000, 0, 7.5, 0, 30);
    expect(result.monthlyPayment).toBeCloseTo(2097.64, 1);
  });
});

// ─── 2. Amortization Schedule Consistency ──────────────────────────────────────

describe('amortization schedule consistency', () => {
  const scenarios = [
    { price: 800000, down: 20, rate: 6.5, appr: 3, years: 10 },
    { price: 500000, down: 0, rate: 3.0, appr: 0, years: 30 },
    { price: 1000000, down: 50, rate: 9.0, appr: 10, years: 5 },
    { price: 600000, down: 10, rate: 5.0, appr: 5, years: 1 },
    { price: 800000, down: 20, rate: 0, appr: 3, years: 15 },
  ];

  for (const s of scenarios) {
    const label = `${s.price / 1000}k/${s.down}%/${s.rate}%/${s.years}yr`;

    it(`${label}: schedule length matches holding period`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      expect(result.schedule.length).toBe(s.years);
    });

    it(`${label}: year-to-year balance continuity`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      for (let i = 1; i < result.schedule.length; i++) {
        expect(result.schedule[i].beginningBalance).toBeCloseTo(result.schedule[i - 1].endingBalance, 2);
      }
    });

    it(`${label}: first year begins with full loan amount`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      expect(result.schedule[0].beginningBalance).toBeCloseTo(result.loanAmount, 2);
    });

    it(`${label}: principal + interest = payment each year`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      for (const yr of result.schedule) {
        expect(yr.principal + yr.interest).toBeCloseTo(yr.payment, 1);
      }
    });

    it(`${label}: endingBalance = beginningBalance - principal each year`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      for (const yr of result.schedule) {
        // endingBalance is clamped to 0, so check with clamp
        const expected = Math.max(0, yr.beginningBalance - yr.principal);
        expect(yr.endingBalance).toBeCloseTo(expected, 1);
      }
    });

    it(`${label}: all ending balances are non-negative`, () => {
      const result = computeMortgage(s.price, s.down, s.rate, s.appr, s.years);
      for (const yr of result.schedule) {
        expect(yr.endingBalance).toBeGreaterThanOrEqual(0);
      }
    });
  }

  it('30-year holding fully amortizes the loan (balance reaches ~$0)', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 30);
    const finalBalance = result.schedule[29].endingBalance;
    expect(finalBalance).toBeCloseTo(0, 0);
  });

  it('30-year holding at 0% rate fully amortizes', () => {
    const result = computeMortgage(800000, 20, 0, 0, 30);
    const finalBalance = result.schedule[29].endingBalance;
    expect(finalBalance).toBeCloseTo(0, 0);
  });
});

// ─── 3. Home Value / Appreciation ──────────────────────────────────────────────

describe('home value appreciation', () => {
  it('0% appreciation: home value stays at purchase price every year', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 10);
    for (const yr of result.schedule) {
      expect(yr.homeValue).toBeCloseTo(800000, 0);
    }
  });

  it('3% appreciation over 10 years: $800k * 1.03^10', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    const expected = 800000 * Math.pow(1.03, 10); // $1,074,913.56
    expect(result.finalHomeValue).toBeCloseTo(expected, 2);
  });

  it('10% appreciation over 5 years: $500k * 1.10^5', () => {
    const result = computeMortgage(500000, 20, 6.5, 10, 5);
    const expected = 500000 * Math.pow(1.10, 5); // $805,255.00
    expect(result.finalHomeValue).toBeCloseTo(expected, 2);
  });

  it('appreciation compounds correctly year-by-year', () => {
    const result = computeMortgage(1000000, 20, 5, 5, 20);
    for (const yr of result.schedule) {
      const expected = 1000000 * Math.pow(1.05, yr.year);
      expect(yr.homeValue).toBeCloseTo(expected, 2);
    }
  });
});

// ─── 4. Equity Calculation ─────────────────────────────────────────────────────

describe('equity calculation', () => {
  it('equity = homeValue - endingBalance for every year', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 30);
    for (const yr of result.schedule) {
      expect(yr.equity).toBeCloseTo(yr.homeValue - yr.endingBalance, 2);
    }
  });

  it('equity with 0% appreciation = principal paid + down payment', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 10);
    const totalPrincipalPaid = result.schedule.reduce((s, yr) => s + yr.principal, 0);
    // equity = homeValue(=800k) - remainingBalance = 800k - (loanAmount - totalPrincipal)
    // = 800k - loanAmount + totalPrincipal = downPayment + totalPrincipal
    expect(result.equity).toBeCloseTo(result.downPayment + totalPrincipalPaid, 1);
  });
});

// ─── 5. Summary Totals ────────────────────────────────────────────────────────

describe('summary totals', () => {
  const result = computeMortgage(800000, 20, 6.5, 3, 10);

  it('totalPaid = monthlyPayment * 12 * holdingYears', () => {
    expect(result.totalPaid).toBeCloseTo(result.monthlyPayment * 12 * 10, 2);
  });

  it('totalInterest = sum of schedule interest', () => {
    const sumInterest = result.schedule.reduce((s, yr) => s + yr.interest, 0);
    expect(result.totalInterest).toBeCloseTo(sumInterest, 2);
  });

  it('totalInterest = totalPaid - sum of principal', () => {
    const sumPrincipal = result.schedule.reduce((s, yr) => s + yr.principal, 0);
    expect(result.totalInterest).toBeCloseTo(result.totalPaid - sumPrincipal, 1);
  });

  it('remainingBalance = last schedule entry endingBalance', () => {
    expect(result.remainingBalance).toBe(result.schedule[9].endingBalance);
  });

  it('finalHomeValue = last schedule entry homeValue', () => {
    expect(result.finalHomeValue).toBe(result.schedule[9].homeValue);
  });

  it('equity = finalHomeValue - remainingBalance', () => {
    expect(result.equity).toBeCloseTo(result.finalHomeValue - result.remainingBalance, 2);
  });

  it('netProfit = equity - (downPayment + totalPaid)', () => {
    expect(result.netProfit).toBeCloseTo(
      result.equity - (result.downPayment + result.totalPaid + result.totalPropertyTax + result.totalInsurance), 2);
  });
});

// ─── 6. ROI Calculation ───────────────────────────────────────────────────────

describe('ROI calculation', () => {
  it('annualized ROI formula: (equity / totalCash)^(1/years) - 1', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    const totalCash = result.downPayment + result.totalPaid + result.totalPropertyTax + result.totalInsurance;
    const expected = Math.pow(result.equity / totalCash, 1 / 10) - 1;
    expect(result.annualizedROI).toBeCloseTo(expected, 6);
  });

  it('negative ROI when appreciation is low and rate is high', () => {
    const result = computeMortgage(800000, 20, 9.0, 0, 5);
    expect(result.annualizedROI).toBeLessThan(0);
    expect(result.netProfit).toBeLessThan(0);
  });

  it('positive ROI when appreciation is high and rate is low', () => {
    const result = computeMortgage(800000, 20, 3.0, 8, 10);
    expect(result.annualizedROI).toBeGreaterThan(0);
    expect(result.netProfit).toBeGreaterThan(0);
  });

  it('ROI with 0% rate and high appreciation is strongly positive', () => {
    const result = computeMortgage(800000, 20, 0, 10, 10);
    expect(result.annualizedROI).toBeGreaterThan(0.05);
  });
});

// ─── 7. Edge Cases ────────────────────────────────────────────────────────────

describe('edge cases', () => {
  it('0% interest rate: no interest accrued', () => {
    const result = computeMortgage(800000, 20, 0, 3, 10);
    expect(result.totalInterest).toBeCloseTo(0, 2);
    for (const yr of result.schedule) {
      expect(yr.interest).toBeCloseTo(0, 2);
    }
  });

  it('0% interest rate: monthly payment = loan / 360', () => {
    const result = computeMortgage(800000, 20, 0, 0, 10);
    expect(result.monthlyPayment).toBeCloseTo(640000 / 360, 2);
  });

  it('holding period = 1 year: schedule has exactly 1 entry', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 1);
    expect(result.schedule.length).toBe(1);
  });

  it('holding period = 30 years: balance reaches $0', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 30);
    expect(result.remainingBalance).toBeCloseTo(0, 0);
  });

  it('0% down: full house price is financed', () => {
    const result = computeMortgage(600000, 0, 5.0, 3, 10);
    expect(result.loanAmount).toBe(600000);
    expect(result.downPayment).toBe(0);
  });

  it('50% down: half the house price is financed', () => {
    const result = computeMortgage(1000000, 50, 7.0, 3, 10);
    expect(result.loanAmount).toBe(500000);
    expect(result.downPayment).toBe(500000);
  });

  it('0% appreciation: home value equals purchase price', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 10);
    expect(result.finalHomeValue).toBeCloseTo(800000, 0);
  });

  it('max appreciation (10%) + max holding (30 years): no overflow', () => {
    const result = computeMortgage(2000000, 0, 10, 10, 30);
    expect(Number.isFinite(result.finalHomeValue)).toBe(true);
    expect(Number.isFinite(result.equity)).toBe(true);
    expect(Number.isFinite(result.annualizedROI)).toBe(true);
    expect(result.finalHomeValue).toBeGreaterThan(2000000);
  });

  it('min inputs: $500k, 0% down, 2.5% rate, 0% appr, 1 year', () => {
    const result = computeMortgage(500000, 0, 2.5, 0, 1);
    expect(result.monthlyPayment).toBeGreaterThan(0);
    expect(result.schedule.length).toBe(1);
    expect(result.finalHomeValue).toBeCloseTo(500000, 0);
  });

  it('max inputs: $2M, 50% down, 10% rate, 10% appr, 30 years', () => {
    const result = computeMortgage(2000000, 50, 10, 10, 30);
    expect(result.monthlyPayment).toBeGreaterThan(0);
    expect(result.schedule.length).toBe(30);
    expect(result.remainingBalance).toBeCloseTo(0, 0);
  });
});

// ─── 8. Formatting Functions ──────────────────────────────────────────────────

describe('formatCurrency', () => {
  it('formats typical values with $ and commas', () => {
    expect(formatCurrency(4045)).toBe('$4,045');
    expect(formatCurrency(800000)).toBe('$800,000');
    expect(formatCurrency(0)).toBe('$0');
  });

  it('formats millions with M suffix', () => {
    expect(formatCurrency(1000000)).toBe('$1.00M');
    expect(formatCurrency(1500000)).toBe('$1.50M');
    expect(formatCurrency(2345678)).toBe('$2.35M');
  });

  it('formats negative values', () => {
    expect(formatCurrency(-50000)).toBe('$-50,000');
    expect(formatCurrency(-1500000)).toBe('-$1.50M');
  });
});

describe('formatAxisCurrency', () => {
  it('formats thousands with k suffix', () => {
    expect(formatAxisCurrency(500000)).toBe('$500k');
    expect(formatAxisCurrency(1000)).toBe('$1k');
  });

  it('formats millions with M suffix', () => {
    expect(formatAxisCurrency(1000000)).toBe('$1.0M');
    expect(formatAxisCurrency(2500000)).toBe('$2.5M');
  });

  it('formats small values without suffix', () => {
    expect(formatAxisCurrency(500)).toBe('$500');
    expect(formatAxisCurrency(0)).toBe('$0');
  });
});

describe('formatPercent', () => {
  it('formats with default 1 decimal', () => {
    expect(formatPercent(3.0)).toBe('3.0%');
    expect(formatPercent(6.5)).toBe('6.5%');
  });

  it('formats with specified decimals', () => {
    expect(formatPercent(3.456, 2)).toBe('3.46%');
    expect(formatPercent(0, 0)).toBe('0%');
  });
});

// ─── 9. resolveYearlyRates ────────────────────────────────────────────────────

describe('resolveYearlyRates', () => {
  it('scalar input returns uniform 30-element array', () => {
    const rates = resolveYearlyRates(6.5);
    expect(rates).toHaveLength(30);
    expect(rates.every(r => r === 6.5)).toBe(true);
  });

  it('single control point at year 1 fills all years', () => {
    const rates = resolveYearlyRates([{ year: 1, rate: 5.0 }]);
    expect(rates).toHaveLength(30);
    expect(rates.every(r => r === 5.0)).toBe(true);
  });

  it('two control points interpolate linearly', () => {
    const rates = resolveYearlyRates([{ year: 1, rate: 5.0 }, { year: 6, rate: 7.0 }]);
    expect(rates[0]).toBe(5.0);       // year 1: at first point
    expect(rates[2]).toBeCloseTo(5.8); // year 3: 2/5 of the way from 5 to 7
    expect(rates[5]).toBe(7.0);       // year 6: at second point
    expect(rates[29]).toBe(7.0);      // year 30: flat after last point
  });

  it('unsorted control points are handled correctly', () => {
    const rates = resolveYearlyRates([{ year: 10, rate: 8.0 }, { year: 1, rate: 5.0 }]);
    expect(rates[0]).toBe(5.0);
    expect(rates[4]).toBeCloseTo(5.0 + (4/9) * 3); // year 5: interpolated
    expect(rates[9]).toBe(8.0);
    expect(rates[29]).toBe(8.0);
  });

  it('three control points with interpolation', () => {
    const rates = resolveYearlyRates([
      { year: 1, rate: 4.0 }, { year: 5, rate: 6.0 }, { year: 15, rate: 3.0 }
    ]);
    expect(rates[0]).toBe(4.0);           // year 1
    expect(rates[2]).toBeCloseTo(5.0);    // year 3: halfway from 4 to 6
    expect(rates[4]).toBe(6.0);           // year 5
    expect(rates[9]).toBeCloseTo(4.5);    // year 10: halfway from 6 to 3
    expect(rates[14]).toBe(3.0);          // year 15
    expect(rates[29]).toBe(3.0);          // year 30: flat after last
  });

  it('custom totalYears parameter', () => {
    const rates = resolveYearlyRates(5.0, 10);
    expect(rates).toHaveLength(10);
  });
});

// ─── 10. Variable-Rate Computation ────────────────────────────────────────────

describe('variable rate computation', () => {
  it('single control point matches scalar rate result', () => {
    const scalar = computeMortgage(800000, 20, 6.5, 3, 10);
    const points = computeMortgage(800000, 20, [{ year: 1, rate: 6.5 }], 3, 10);
    expect(points.monthlyPayment).toBeCloseTo(scalar.monthlyPayment, 2);
    expect(points.totalPaid).toBeCloseTo(scalar.totalPaid, 2);
    expect(points.totalInterest).toBeCloseTo(scalar.totalInterest, 2);
    expect(points.remainingBalance).toBeCloseTo(scalar.remainingBalance, 2);
  });

  it('higher rate in later years increases total interest', () => {
    const flat = computeMortgage(800000, 20, 6.5, 3, 10);
    const rising = computeMortgage(800000, 20, [
      { year: 1, rate: 6.5 }, { year: 5, rate: 8.0 }
    ], 3, 10);
    expect(rising.totalInterest).toBeGreaterThan(flat.totalInterest);
  });

  it('lower rate in later years decreases total interest', () => {
    const flat = computeMortgage(800000, 20, 6.5, 3, 10);
    const falling = computeMortgage(800000, 20, [
      { year: 1, rate: 6.5 }, { year: 5, rate: 4.0 }
    ], 3, 10);
    expect(falling.totalInterest).toBeLessThan(flat.totalInterest);
  });

  it('schedule rows include correct per-year rate (interpolated)', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 6, rate: 7.0 }
    ], 3, 10);
    expect(result.schedule[0].rate).toBe(5.0);           // year 1
    expect(result.schedule[2].rate).toBeCloseTo(5.8);    // year 3: interpolated
    expect(result.schedule[5].rate).toBe(7.0);           // year 6
    expect(result.schedule[9].rate).toBe(7.0);           // year 10: flat after last
  });

  it('balance continuity holds with variable rates', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 3, rate: 7.0 }, { year: 8, rate: 4.0 }
    ], 3, 10);
    for (let i = 1; i < result.schedule.length; i++) {
      expect(result.schedule[i].beginningBalance)
        .toBeCloseTo(result.schedule[i - 1].endingBalance, 2);
    }
  });

  it('principal + interest = payment holds each year with variable rates', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 5, rate: 9.0 }
    ], 3, 10);
    for (const yr of result.schedule) {
      expect(yr.principal + yr.interest).toBeCloseTo(yr.payment, 1);
    }
  });

  it('30-year variable rate fully amortizes', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 10, rate: 7.0 }, { year: 20, rate: 4.0 }
    ], 0, 30);
    expect(result.remainingBalance).toBeCloseTo(0, 0);
  });

  it('totalPaid equals sum of yearly payments', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 5, rate: 8.0 }
    ], 3, 10);
    const sumPayments = result.schedule.reduce((s, yr) => s + yr.payment, 0);
    expect(result.totalPaid).toBeCloseTo(sumPayments, 2);
  });
});

// ─── 11. Schedule Monthly Payment Field ───────────────────────────────────────

describe('schedule monthlyPayment field', () => {
  it('monthlyPayment * 12 = annual payment for each year', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    for (const yr of result.schedule) {
      expect(yr.monthlyPayment * 12).toBeCloseTo(yr.payment, 2);
    }
  });

  it('monthlyPayment is constant with a fixed rate', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 30);
    const first = result.schedule[0].monthlyPayment;
    for (const yr of result.schedule) {
      expect(yr.monthlyPayment).toBeCloseTo(first, 2);
    }
  });

  it('monthlyPayment changes with variable rates', () => {
    const result = computeMortgage(800000, 20, [
      { year: 1, rate: 5.0 }, { year: 6, rate: 8.0 }
    ], 3, 10);
    // years 1-5 have lower rates than years 6-10, so monthly payment should differ
    expect(result.schedule[0].monthlyPayment).not.toBeCloseTo(result.schedule[9].monthlyPayment, 0);
    // each row's monthlyPayment * 12 should still equal payment
    for (const yr of result.schedule) {
      expect(yr.monthlyPayment * 12).toBeCloseTo(yr.payment, 2);
    }
  });

  it('summary monthlyPayment matches first schedule row', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    expect(result.monthlyPayment).toBeCloseTo(result.schedule[0].monthlyPayment, 2);
  });
});

// ─── 12. Property Tax & Insurance ─────────────────────────────────────────────

describe('property tax and insurance', () => {
  it('each year propertyTax = homeValue * PROPERTY_TAX_RATE', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    for (const yr of result.schedule) {
      expect(yr.propertyTax).toBeCloseTo(yr.homeValue * PROPERTY_TAX_RATE, 2);
    }
  });

  it('each year insurance = homeValue * INSURANCE_RATE', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    for (const yr of result.schedule) {
      expect(yr.insurance).toBeCloseTo(yr.homeValue * INSURANCE_RATE, 2);
    }
  });

  it('tax and insurance grow with appreciation', () => {
    const result = computeMortgage(800000, 20, 6.5, 5, 10);
    expect(result.schedule[9].propertyTax).toBeGreaterThan(result.schedule[0].propertyTax);
    expect(result.schedule[9].insurance).toBeGreaterThan(result.schedule[0].insurance);
  });

  it('tax and insurance are constant with 0% appreciation', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 10);
    for (const yr of result.schedule) {
      expect(yr.propertyTax).toBeCloseTo(800000 * PROPERTY_TAX_RATE, 2);
      expect(yr.insurance).toBeCloseTo(800000 * INSURANCE_RATE, 2);
    }
  });

  it('totalPropertyTax = sum of schedule propertyTax', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    const sum = result.schedule.reduce((s, yr) => s + yr.propertyTax, 0);
    expect(result.totalPropertyTax).toBeCloseTo(sum, 2);
  });

  it('totalInsurance = sum of schedule insurance', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    const sum = result.schedule.reduce((s, yr) => s + yr.insurance, 0);
    expect(result.totalInsurance).toBeCloseTo(sum, 2);
  });

  it('tax and insurance are included in netProfit calculation', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    const totalCash = result.downPayment + result.totalPaid + result.totalPropertyTax + result.totalInsurance;
    expect(result.netProfit).toBeCloseTo(result.equity - totalCash, 2);
  });

  it('tax and insurance make netProfit lower than without them', () => {
    const result = computeMortgage(800000, 20, 6.5, 3, 10);
    // netProfit should be lower than equity - (downPayment + totalPaid) since tax+insurance are extra costs
    const profitWithoutTaxIns = result.equity - (result.downPayment + result.totalPaid);
    expect(result.netProfit).toBeLessThan(profitWithoutTaxIns);
  });
});

// ─── 13. PMI ──────────────────────────────────────────────────────────────────

describe('PMI', () => {
  it('no PMI when down payment >= 20%', () => {
    const result = computeMortgage(800000, 20, 6.5, 0, 10);
    for (const yr of result.schedule) {
      expect(yr.pmi).toBe(0);
    }
    expect(result.totalPMI).toBe(0);
  });

  it('PMI applies when equity < 20% of home value', () => {
    const result = computeMortgage(800000, 10, 6.5, 0, 10);
    expect(result.schedule[0].pmi).toBeGreaterThan(0);
    expect(result.totalPMI).toBeGreaterThan(0);
  });

  it('PMI = balance * PMI_RATE when active', () => {
    const result = computeMortgage(800000, 10, 6.5, 0, 1);
    const yr = result.schedule[0];
    expect(yr.pmi).toBeCloseTo(yr.endingBalance * PMI_RATE, 0);
  });

  it('PMI drops off once equity reaches 20%', () => {
    const result = computeMortgage(800000, 10, 6.5, 5, 30);
    const firstWithoutPMI = result.schedule.find(yr => yr.pmi === 0);
    expect(firstWithoutPMI).toBeDefined();
    // once PMI drops, it stays off
    const idx = result.schedule.indexOf(firstWithoutPMI);
    for (let i = idx; i < result.schedule.length; i++) {
      expect(result.schedule[i].pmi).toBe(0);
    }
  });

  it('PMI is included in totalCashInvested for netProfit', () => {
    const result = computeMortgage(800000, 10, 6.5, 3, 10);
    const totalCash = result.downPayment + result.totalPaid + result.totalPropertyTax + result.totalInsurance + result.totalPMI;
    expect(result.netProfit).toBeCloseTo(result.equity - totalCash, 2);
  });
});

// ─── 14. Stock Market Comparison ──────────────────────────────────────────────

describe('computeStockComparison', () => {
  it('compounds a lump sum correctly', () => {
    const result = computeStockComparison(100000, 10, 10);
    expect(result.finalStockValue).toBeCloseTo(100000 * Math.pow(1.10, 10), 2);
  });

  it('0% return keeps value at initial investment', () => {
    const result = computeStockComparison(160000, 0, 10);
    expect(result.finalStockValue).toBeCloseTo(160000, 2);
    for (const yr of result.schedule) {
      expect(yr.stockValue).toBeCloseTo(160000, 2);
    }
  });

  it('schedule length matches holding years', () => {
    const result = computeStockComparison(100000, 10, 5);
    expect(result.schedule.length).toBe(5);
  });

  it('year-by-year compounding is correct', () => {
    const result = computeStockComparison(200000, 8, 20);
    for (const yr of result.schedule) {
      expect(yr.stockValue).toBeCloseTo(200000 * Math.pow(1.08, yr.year), 2);
    }
  });

  it('finalStockValue matches last schedule entry', () => {
    const result = computeStockComparison(160000, 10, 10);
    expect(result.finalStockValue).toBe(result.schedule[9].stockValue);
  });
});
