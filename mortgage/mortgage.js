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

export function computeMortgage(housePrice, downPct, annualRate, appreciationRate, holdingYears) {
  const downPayment = housePrice * downPct / 100;
  const loanAmount = housePrice - downPayment;
  const r = annualRate / 100 / 12;
  const n = 360; // 30-year fixed
  const M = r === 0 ? loanAmount / n : loanAmount * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);

  const schedule = [];
  let balance = loanAmount;

  for (let year = 1; year <= holdingYears; year++) {
    const beginBal = balance;
    let yearPrincipal = 0;
    let yearInterest = 0;

    for (let m = 0; m < 12; m++) {
      const intPmt = balance * r;
      const prinPmt = M - intPmt;
      yearInterest += intPmt;
      yearPrincipal += prinPmt;
      balance -= prinPmt;
    }

    balance = Math.max(0, balance);
    const homeValue = housePrice * Math.pow(1 + appreciationRate / 100, year);
    const equity = homeValue - balance;

    schedule.push({
      year,
      beginningBalance: beginBal,
      payment: M * 12,
      principal: yearPrincipal,
      interest: yearInterest,
      endingBalance: balance,
      homeValue,
      equity,
    });
  }

  const totalPaid = M * 12 * holdingYears;
  const totalInterest = schedule.reduce((s, y) => s + y.interest, 0);
  const last = schedule[holdingYears - 1];
  const totalCashInvested = downPayment + totalPaid;
  const netProfit = last.equity - totalCashInvested;
  const annROI = totalCashInvested > 0
    ? Math.pow(last.equity / totalCashInvested, 1 / holdingYears) - 1
    : 0;

  return {
    monthlyPayment: M,
    downPayment,
    loanAmount,
    totalPaid,
    totalInterest,
    finalHomeValue: last.homeValue,
    remainingBalance: last.endingBalance,
    equity: last.equity,
    netProfit,
    annualizedROI: annROI,
    schedule,
  };
}
