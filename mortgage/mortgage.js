export function formatCurrency(v) {
  if (Math.abs(v) >= 1e6) return (v < 0 ? '-' : '') + '$' + (Math.abs(v) / 1e6).toFixed(2) + 'M';
  return '$' + Math.round(v).toLocaleString('en-US');
}

export function formatAxisCurrency(v) {
  if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) return '$' + Math.round(v / 1e3) + 'k';
  return '$' + v;
}

export function formatPercent(v, d = 1) { return v.toFixed(d) + '%'; }

export function resolveYearlyRates(rateInput, totalYears = 30) {
  if (typeof rateInput === 'number') {
    return Array.from({ length: totalYears }, () => rateInput);
  }
  const sorted = [...rateInput].sort((a, b) => a.year - b.year);
  const rates = new Array(totalYears);
  for (let y = 1; y <= totalYears; y++) {
    // Find surrounding control points
    let before = sorted[0];
    let after = null;
    for (const cp of sorted) {
      if (cp.year <= y) before = cp;
      else if (!after) after = cp;
    }
    if (!after || before.year === y) {
      // At or past the last control point: use its rate
      rates[y - 1] = before.rate;
    } else {
      // Linearly interpolate between before and after
      const t = (y - before.year) / (after.year - before.year);
      rates[y - 1] = before.rate + t * (after.rate - before.rate);
    }
  }
  return rates;
}

export const PROPERTY_TAX_RATE = 0.01;  // 1.0% of home value per year
export const INSURANCE_RATE = 0.004;    // 0.4% of home value per year
export const PMI_RATE = 0.007;          // 0.7% of loan amount per year

export function computeMortgage(housePrice, downPct, rateInput, appreciationRate, holdingYears, maintenanceRate = 0) {
  const downPayment = housePrice * downPct / 100;
  const loanAmount = housePrice - downPayment;
  const yearlyRates = resolveYearlyRates(rateInput);

  const schedule = [];
  let balance = loanAmount;

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
    });
  }

  const totalPaid = schedule.reduce((s, yr) => s + yr.payment, 0);
  const totalInterest = schedule.reduce((s, y) => s + y.interest, 0);
  const totalPropertyTax = schedule.reduce((s, yr) => s + yr.propertyTax, 0);
  const totalInsurance = schedule.reduce((s, yr) => s + yr.insurance, 0);
  const totalPMI = schedule.reduce((s, yr) => s + yr.pmi, 0);
  const totalMaintenance = schedule.reduce((s, yr) => s + yr.maintenance, 0);
  const last = schedule[holdingYears - 1];
  const totalCashInvested = downPayment + totalPaid + totalPropertyTax + totalInsurance + totalPMI + totalMaintenance;
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
    finalHomeValue: last.homeValue,
    remainingBalance: last.endingBalance,
    equity: last.equity,
    netProfit,
    annualizedROI: annROI,
    schedule,
  };
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
