export function formatCurrency(v) {
  if (Math.abs(v) >= 1e6) return (v < 0 ? '-' : '') + '$' + (Math.abs(v) / 1e6).toFixed(2) + 'M';
  return '$' + Math.round(v).toLocaleString('en-US');
}

export function formatAxisCurrency(v) {
  if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) {
    const k = v / 1e3;
    return k === Math.floor(k) ? '$' + k + 'k' : '$' + k.toFixed(1) + 'k';
  }
  return '$' + v;
}

export function formatPercent(v, d = 1) { return v.toFixed(d) + '%'; }

// Generic interpolation for {year, value} control points
export function resolveYearlyValues(input, totalYears = 30) {
  if (typeof input === 'number') return Array.from({ length: totalYears }, () => input);
  const sorted = [...input].sort((a, b) => a.year - b.year);
  const values = new Array(totalYears);
  for (let y = 1; y <= totalYears; y++) {
    let before = sorted[0];
    let after = null;
    for (const cp of sorted) {
      if (cp.year <= y) before = cp;
      else if (!after) after = cp;
    }
    if (!after || before.year === y) {
      values[y - 1] = before.value;
    } else {
      const t = (y - before.year) / (after.year - before.year);
      values[y - 1] = before.value + t * (after.value - before.value);
    }
  }
  return values;
}

// Backward-compatible: accepts {year, rate} control points
export function resolveYearlyRates(rateInput, totalYears = 30) {
  if (typeof rateInput === 'number') return resolveYearlyValues(rateInput, totalYears);
  return resolveYearlyValues(rateInput.map(cp => ({ year: cp.year, value: cp.rate })), totalYears);
}

export const PROPERTY_TAX_RATE = 0.01;
export const INSURANCE_RATE = 0.004;
export const PMI_RATE = 0.007;
export const STANDARD_DEDUCTION_MARRIED = 32200;
export const SALT_CAP = 40000;
export const MORTGAGE_DEBT_CAP = 750000;
export const GA_STATE_TAX_RATE = 0.0519; // Georgia flat rate 2026

// 2026 married filing jointly brackets
export const TAX_BRACKETS_MFJ = [
  { limit: 24900, rate: 10 },
  { limit: 101400, rate: 12 },
  { limit: 201550, rate: 22 },
  { limit: 383900, rate: 24 },
  { limit: 487450, rate: 32 },
  { limit: 731200, rate: 35 },
  { limit: Infinity, rate: 37 },
];

export function computeFederalTax(grossIncome, deduction = STANDARD_DEDUCTION_MARRIED) {
  const taxableIncome = Math.max(0, grossIncome - deduction);
  let tax = 0, prev = 0;
  for (const bracket of TAX_BRACKETS_MFJ) {
    const taxable = Math.min(taxableIncome, bracket.limit) - prev;
    if (taxable <= 0) break;
    tax += taxable * bracket.rate / 100;
    prev = bracket.limit;
  }
  return tax;
}

export function computeFullScenario(housePrice, downPayment, stockInvestment, rateInput,
  appreciationRate, holdingYears, maintenanceRate, incomeInput, stockReturnPct) {
  const loanAmount = housePrice - downPayment;
  const yearlyRates = resolveYearlyRates(rateInput);
  const yearlyIncomes = incomeInput ? resolveYearlyValues(incomeInput, 30) : null;

  const schedule = [];
  let balance = loanAmount;
  let stockPortfolio = stockInvestment;

  for (let year = 1; year <= holdingYears; year++) {
    const beginBal = balance;
    const annualRate = yearlyRates[year - 1];
    const r = annualRate / 100 / 12;
    const remainingMonths = (30 - (year - 1)) * 12;

    let M;
    if (r === 0) {
      M = balance / remainingMonths;
    } else {
      M = balance * (r * Math.pow(1 + r, remainingMonths)) / (Math.pow(1 + r, remainingMonths) - 1);
    }

    let yearPrincipal = 0;
    let yearInterest = 0;

    for (let m = 0; m < 12; m++) {
      if (balance <= 0) break;
      const intPmt = balance * r;
      const prinPmt = Math.min(M - intPmt, balance);
      yearInterest += intPmt;
      yearPrincipal += prinPmt;
      balance -= prinPmt;
    }

    balance = Math.max(0, balance);
    const homeValue = housePrice * Math.pow(1 + appreciationRate / 100, year);
    const propertyTax = homeValue * PROPERTY_TAX_RATE;
    const insurance = homeValue * INSURANCE_RATE;
    const maintenance = homeValue * maintenanceRate / 100;
    const equity = homeValue - balance;
    const pmi = (equity / homeValue < 0.2 && balance > 0) ? balance * PMI_RATE : 0;

    // Tax computation: state tax first (no dependency), then include in SALT for federal
    const income = yearlyIncomes ? yearlyIncomes[year - 1] : 0;
    const stateTax = Math.max(0, income - STANDARD_DEDUCTION_MARRIED) * GA_STATE_TAX_RATE;
    const deductibleInterest = loanAmount > 0 ? yearInterest * Math.min(1, MORTGAGE_DEBT_CAP / loanAmount) : 0;
    const saltDeduction = Math.min(propertyTax + stateTax, SALT_CAP);
    const totalItemized = deductibleInterest + saltDeduction;
    const taxWithItemization = computeFederalTax(income, Math.max(STANDARD_DEDUCTION_MARRIED, totalItemized));
    const taxWithStandard = computeFederalTax(income, STANDARD_DEDUCTION_MARRIED);
    const taxSavings = taxWithStandard - taxWithItemization;

    // Housing costs and cashflow
    const housingCosts = M * 12 + propertyTax + insurance + maintenance + pmi;
    const afterTaxIncome = income - taxWithItemization - stateTax;
    const cashflow = afterTaxIncome - housingCosts;

    // Stock portfolio: grow existing, then add/withdraw cashflow
    const preWithdraw = stockPortfolio * (1 + stockReturnPct / 100) + cashflow;
    const bankrupt = preWithdraw < 0;
    stockPortfolio = Math.max(0, preWithdraw);

    schedule.push({
      year,
      monthlyPayment: M,
      beginningBalance: beginBal,
      payment: M * 12,
      principal: yearPrincipal,
      interest: yearInterest,
      endingBalance: balance,
      homeValue,
      equity,
      rate: annualRate,
      propertyTax,
      insurance,
      maintenance,
      pmi,
      taxSavings,
      income,
      federalTax: taxWithItemization,
      stateTax,
      housingCosts,
      afterTaxIncome,
      cashflow,
      bankrupt,
      stockValue: stockPortfolio,
    });
  }

  const totalPaid = schedule.reduce((s, yr) => s + yr.payment, 0);
  const totalInterest = schedule.reduce((s, y) => s + y.interest, 0);
  const totalPropertyTax = schedule.reduce((s, yr) => s + yr.propertyTax, 0);
  const totalInsurance = schedule.reduce((s, yr) => s + yr.insurance, 0);
  const totalPMI = schedule.reduce((s, yr) => s + yr.pmi, 0);
  const totalMaintenance = schedule.reduce((s, yr) => s + yr.maintenance, 0);
  const totalTaxSavings = schedule.reduce((s, yr) => s + yr.taxSavings, 0);
  const last = schedule[holdingYears - 1];
  const totalCashInvested = downPayment + totalPaid + totalPropertyTax + totalInsurance + totalPMI + totalMaintenance - totalTaxSavings;
  const netProfit = last.equity - totalCashInvested;
  const annROI = totalCashInvested > 0
    ? Math.pow(last.equity / totalCashInvested, 1 / holdingYears) - 1
    : 0;

  return {
    monthlyPayment: schedule[0].payment / 12,
    downPayment,
    loanAmount,
    totalPaid,
    totalInterest,
    totalPropertyTax,
    totalInsurance,
    totalPMI,
    totalMaintenance,
    totalTaxSavings,
    finalHomeValue: last.homeValue,
    remainingBalance: last.endingBalance,
    equity: last.equity,
    netProfit,
    annualizedROI: annROI,
    finalStockValue: last.stockValue,
    schedule,
  };
}

// Backward-compatible wrapper
export function computeMortgage(housePrice, downPct, rateInput, appreciationRate, holdingYears, maintenanceRate = 0, marginalTaxRate = 0) {
  const downPayment = housePrice * downPct / 100;
  const result = computeFullScenario(housePrice, downPayment, 0, rateInput, appreciationRate, holdingYears, maintenanceRate, null, 0);
  // Apply legacy flat marginal tax rate if specified (for backward compat with tests)
  if (marginalTaxRate > 0) {
    let totalTaxSavings = 0;
    for (const yr of result.schedule) {
      const deductibleInterest = result.loanAmount > 0 ? yr.interest * Math.min(1, MORTGAGE_DEBT_CAP / result.loanAmount) : 0;
      const saltDeduction = Math.min(yr.propertyTax, SALT_CAP);
      const totalItemized = deductibleInterest + saltDeduction;
      yr.taxSavings = Math.max(0, totalItemized - STANDARD_DEDUCTION_MARRIED) * marginalTaxRate / 100;
      totalTaxSavings += yr.taxSavings;
    }
    result.totalTaxSavings = totalTaxSavings;
    const totalCashInvested = result.downPayment + result.totalPaid + result.totalPropertyTax + result.totalInsurance + result.totalPMI + result.totalMaintenance - totalTaxSavings;
    result.netProfit = result.equity - totalCashInvested;
    result.annualizedROI = totalCashInvested > 0
      ? Math.pow(result.equity / totalCashInvested, 1 / holdingYears) - 1
      : 0;
  }
  return result;
}

export function computeStockComparison(lumpSum, annualReturnPct, holdingYears) {
  const schedule = [];
  for (let year = 1; year <= holdingYears; year++) {
    schedule.push({
      year,
      stockValue: lumpSum * Math.pow(1 + annualReturnPct / 100, year),
    });
  }
  return {
    finalStockValue: schedule[holdingYears - 1].stockValue,
    schedule,
  };
}
