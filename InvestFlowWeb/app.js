const STORAGE_KEY = "invest-flow-web-v1";
const FAMILY_KEY = "invest-flow-family-id";
const STATUSES = ["Inbox", "Watch", "Candidate", "Rejected", "Portfolio"];
const urlParams = new URLSearchParams(window.location.search);
const familyId = urlParams.get("family") || localStorage.getItem(FAMILY_KEY) || "family";
localStorage.setItem(FAMILY_KEY, familyId);
let remoteReady = false;
let suppressRemoteSave = false;
let remoteUpdatedAt = "";
let remoteSaveTimer = null;

const i18n = {
  en: {
    money: "Money",
    routine: "Routine",
    postit: "Post-it",
    investableThisMonth: "Investable this month",
    income: "Income",
    expense: "Expense",
    expenses: "Expenses",
    allocated: "Allocated",
    quickCashFlow: "Quick cash flow",
    label: "Label",
    amount: "Amount",
    addEntry: "Add entry",
    paycheck: "+ Paycheck",
    bill: "- Bill",
    recurringAllocation: "Recurring allocation",
    symbol: "Symbol",
    monthly: "Monthly",
    addToPlan: "Add to plan",
    cashFlowMix: "Cash-flow mix",
    budgetRuleTitle: "50-30-20 budget",
    budgetRuleSubtitle: "Needs · Wants · Future",
    needs: "Needs",
    wants: "Wants",
    future: "Future",
    target: "Target",
    actual: "Actual",
    statementAnalyzer: "Bank/card paste analyzer",
    uploadStatement: "Upload Excel/CSV",
    uploadHint: "Upload Hana Bank .xls/.xlsx, CSV, TSV, TXT, or paste the same content below.",
    xlsParserUnavailable: "This binary Excel file needs the spreadsheet parser. Check your internet connection or export as CSV/TSV and upload again.",
    fileReadFailed: "Could not read this file.",
    statementPlaceholder: "Paste Hana Bank, KB Card, Samsung Card, Shinhan Card, or other transaction history here.",
    analyzeStatement: "Analyze 50-30-20",
    addAnalyzedToMoney: "Add to Money",
    review: "Review",
    reviewTitle: "Classification review",
    reviewSubtitle: "Review classified transactions",
    backToMoney: "Back",
    confirmImport: "Confirm to Money",
    includeAll: "Include all",
    excludeTransfers: "Exclude transfers",
    included: "Included",
    excluded: "Excluded",
    transactionType: "Type",
    classification: "Classification",
    monthlyOverview: "Monthly overview",
    noItems: "No items",
    analysisEmpty: "Paste transaction lines first.",
    analysisReady: (count) => `${count} classified transactions ready.`,
    analysisImported: (count) => `${count} transactions added to Money.`,
    analysisAutoImported: (count, skipped) => `${count} transactions added to Money automatically. ${skipped} duplicates skipped.`,
    analysisNoReady: "Analyze transactions before adding.",
    essentialReason: "Essential living cost",
    discretionaryReason: "Flexible lifestyle spend",
    investingReason: "Future, debt, savings, or investment",
    incomeReason: "Detected income or deposit",
    transfer: "Transfer",
    transferReason: "Internal transfer excluded from 50-30-20 totals",
    unknownMerchant: "Transaction",
    monthlyRecurring: "Monthly recurring",
    routineCompletion: "Routine completion",
    completedOf: (complete, total) => `${complete} of ${total}`,
    morning: "Morning",
    readMarketTone: "Read market tone",
    checkCash: "Check cash available",
    reviewWatchlist: "Review watchlist",
    intraday: "Intraday",
    checkAlerts: "Check alerts only",
    answerContrarian: "Answer contrarian prompts",
    noFomo: "No-FOMO confirmation",
    contrarianQuestions: "Pre-trade contrarian questions",
    wrongThesis: "What would make this thesis wrong?",
    otherSide: "Who is on the other side of this trade?",
    waitPrice: "What price would make me wait?",
    evening: "Evening",
    writeReview: "Write review",
    reviewAllocationDrift: "Review allocation drift",
    tomorrowPlan: "Set tomorrow plan",
    dailyReviewNotes: "Daily review notes",
    learnToday: "What did I learn today?",
    capture: "Capture",
    stock: "Stock",
    crypto: "Crypto",
    ideaTitle: "Idea title",
    textNote: "Text note",
    saveText: "Save text",
    voiceNote: "Voice note",
    mockMarketData: "Mock market data",
    noIdeas: (status) => `No ideas in ${statusLabel(status)}.`,
    proposed: (amount) => `Proposed: ${money(amount)}/mo`,
    approve: "Approve",
    aiSummary: "AI summary",
    resetDemo: "Reset demo data",
    moveIdeaStatus: "Move idea status",
    thesis: "Thesis",
    noNoteYet: "No note yet.",
    mockedAt: "is mocked at",
    dayMove: "day move",
    checkDownside: "Check downside, catalyst durability, and position size before approval.",
    start: "Start",
    smallWeight: "at a small recurring weight until the thesis earns more capital.",
    voiceFallback: "Voice note placeholder: investigate entry after a pullback, confirm thesis, and avoid chasing green candles.",
    statuses: {
      Inbox: "Inbox",
      Watch: "Watch",
      Candidate: "Candidate",
      Rejected: "Rejected",
      Portfolio: "Portfolio"
    }
  },
  ko: {
    money: "머니",
    routine: "루틴",
    postit: "포스트잇",
    investableThisMonth: "이번 달 투자 가능 금액",
    income: "수입",
    expense: "지출",
    expenses: "지출",
    allocated: "배분",
    quickCashFlow: "빠른 현금흐름 입력",
    label: "항목명",
    amount: "금액",
    addEntry: "항목 추가",
    paycheck: "+ 월급",
    bill: "- 고정비",
    recurringAllocation: "반복 투자 배분",
    symbol: "심볼",
    monthly: "월 금액",
    addToPlan: "계획에 추가",
    cashFlowMix: "현금흐름 구성",
    budgetRuleTitle: "50-30-20 예산",
    budgetRuleSubtitle: "필수 · 선택 · 미래",
    needs: "필수",
    wants: "선택",
    future: "투자",
    target: "목표",
    actual: "현재",
    statementAnalyzer: "은행/카드 내역 붙여넣기 분석",
    uploadStatement: "엑셀/CSV 업로드",
    uploadHint: "하나은행 .xls/.xlsx, CSV, TSV, TXT를 업로드하거나 아래에 같은 내용을 붙여넣으세요.",
    xlsParserUnavailable: "이 바이너리 엑셀 파일은 스프레드시트 파서가 필요합니다. 인터넷 연결을 확인하거나 CSV/TSV로 내보낸 뒤 다시 업로드하세요.",
    fileReadFailed: "파일을 읽을 수 없습니다.",
    statementPlaceholder: "하나은행, 국민카드, 삼성카드, 신한카드 등의 거래 내역을 그대로 붙여넣으세요.",
    analyzeStatement: "50-30-20 분석",
    addAnalyzedToMoney: "Money에 추가",
    review: "검토",
    reviewTitle: "분류 검토",
    reviewSubtitle: "분류된 거래를 확인하세요",
    backToMoney: "뒤로",
    confirmImport: "Money에 확정",
    includeAll: "전체 포함",
    excludeTransfers: "이체 제외",
    included: "포함",
    excluded: "제외",
    transactionType: "입출금",
    classification: "분류",
    monthlyOverview: "월별 요약",
    noItems: "항목 없음",
    analysisEmpty: "먼저 거래 내역을 붙여넣어 주세요.",
    analysisReady: (count) => `${count}건의 거래를 분류했습니다.`,
    analysisImported: (count) => `${count}건을 Money에 추가했습니다.`,
    analysisAutoImported: (count, skipped) => `${count}건을 자동으로 Money에 추가했습니다. 중복 ${skipped}건은 제외했습니다.`,
    analysisNoReady: "추가하기 전에 먼저 분석해 주세요.",
    essentialReason: "생계유지에 필요한 필수 지출",
    discretionaryReason: "삶의 질을 위한 선택 지출",
    investingReason: "비상금, 부채상환, 투자 등 미래 지출",
    incomeReason: "수입 또는 입금으로 감지",
    transfer: "이체",
    transferReason: "50-30-20 합계에서 제외되는 내부 이체",
    unknownMerchant: "거래",
    monthlyRecurring: "매월 반복",
    routineCompletion: "루틴 완료율",
    completedOf: (complete, total) => `${total}개 중 ${complete}개 완료`,
    morning: "아침",
    readMarketTone: "시장 분위기 확인",
    checkCash: "투자 가능 현금 확인",
    reviewWatchlist: "관심종목 점검",
    intraday: "장중",
    checkAlerts: "알림만 확인",
    answerContrarian: "반대 질문 답하기",
    noFomo: "추격매수 방지 확인",
    contrarianQuestions: "매수 전 반대 질문",
    wrongThesis: "이 투자 가설이 틀렸다는 증거는?",
    otherSide: "이 거래의 반대편에는 누가 있는가?",
    waitPrice: "어떤 가격이면 기다릴 것인가?",
    evening: "저녁",
    writeReview: "하루 리뷰 작성",
    reviewAllocationDrift: "배분 이탈 점검",
    tomorrowPlan: "내일 계획 설정",
    dailyReviewNotes: "일일 리뷰 노트",
    learnToday: "오늘 배운 점은?",
    capture: "아이디어 저장",
    stock: "주식",
    crypto: "크립토",
    ideaTitle: "아이디어 제목",
    textNote: "텍스트 메모",
    saveText: "텍스트 저장",
    voiceNote: "음성 메모",
    mockMarketData: "모의 시장 데이터",
    noIdeas: (status) => `${statusLabel(status)} 상태의 아이디어가 없습니다.`,
    proposed: (amount) => `제안: 월 ${money(amount)}`,
    approve: "승인",
    aiSummary: "AI 요약",
    resetDemo: "데모 초기화",
    moveIdeaStatus: "아이디어 상태 변경",
    thesis: "투자 가설",
    noNoteYet: "아직 메모가 없습니다.",
    mockedAt: "모의 가격",
    dayMove: "일간 변동",
    checkDownside: "승인 전 하방 리스크, 촉매 지속성, 포지션 크기를 확인하세요.",
    start: "시작:",
    smallWeight: "은 투자 가설이 검증될 때까지 작은 반복 비중으로 운용하세요.",
    voiceFallback: "음성 메모 예시: 조정 후 진입을 검토하고, 투자 가설을 확인하며, 급등 추격은 피한다.",
    statuses: {
      Inbox: "인박스",
      Watch: "관찰",
      Candidate: "후보",
      Rejected: "제외",
      Portfolio: "포트폴리오"
    }
  }
};

const marketService = {
  quotes: [
    { symbol: "AAPL", name: "Apple", price: 214.35, change: -0.8 },
    { symbol: "NVDA", name: "NVIDIA", price: 148.2, change: 1.4 },
    { symbol: "BTC", name: "Bitcoin", price: 68250, change: -2.1 },
    { symbol: "ETH", name: "Ethereum", price: 3520, change: 0.7 },
    { symbol: "VOO", name: "Vanguard S&P 500 ETF", price: 521.12, change: 0.3 }
  ],
  quote(symbol) {
    return this.quotes.find((quote) => quote.symbol === symbol.toUpperCase()) ?? {
      symbol: symbol.toUpperCase(),
      name: symbol.toUpperCase(),
      price: 100,
      change: 0
    };
  },
  async refreshFromBackend() {
    const response = await fetch("./api/market", { cache: "no-store" });
    if (!response.ok) throw new Error("Market backend unavailable");
    const payload = await response.json();
    const data = payload.data || {};
    const quotes = Object.entries(data).map(([symbol, value]) => ({
      symbol,
      name: symbol,
      price: Number(value.price || 0),
      change: Number(value.change_percent || 0)
    })).filter((quote) => quote.price > 0);
    if (quotes.length) {
      this.quotes = quotes.slice(0, 40);
    }
  }
};

const financeAnalysisService = {
  analyze(text) {
    return text
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => this.parseLine(line))
      .filter(Boolean);
  },
  parseLine(line) {
    if (/거래일시\s+구분\s+적요|합\s*계/.test(line)) return null;

    const hana = parseHanaBankLine(line);
    const amount = hana?.amount ?? extractAmount(line);
    if (!amount) return null;

    const kind = hana?.kind ?? inferKind(line);
    const bucket = hana?.bucket ?? (kind === "income" ? "income" : classifyBucket(line));
    const merchant = hana?.merchant ?? extractMerchant(line);
    const currency = hana?.currency ?? detectCurrency(line);

    return {
      id: uid(),
      raw: line,
      title: merchant || copy().unknownMerchant,
      amount,
      kind,
      bucket,
      currency,
      date: hana?.date ?? extractDate(line) ?? todayKey(),
      institution: hana?.institution ?? detectInstitution(line),
      reason: reasonForBucket(bucket)
    };
  }
};

const aiService = {
  async summarize(idea) {
    const backendSummary = await this.summarizeWithDeepSeek(idea).catch(() => "");
    if (backendSummary) return backendSummary;

    const quote = marketService.quote(idea.symbol);
    const t = copy();
    if (state.language === "ko") {
      return `${t.thesis}: ${idea.note || t.noNoteYet} ${quote.symbol} ${t.mockedAt} ${money(quote.price, "USD")}, ${quote.change.toFixed(1)}% ${t.dayMove}. ${t.checkDownside}`;
    }
    return `${t.thesis}: ${idea.note || t.noNoteYet} ${quote.symbol} ${t.mockedAt} ${money(quote.price, "USD")} with a ${quote.change.toFixed(1)}% ${t.dayMove}. ${t.checkDownside}`;
  },
  async summarizeWithDeepSeek(idea) {
    const quote = marketService.quote(idea.symbol);
    const response = await fetch("./api/deepseek", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: [{
          role: "user",
          content: `Analyze this investment Post-it. Symbol: ${idea.symbol}. Asset: ${idea.asset}. Note: ${idea.note}. Market: ${quote.price} (${quote.change}%).`
        }]
      })
    });
    if (!response.ok) return "";
    const payload = await response.json();
    return payload.answer || "";
  },
  propose(idea, investable) {
    const weight = idea.asset === "crypto" ? 0.08 : 0.12;
    const t = copy();
    return {
      amount: Math.max(0, Math.round(investable * weight)),
      rationale: state.language === "ko"
        ? `${t.start} ${idea.symbol.toUpperCase()}${t.smallWeight}`
        : `${t.start} ${idea.symbol.toUpperCase()} ${t.smallWeight}`
    };
  }
};

const defaultState = () => ({
  activeScreen: "money",
  language: "en",
  currency: "KRW",
  selectedBucket: "essential",
  cashKind: "income",
  assetKind: "stock",
  ideaStatus: "Inbox",
  entries: [
    { id: uid(), title: "Salary", amount: 6200000, kind: "income", bucket: "income", currency: "KRW", recurring: true },
    { id: uid(), title: "Rent", amount: 2100000, kind: "expense", bucket: "essential", currency: "KRW", recurring: true },
    { id: uid(), title: "Core bills", amount: 950000, kind: "expense", bucket: "essential", currency: "KRW", recurring: true }
  ],
  allocations: [
    { id: uid(), symbol: "VOO", amount: 900000, currency: "KRW" }
  ],
  pendingImports: [],
  analysisMessage: "",
  routineDate: todayKey(),
  routine: {
    morningMarketRead: false,
    morningCashCheck: false,
    morningWatchlistReview: false,
    intradayPriceAlerts: false,
    intradayContrarianCheck: false,
    intradayNoFomoCheck: false,
    eveningJournal: false,
    eveningAllocationReview: false,
    eveningTomorrowPlan: false,
    contrarianOne: "",
    contrarianTwo: "",
    contrarianThree: "",
    dailyReviewNotes: ""
  },
  ideas: [
    {
      id: uid(),
      title: "Core ETF add",
      symbol: "VOO",
      asset: "stock",
      status: "Watch",
      note: "Keep adding when monthly cash flow is positive.",
      summary: "",
      proposal: null,
      approved: false
    }
  ]
});

let state = loadState();

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function uid() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return `id-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return defaultState();
  return normalizeState(JSON.parse(saved));
}

function normalizeState(parsed) {
  parsed.language = parsed.language ?? "en";
  parsed.currency = parsed.currency ?? "KRW";
  parsed.selectedBucket = parsed.selectedBucket ?? "essential";
  parsed.pendingImports = parsed.pendingImports ?? [];
  parsed.analysisMessage = parsed.analysisMessage ?? "";
  parsed.entries = (parsed.entries ?? []).map((entry) => ({
    ...entry,
    currency: entry.currency ?? inferLegacyCurrency(entry.amount, entry.title),
    date: entry.date ?? todayKey(),
    bucket: entry.bucket ?? (entry.kind === "income" ? "income" : classifyBucket(entry.title ?? ""))
  }));
  parsed.allocations = (parsed.allocations ?? []).map((allocation) => ({
    ...allocation,
    currency: allocation.currency ?? inferLegacyCurrency(allocation.amount, allocation.symbol)
  }));
  if (parsed.routineDate !== todayKey()) {
    parsed.routineDate = todayKey();
    parsed.routine = defaultState().routine;
  }
  return parsed;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  scheduleRemoteSave();
}

function scheduleRemoteSave() {
  if (!remoteReady || suppressRemoteSave) return;
  clearTimeout(remoteSaveTimer);
  remoteSaveTimer = setTimeout(saveRemoteState, 600);
}

async function loadRemoteState() {
  try {
    const response = await fetch(`./api/investflow/state?family_id=${encodeURIComponent(familyId)}`, {
      cache: "no-store"
    });
    if (!response.ok) throw new Error("Invest Flow sync unavailable");
    const payload = await response.json();
    remoteReady = true;
    if (!payload.found || !payload.payload) {
      scheduleRemoteSave();
      return;
    }
    remoteUpdatedAt = payload.updated_at || "";
    suppressRemoteSave = true;
    state = normalizeState({ ...defaultState(), ...payload.payload });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    render();
    suppressRemoteSave = false;
  } catch {
    remoteReady = false;
  }
}

async function saveRemoteState() {
  try {
    const response = await fetch("./api/investflow/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        family_id: familyId,
        payload: state
      })
    });
    if (!response.ok) throw new Error("Invest Flow sync unavailable");
    const payload = await response.json();
    remoteUpdatedAt = payload.updated_at || remoteUpdatedAt;
  } catch {
    remoteReady = false;
  }
}

async function refreshRemoteState() {
  if (!remoteReady) return loadRemoteState();
  try {
    const response = await fetch(`./api/investflow/state?family_id=${encodeURIComponent(familyId)}`, {
      cache: "no-store"
    });
    if (!response.ok) throw new Error("Invest Flow sync unavailable");
    const payload = await response.json();
    if (!payload.found || !payload.payload || payload.updated_at === remoteUpdatedAt) return;
    remoteUpdatedAt = payload.updated_at || "";
    suppressRemoteSave = true;
    state = normalizeState({ ...defaultState(), ...payload.payload });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    render();
    suppressRemoteSave = false;
  } catch {
    remoteReady = false;
  }
}

function inferLegacyCurrency(amount, label = "") {
  const value = Number(amount || 0);
  const text = String(label).toLowerCase();
  if (/salary|rent|bill|paycheck|voo|aapl|nvda|btc|eth/.test(text) && value < 100000) return "USD";
  return value < 100000 ? "USD" : "KRW";
}

function money(value, currency = state?.currency ?? "KRW") {
  const locale = currency === "KRW" ? "ko-KR" : "en-US";
  return Number(value || 0).toLocaleString(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  });
}

function copy() {
  return i18n[state?.language === "ko" ? "ko" : "en"];
}

function statusLabel(status) {
  return copy().statuses[status] ?? status;
}

function bucketLabel(bucket) {
  const labels = {
    essential: copy().needs,
    discretionary: copy().wants,
    investing: copy().future,
    income: copy().income,
    expense: copy().expense,
    transfer: copy().transfer
  };
  return labels[bucket] ?? bucket;
}

function reasonForBucket(bucket) {
  const reasons = {
    essential: copy().essentialReason,
    discretionary: copy().discretionaryReason,
    investing: copy().investingReason,
    income: copy().incomeReason,
    transfer: copy().transferReason
  };
  return reasons[bucket] ?? "";
}

function parseHanaBankLine(line) {
  const cells = line.split("\t").map((cell) => cell.trim());
  if (cells.length < 6 || !/^\d{4}-\d{1,2}-\d{1,2}/.test(cells[0])) return null;

  const [, type = "", memo = "", withdrawalRaw = "0", depositRaw = "0", , branch = ""] = cells;
  const withdrawal = parseMoneyToken(withdrawalRaw);
  const deposit = parseMoneyToken(depositRaw);
  const amount = withdrawal > 0 ? withdrawal : deposit;
  if (!amount) return null;

  const text = `${type} ${memo} ${branch}`;
  const isExpense = withdrawal > 0;
  const bucket = classifyHanaBucket(type, memo, branch, isExpense);

  return {
    amount,
    kind: bucket === "transfer" ? "transfer" : (isExpense ? "expense" : "income"),
    bucket,
    merchant: cleanHanaMerchant(type, memo),
    institution: detectInstitution(text),
    date: cells[0],
    currency: "KRW"
  };
}

function parseMoneyToken(value) {
  const normalized = String(value ?? "").replace(/[^\d.-]/g, "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? Math.abs(parsed) : 0;
}

function classifyHanaBucket(type, memo, branch, isExpense) {
  const text = `${type} ${memo} ${branch}`.toLowerCase();

  if (/합\s*계|계좌개설|토스\d*/.test(text)) return "transfer";
  if (/키움증권|증권|주식|펀드|etf|isa|연금|irp|투자/.test(text)) {
    return isExpense ? "investing" : "transfer";
  }
  if (/대출상환|대출이자|대출결산이자|상환/.test(text)) return "investing";
  if (/국민카드|신한카드|삼성카드|현대카드|하나카드/.test(text)) return isExpense ? "discretionary" : "transfer";
  if (/김용/.test(memo) && /송금|이체|대체/.test(type)) return "transfer";
  if (!isExpense) return "income";
  if (/월세|전세|관리비|공과금|전기|가스|수도|통신|보험|병원|약국|마트|교통|주유|교육|학원|고려대학교|논문심사료/.test(text)) return "essential";
  if (/하나머니충전|장학회|카드연회비|네이버파이낸셜|주식회사 경아/.test(text)) return "discretionary";

  return classifyBucket(text);
}

function cleanHanaMerchant(type, memo) {
  const cleanedMemo = memo
    .replace(/\(\(.+?\)\)/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return `${type} ${cleanedMemo}`.trim().slice(0, 42);
}

function extractAmount(line) {
  const matches = line.match(/[-+]?\d[\d,]{2,}/g);
  if (!matches) return 0;
  const numeric = matches
    .map((match) => Number(match.replace(/,/g, "")))
    .filter((value) => Number.isFinite(value) && Math.abs(value) >= 100);
  if (!numeric.length) return 0;
  return Math.abs(numeric[numeric.length - 1]);
}

function inferKind(line) {
  const isIncome = /입금|급여|월급|상여|환급|배당|deposit|salary|payroll|refund|dividend/i.test(line)
    && !/출금|승인|결제|일시불|체크|카드|payment/i.test(line);
  return isIncome ? "income" : "expense";
}

function extractDate(line) {
  const match = String(line).match(/\d{4}[-./]\d{1,2}[-./]\d{1,2}/);
  return match ? match[0].replace(/[./]/g, "-") : "";
}

function detectCurrency(line) {
  if (/\$|usd|달러/i.test(line)) return "USD";
  if (/₩|krw|원|하나은행|국민카드|삼성카드|신한카드|현대카드|하나카드/i.test(line)) return "KRW";
  return state.currency;
}

function extractMerchant(line) {
  const withoutDates = line
    .replace(/\d{2,4}[./-]\d{1,2}[./-]\d{1,2}/g, " ")
    .replace(/\d{1,2}:\d{2}/g, " ")
    .replace(/[-+]?\d[\d,]{2,}/g, " ")
    .replace(/하나은행|국민카드|KB국민|삼성카드|신한카드|승인|일시불|체크|입금|출금|결제/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return withoutDates.slice(0, 34);
}

function detectInstitution(line) {
  if (/하나|hana/i.test(line)) return "Hana Bank";
  if (/국민|kb/i.test(line)) return "KB Card";
  if (/삼성|samsung/i.test(line)) return "Samsung Card";
  if (/신한|shinhan/i.test(line)) return "Shinhan Card";
  return "Manual paste";
}

function classifyBucket(line) {
  const text = line.toLowerCase();
  if (/증권|주식|펀드|etf|isa|연금|퇴직|irp|저축|적금|예금|대출상환|카드대금|상환|비상금|투자|brokerage|stock|fund|saving|loan|debt|retire/.test(text)) {
    return "investing";
  }

  if (/월세|전세|관리비|공과금|전기|가스|수도|통신|보험|병원|약국|의원|마트|식료|교통|버스|지하철|택시|주유|충전|교육|학원|렌트|rent|utility|grocery|market|hospital|pharmacy|insurance|transport|fuel/.test(text)) {
    return "essential";
  }

  if (/카페|커피|스타벅스|외식|배달|요기요|배민|쿠팡|쇼핑|무신사|의류|여행|호텔|항공|영화|넷플릭스|디즈니|게임|취미|주점|술|식당|restaurant|cafe|coffee|shopping|travel|hotel|movie|game|hobby/.test(text)) {
    return "discretionary";
  }

  return "discretionary";
}

function totals() {
  const entries = state.entries.filter((entry) => (entry.currency ?? state.currency) === state.currency);
  const allocations = state.allocations.filter((allocation) => (allocation.currency ?? state.currency) === state.currency);
  const income = entries.filter((entry) => entry.kind === "income").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const expenses = entries.filter((entry) => entry.kind === "expense").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const allocated = allocations.reduce((sum, allocation) => sum + Number(allocation.amount), 0);
  return { income, expenses, allocated, investable: income - expenses - allocated };
}

function budgetTotals() {
  const { income } = totals();
  const entries = state.entries.filter((entry) => (entry.currency ?? state.currency) === state.currency);
  const allocations = state.allocations.filter((allocation) => (allocation.currency ?? state.currency) === state.currency);
  const essential = entries.filter((entry) => entry.kind === "expense" && entry.bucket === "essential").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const discretionary = entries.filter((entry) => entry.kind === "expense" && entry.bucket === "discretionary").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const investingEntries = entries.filter((entry) => entry.kind === "expense" && entry.bucket === "investing").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const allocated = allocations.reduce((sum, allocation) => sum + Number(allocation.amount), 0);
  return {
    income,
    essential,
    discretionary,
    investing: investingEntries + allocated
  };
}

function render() {
  renderI18n();
  renderTabs();
  renderMoney();
  renderRoutine();
  renderPostIt();
  renderReview();
  saveState();
}

function renderI18n() {
  const t = copy();
  document.documentElement.lang = state.language === "ko" ? "ko" : "en";
  $$("[data-i18n]").forEach((element) => {
    const value = t[element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  $$("[data-i18n-placeholder]").forEach((element) => {
    const value = t[element.dataset.i18nPlaceholder];
    if (typeof value === "string") element.placeholder = value;
  });
  $("#reset-demo").title = t.resetDemo;
  $("#reset-demo").setAttribute("aria-label", t.resetDemo);
  $$(".lang-switch button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.lang === state.language);
  });
  $$(".currency-switch button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.currency === state.currency);
  });
}

function renderTabs() {
  const t = copy();
  const title = t[state.activeScreen] ?? t.postit;
  $("#screen-title").textContent = title;

  $$(".screen").forEach((screen) => screen.classList.remove("active"));
  $(`#${state.activeScreen}-screen`).classList.add("active");

  $$(".bottom-nav button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.screen === state.activeScreen);
    button.textContent = t[button.dataset.screen] ?? button.textContent;
  });
}

function renderMoney() {
  const { income, expenses, allocated, investable } = totals();
  $("#investable").textContent = money(investable);
  $("#income-total").textContent = money(income);
  $("#expense-total").textContent = money(expenses);
  $("#allocation-total").textContent = money(allocated);
  renderBudgetSummary();
  renderBucketDetail();
  renderMonthlyOverview();
  renderAnalysisResult();

  $$(".segmented [data-kind]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.kind === state.cashKind);
  });

  $("#allocation-list").innerHTML = state.allocations.filter((allocation) => (allocation.currency ?? state.currency) === state.currency).map((allocation) => `
    <div class="list-item">
      <div><strong>${escapeHtml(allocation.symbol)}</strong><div class="muted">${copy().monthlyRecurring}</div></div>
      <strong>${money(allocation.amount, allocation.currency)}</strong>
    </div>
  `).join("");

  drawCashChart(income, expenses, allocated);
}

function renderBudgetSummary() {
  const budget = budgetTotals();
  const rows = [
    { key: "essential", label: copy().needs, target: 0.5, amount: budget.essential },
    { key: "discretionary", label: copy().wants, target: 0.3, amount: budget.discretionary },
    { key: "investing", label: copy().future, target: 0.2, amount: budget.investing }
  ];
  const income = Math.max(budget.income, 1);

  $("#budget-summary").innerHTML = rows.map((row) => {
    const actualPercent = Math.round((row.amount / income) * 100);
    const targetAmount = budget.income * row.target;
    return `
      <button class="budget-row ${state.selectedBucket === row.key ? "selected" : ""}" type="button" data-budget-bucket="${row.key}">
        <div class="budget-label">
          <strong>${row.label}</strong>
          <span>${copy().actual} ${actualPercent}% · ${copy().target} ${Math.round(row.target * 100)}%</span>
        </div>
        <div class="budget-track" aria-hidden="true">
          <span style="width:${Math.min(actualPercent, 100)}%"></span>
        </div>
        <div class="budget-money">
          <b>${money(row.amount)}</b>
          <span>${money(targetAmount)}</span>
        </div>
      </button>
    `;
  }).join("");
}

function renderBucketDetail() {
  const bucket = state.selectedBucket ?? "essential";
  const entries = currentCurrencyEntries()
    .filter((entry) => entry.kind === "expense" && entry.bucket === bucket)
    .sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")))
    .slice(0, 12);

  $("#bucket-detail").innerHTML = `
    <div class="detail-title">${bucketLabel(bucket)}</div>
    ${entries.length ? entries.map((entry) => `
      <div class="detail-item">
        <div>
          <strong>${escapeHtml(entry.title)}</strong>
          <span class="muted">${formatMonth(entry.date)} · ${escapeHtml(entry.source ?? "")}</span>
        </div>
        <b>${money(entry.amount, entry.currency)}</b>
      </div>
    `).join("") : `<p class="muted">${copy().noItems}</p>`}
  `;
}

function renderMonthlyOverview() {
  const months = monthlySummaries();
  $("#monthly-current").textContent = months[0]?.month ?? "-";
  $("#monthly-list").innerHTML = months.length ? months.map((row) => `
    <div class="monthly-item">
      <strong>${row.month}</strong>
      <span class="gain">+${money(row.income)}</span>
      <span class="loss">-${money(row.expenses)}</span>
      <b>${money(row.income - row.expenses)}</b>
    </div>
  `).join("") : `<p class="muted">${copy().noItems}</p>`;
}

function currentCurrencyEntries() {
  return state.entries.filter((entry) => (entry.currency ?? state.currency) === state.currency);
}

function monthlySummaries() {
  const summary = new Map();
  currentCurrencyEntries().forEach((entry) => {
    if (entry.kind === "transfer") return;
    const month = formatMonth(entry.date);
    const row = summary.get(month) ?? { month, income: 0, expenses: 0 };
    if (entry.kind === "income") row.income += Number(entry.amount);
    if (entry.kind === "expense") row.expenses += Number(entry.amount);
    summary.set(month, row);
  });
  return Array.from(summary.values()).sort((a, b) => b.month.localeCompare(a.month)).slice(0, 6);
}

function formatMonth(dateValue) {
  const text = String(dateValue || todayKey());
  const match = text.match(/\d{4}-\d{1,2}/);
  if (!match) return todayKey().slice(0, 7);
  const [year, month] = match[0].split("-");
  return `${year}-${month.padStart(2, "0")}`;
}

function renderAnalysisResult() {
  const message = state.analysisMessage ? `<p class="muted">${escapeHtml(state.analysisMessage)}</p>` : "";
  const items = state.pendingImports.map((item) => `
    <div class="analysis-item">
      <div>
        <strong>${escapeHtml(item.title)}</strong>
        <div class="muted">${escapeHtml(item.institution)} · ${bucketLabel(item.bucket)} · ${escapeHtml(item.reason)}</div>
      </div>
      <b>${item.kind === "income" ? "+" : item.kind === "transfer" ? "" : "-"}${money(item.amount, item.currency)}</b>
    </div>
  `).join("");
  $("#analysis-result").innerHTML = message + items;
}

function renderReview() {
  const items = state.pendingImports ?? [];
  const included = items.filter((item) => item.included);
  const income = included.filter((item) => item.kind === "income").reduce((sum, item) => sum + Number(item.amount), 0);
  const expenses = included.filter((item) => item.kind === "expense").reduce((sum, item) => sum + Number(item.amount), 0);
  const excluded = items.length - included.length;

  $("#review-count").textContent = copy().analysisReady(items.length);
  $("#review-income").textContent = money(income);
  $("#review-expenses").textContent = money(expenses);
  $("#review-excluded").textContent = String(excluded);
  $("#review-list").innerHTML = items.length ? items.map(reviewItemTemplate).join("") : `<p class="muted">${copy().analysisEmpty}</p>`;
}

function reviewItemTemplate(item) {
  const bucketOptions = ["essential", "discretionary", "investing", "income", "transfer"]
    .map((bucket) => `<option value="${bucket}" ${item.bucket === bucket ? "selected" : ""}>${bucketLabel(bucket)}</option>`)
    .join("");
  const kindOptions = ["expense", "income", "transfer"]
    .map((kind) => `<option value="${kind}" ${item.kind === kind ? "selected" : ""}>${bucketLabel(kind)}</option>`)
    .join("");

  return `
    <article class="review-item ${item.included ? "" : "is-excluded"}">
      <label class="review-include">
        <input type="checkbox" data-review-include="${item.id}" ${item.included ? "checked" : ""}>
        <span>${item.included ? copy().included : copy().excluded}</span>
      </label>
      <div class="review-main">
        <strong>${escapeHtml(item.title)}</strong>
        <span class="muted">${escapeHtml(item.institution)} · ${money(item.amount, item.currency)}</span>
        <span class="muted">${escapeHtml(item.reason)}</span>
      </div>
      <div class="review-controls">
        <label>
          <span>${copy().transactionType}</span>
          <select data-review-kind="${item.id}">${kindOptions}</select>
        </label>
        <label>
          <span>${copy().classification}</span>
          <select data-review-bucket="${item.id}">${bucketOptions}</select>
        </label>
      </div>
    </article>
  `;
}

function analyzeStatementText(text, autoImport = true) {
  if (!text) {
    state.pendingImports = [];
    state.analysisMessage = copy().analysisEmpty;
    render();
    return;
  }

  state.pendingImports = financeAnalysisService.analyze(text).map((item) => ({
    ...item,
    included: item.bucket !== "transfer"
  }));
  state.analysisMessage = copy().analysisReady(state.pendingImports.length);
  state.activeScreen = "review";
  render();
}

function importAnalyzedTransactions(items) {
  let added = 0;
  let skipped = 0;

  items.filter((item) => item.included).forEach((item) => {
    const key = transactionKey(item);
    const exists = state.entries.some((entry) => entry.importKey === key);
    if (exists) {
      skipped += 1;
      return;
    }

    state.entries.unshift({
      id: uid(),
      title: item.title,
      amount: item.amount,
      kind: item.kind,
      bucket: item.bucket,
      currency: item.currency,
      date: item.date ?? todayKey(),
      recurring: false,
      source: item.institution,
      raw: item.raw,
      importKey: key
    });
    added += 1;
  });

  return { added, skipped };
}

function transactionKey(item) {
  return [item.institution, item.raw, item.amount, item.kind, item.currency].join("|");
}

async function readStatementFile(file) {
  const buffer = await file.arrayBuffer();
  const lowerName = file.name.toLowerCase();
  const isSpreadsheet = /\.(xls|xlsx)$/.test(lowerName);

  if (isSpreadsheet && globalThis.XLSX) {
    const workbook = globalThis.XLSX.read(buffer, { type: "array" });
    return workbook.SheetNames.map((sheetName) => {
      const sheet = workbook.Sheets[sheetName];
      return globalThis.XLSX.utils.sheet_to_csv(sheet, { FS: "\t", blankrows: false });
    }).join("\n");
  }

  const bytes = new Uint8Array(buffer);
  if (isSpreadsheet && isOleExcel(bytes)) {
    throw new Error(copy().xlsParserUnavailable);
  }

  return normalizeSpreadsheetText(decodeTextBuffer(buffer));
}

function isOleExcel(bytes) {
  return bytes.length > 8
    && bytes[0] === 0xd0
    && bytes[1] === 0xcf
    && bytes[2] === 0x11
    && bytes[3] === 0xe0;
}

function decodeTextBuffer(buffer) {
  const utf8 = new TextDecoder("utf-8", { fatal: false }).decode(buffer);
  try {
    const kr = new TextDecoder("euc-kr", { fatal: false }).decode(buffer);
    const utf8Noise = (utf8.match(/�/g) || []).length;
    const krNoise = (kr.match(/�/g) || []).length;
    return krNoise < utf8Noise ? kr : utf8;
  } catch {
    return utf8;
  }
}

function normalizeSpreadsheetText(text) {
  if (!/<table|<tr|<td|<th/i.test(text)) return text;
  return text
    .replace(/<\/tr>/gi, "\n")
    .replace(/<\/(td|th)>/gi, "\t")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\t+\n/g, "\n")
    .trim();
}

function drawCashChart(income, expenses, allocated) {
  const canvas = $("#cash-chart");
  const context = canvas.getContext("2d");
  const values = [
    [copy().income, income, "#176b5b"],
    [copy().expenses, expenses, "#c8643b"],
    [copy().allocated, allocated, "#334f7d"]
  ];
  const max = Math.max(...values.map((item) => item[1]), 1);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.font = "24px system-ui";
  values.forEach(([label, value, color], index) => {
    const x = 42 + index * 195;
    const height = Math.max(8, (value / max) * 150);
    context.fillStyle = color;
    context.fillRect(x, 190 - height, 112, height);
    context.fillStyle = "#15191d";
    context.fillText(label, x, 226);
    context.fillText(money(value), x, 34);
  });
}

function renderRoutine() {
  const keys = Object.keys(state.routine).filter((key) => typeof state.routine[key] === "boolean");
  const complete = keys.filter((key) => state.routine[key]).length;
  $("#routine-count").textContent = copy().completedOf(complete, keys.length);
  $("#routine-progress").value = complete;

  $$("[data-routine]").forEach((input) => {
    input.checked = Boolean(state.routine[input.dataset.routine]);
  });

  $$("[data-routine-text]").forEach((input) => {
    input.value = state.routine[input.dataset.routineText] ?? "";
  });
}

function renderPostIt() {
  $$(".segmented [data-asset]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.asset === state.assetKind);
  });

  $$(".status-strip button").forEach((button) => {
    button.classList.toggle("selected", button.dataset.status === state.ideaStatus);
    button.textContent = statusLabel(button.dataset.status);
  });

  $("#quote-list").innerHTML = marketService.quotes.map((quote) => `
    <div class="list-item">
      <div><strong>${quote.symbol}</strong><div class="muted">${quote.name}</div></div>
      <div><strong>${money(quote.price, "USD")}</strong><div class="${quote.change >= 0 ? "gain" : "loss"}">${quote.change.toFixed(1)}%</div></div>
    </div>
  `).join("");

  const ideas = state.ideas.filter((idea) => idea.status === state.ideaStatus);
  $("#idea-list").innerHTML = ideas.length ? ideas.map((idea) => ideaTemplate(idea)).join("") : `<div class="card muted">${copy().noIdeas(state.ideaStatus)}</div>`;
}

function ideaTemplate(idea) {
  const t = copy();
  const proposal = idea.proposal ? `
    <div class="proposal">
      <strong>${t.proposed(idea.proposal.amount)}</strong>
      <p class="muted">${escapeHtml(idea.proposal.rationale)}</p>
    </div>
  ` : "";

  const approve = idea.proposal && !idea.approved ? `<button class="primary" data-approve="${idea.id}" type="button">${t.approve}</button>` : "";

  return `
    <article class="idea-card">
      <div class="idea-head">
        <div>
          <h2>${escapeHtml(idea.title)}</h2>
          <p class="muted">${idea.asset === "crypto" ? t.crypto : t.stock} · ${escapeHtml(idea.symbol.toUpperCase())}</p>
        </div>
        <select data-move="${idea.id}" aria-label="${t.moveIdeaStatus}">
          ${STATUSES.map((status) => `<option value="${status}" ${status === idea.status ? "selected" : ""}>${statusLabel(status)}</option>`).join("")}
        </select>
      </div>
      <p>${escapeHtml(idea.note)}</p>
      ${idea.summary ? `<p class="muted">${escapeHtml(idea.summary)}</p>` : ""}
      ${proposal}
      <div class="idea-actions">
        <button data-summary="${idea.id}" type="button">${t.aiSummary}</button>
        ${approve}
      </div>
    </article>
  `;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[char]);
}

function bindEvents() {
  $$(".bottom-nav button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeScreen = button.dataset.screen;
      render();
    });
  });

  $("#reset-demo").addEventListener("click", () => {
    const language = state.language;
    const currency = state.currency;
    state = defaultState();
    state.language = language;
    state.currency = currency;
    render();
  });

  $$(".lang-switch button").forEach((button) => {
    button.addEventListener("click", () => {
      state.language = button.dataset.lang;
      render();
    });
  });

  $$(".currency-switch button").forEach((button) => {
    button.addEventListener("click", () => {
      state.currency = button.dataset.currency;
      render();
    });
  });

  $$(".segmented [data-kind]").forEach((button) => {
    button.addEventListener("click", () => {
      state.cashKind = button.dataset.kind;
      render();
    });
  });

  $$(".segmented [data-asset]").forEach((button) => {
    button.addEventListener("click", () => {
      state.assetKind = button.dataset.asset;
      render();
    });
  });

  $("#quick-income").addEventListener("click", () => addEntry("Paycheck", state.currency === "KRW" ? 2500000 : 2500, "income"));
  $("#quick-expense").addEventListener("click", () => addEntry("Bill", state.currency === "KRW" ? 120000 : 120, "expense"));
  $("#add-cash").addEventListener("click", () => {
    addEntry($("#cash-title").value || state.cashKind, Number($("#cash-amount").value || 0), state.cashKind);
    $("#cash-title").value = "";
    $("#cash-amount").value = "";
  });

  $("#budget-summary").addEventListener("click", (event) => {
    const button = event.target.closest("[data-budget-bucket]");
    if (!button) return;
    state.selectedBucket = button.dataset.budgetBucket;
    render();
  });

  $("#analyze-statement").addEventListener("click", () => {
    analyzeStatementText($("#statement-input").value.trim());
  });

  $("#statement-file").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await readStatementFile(file);
      $("#statement-input").value = text;
      analyzeStatementText(text);
    } catch (error) {
      state.pendingImports = [];
      state.analysisMessage = error?.message || copy().fileReadFailed;
      render();
    }
  });

  $("#import-analysis").addEventListener("click", () => {
    if (!state.pendingImports.length) {
      state.analysisMessage = copy().analysisNoReady;
      render();
      return;
    }

    state.activeScreen = "review";
    render();
  });

  $("#review-back").addEventListener("click", () => {
    state.activeScreen = "money";
    render();
  });

  $("#review-confirm").addEventListener("click", () => {
    if (!state.pendingImports.length) {
      state.analysisMessage = copy().analysisNoReady;
      state.activeScreen = "money";
      render();
      return;
    }

    const result = importAnalyzedTransactions(state.pendingImports);
    state.analysisMessage = copy().analysisAutoImported(result.added, result.skipped);
    state.pendingImports = [];
    $("#statement-input").value = "";
    $("#statement-file").value = "";
    state.activeScreen = "money";
    render();
  });

  $("#review-include-all").addEventListener("click", () => {
    state.pendingImports.forEach((item) => {
      item.included = true;
    });
    render();
  });

  $("#review-exclude-transfers").addEventListener("click", () => {
    state.pendingImports.forEach((item) => {
      item.included = item.bucket !== "transfer";
    });
    render();
  });

  $("#review-list").addEventListener("change", (event) => {
    const includeId = event.target.dataset.reviewInclude;
    const kindId = event.target.dataset.reviewKind;
    const bucketId = event.target.dataset.reviewBucket;
    const id = includeId || kindId || bucketId;
    if (!id) return;

    const item = state.pendingImports.find((candidate) => candidate.id === id);
    if (!item) return;

    if (includeId) {
      item.included = event.target.checked;
    }
    if (kindId) {
      item.kind = event.target.value;
      if (item.kind === "income") item.bucket = "income";
      if (item.kind === "transfer") item.bucket = "transfer";
      if (item.kind === "expense" && ["income", "transfer"].includes(item.bucket)) item.bucket = "discretionary";
    }
    if (bucketId) {
      item.bucket = event.target.value;
      item.kind = item.bucket === "income" ? "income" : item.bucket === "transfer" ? "transfer" : "expense";
      item.reason = reasonForBucket(item.bucket);
      item.included = item.bucket !== "transfer";
    }
    item.reason = reasonForBucket(item.bucket);
    render();
  });

  $("#add-allocation").addEventListener("click", () => {
    const symbol = $("#allocation-symbol").value.trim().toUpperCase();
    const amount = Number($("#allocation-amount").value || 0);
    if (!symbol || amount <= 0) return;
    state.allocations.unshift({ id: uid(), symbol, amount, currency: state.currency });
    $("#allocation-symbol").value = "";
    $("#allocation-amount").value = "";
    render();
  });

  $$("[data-routine]").forEach((input) => {
    input.addEventListener("change", () => {
      state.routine[input.dataset.routine] = input.checked;
      render();
    });
  });

  $$("[data-routine-text]").forEach((input) => {
    input.addEventListener("input", () => {
      state.routine[input.dataset.routineText] = input.value;
      saveState();
      renderRoutine();
    });
  });

  $("#save-idea").addEventListener("click", saveIdea);
  $("#voice-idea").addEventListener("click", startVoiceNote);

  $$(".status-strip button").forEach((button) => {
    button.addEventListener("click", () => {
      state.ideaStatus = button.dataset.status;
      render();
    });
  });

  $("#idea-list").addEventListener("click", async (event) => {
    const summaryId = event.target.dataset.summary;
    const approveId = event.target.dataset.approve;

    if (summaryId) {
      const idea = state.ideas.find((item) => item.id === summaryId);
      const { investable } = totals();
      idea.summary = await aiService.summarize(idea);
      idea.proposal = aiService.propose(idea, investable);
      render();
    }

    if (approveId) {
      const idea = state.ideas.find((item) => item.id === approveId);
      idea.approved = true;
      idea.status = "Portfolio";
      state.ideaStatus = "Portfolio";
      state.allocations.unshift({ id: uid(), symbol: idea.symbol.toUpperCase(), amount: idea.proposal.amount, currency: state.currency });
      render();
    }
  });

  $("#idea-list").addEventListener("change", (event) => {
    const moveId = event.target.dataset.move;
    if (!moveId) return;
    const idea = state.ideas.find((item) => item.id === moveId);
    idea.status = event.target.value;
    render();
  });
}

function addEntry(title, amount, kind, bucket = null) {
  if (!amount || amount <= 0) return;
  state.entries.unshift({
    id: uid(),
    title,
    amount,
    kind,
    currency: state.currency,
    date: todayKey(),
    bucket: bucket ?? (kind === "income" ? "income" : classifyBucket(title)),
    recurring: true
  });
  render();
}

function saveIdea() {
  const title = $("#idea-title").value.trim();
  const symbol = $("#idea-symbol").value.trim().toUpperCase();
  const note = $("#idea-note").value.trim();
  if (!title || !symbol) return;
  state.ideas.unshift({
    id: uid(),
    title,
    symbol,
    asset: state.assetKind,
    status: "Inbox",
    note,
    summary: "",
    proposal: null,
    approved: false
  });
  $("#idea-title").value = "";
  $("#idea-symbol").value = "";
  $("#idea-note").value = "";
  state.ideaStatus = "Inbox";
  render();
}

function startVoiceNote() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    $("#idea-note").value = copy().voiceFallback;
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = state.language === "ko" ? "ko-KR" : "en-US";
  recognition.interimResults = false;
  recognition.onresult = (event) => {
    $("#idea-note").value = event.results[0][0].transcript;
  };
  recognition.start();
}

bindEvents();
render();
loadRemoteState();
setInterval(refreshRemoteState, 10000);
marketService.refreshFromBackend()
  .then(() => render())
  .catch(() => {});
setInterval(() => {
  marketService.refreshFromBackend()
    .then(() => render())
    .catch(() => {});
}, 300000);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js");
}
