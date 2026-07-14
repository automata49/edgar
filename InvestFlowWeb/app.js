const STORAGE_KEY = "invest-flow-web-v1";
const STATUSES = ["Inbox", "Watch", "Candidate", "Rejected", "Portfolio"];

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
  }
};

const aiService = {
  summarize(idea) {
    const quote = marketService.quote(idea.symbol);
    const t = copy();
    if (state.language === "ko") {
      return `${t.thesis}: ${idea.note || t.noNoteYet} ${quote.symbol} ${t.mockedAt} ${money(quote.price)}, ${quote.change.toFixed(1)}% ${t.dayMove}. ${t.checkDownside}`;
    }
    return `${t.thesis}: ${idea.note || t.noNoteYet} ${quote.symbol} ${t.mockedAt} ${money(quote.price)} with a ${quote.change.toFixed(1)}% ${t.dayMove}. ${t.checkDownside}`;
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
  cashKind: "income",
  assetKind: "stock",
  ideaStatus: "Inbox",
  entries: [
    { id: uid(), title: "Salary", amount: 6200, kind: "income", recurring: true },
    { id: uid(), title: "Rent", amount: 2100, kind: "expense", recurring: true },
    { id: uid(), title: "Core bills", amount: 950, kind: "expense", recurring: true }
  ],
  allocations: [
    { id: uid(), symbol: "VOO", amount: 900 }
  ],
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
  const parsed = JSON.parse(saved);
  parsed.language = parsed.language ?? "en";
  if (parsed.routineDate !== todayKey()) {
    parsed.routineDate = todayKey();
    parsed.routine = defaultState().routine;
  }
  return parsed;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function money(value) {
  return Number(value || 0).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
}

function copy() {
  return i18n[state?.language === "ko" ? "ko" : "en"];
}

function statusLabel(status) {
  return copy().statuses[status] ?? status;
}

function totals() {
  const income = state.entries.filter((entry) => entry.kind === "income").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const expenses = state.entries.filter((entry) => entry.kind === "expense").reduce((sum, entry) => sum + Number(entry.amount), 0);
  const allocated = state.allocations.reduce((sum, allocation) => sum + Number(allocation.amount), 0);
  return { income, expenses, allocated, investable: income - expenses - allocated };
}

function render() {
  renderI18n();
  renderTabs();
  renderMoney();
  renderRoutine();
  renderPostIt();
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

  $$(".segmented [data-kind]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.kind === state.cashKind);
  });

  $("#allocation-list").innerHTML = state.allocations.map((allocation) => `
    <div class="list-item">
      <div><strong>${escapeHtml(allocation.symbol)}</strong><div class="muted">${copy().monthlyRecurring}</div></div>
      <strong>${money(allocation.amount)}</strong>
    </div>
  `).join("");

  drawCashChart(income, expenses, allocated);
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
      <div><strong>${money(quote.price)}</strong><div class="${quote.change >= 0 ? "gain" : "loss"}">${quote.change.toFixed(1)}%</div></div>
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
    state = defaultState();
    state.language = language;
    render();
  });

  $$(".lang-switch button").forEach((button) => {
    button.addEventListener("click", () => {
      state.language = button.dataset.lang;
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

  $("#quick-income").addEventListener("click", () => addEntry("Paycheck", 2500, "income"));
  $("#quick-expense").addEventListener("click", () => addEntry("Bill", 120, "expense"));
  $("#add-cash").addEventListener("click", () => {
    addEntry($("#cash-title").value || state.cashKind, Number($("#cash-amount").value || 0), state.cashKind);
    $("#cash-title").value = "";
    $("#cash-amount").value = "";
  });

  $("#add-allocation").addEventListener("click", () => {
    const symbol = $("#allocation-symbol").value.trim().toUpperCase();
    const amount = Number($("#allocation-amount").value || 0);
    if (!symbol || amount <= 0) return;
    state.allocations.unshift({ id: uid(), symbol, amount });
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

  $("#idea-list").addEventListener("click", (event) => {
    const summaryId = event.target.dataset.summary;
    const approveId = event.target.dataset.approve;

    if (summaryId) {
      const idea = state.ideas.find((item) => item.id === summaryId);
      const { investable } = totals();
      idea.summary = aiService.summarize(idea);
      idea.proposal = aiService.propose(idea, investable);
      render();
    }

    if (approveId) {
      const idea = state.ideas.find((item) => item.id === approveId);
      idea.approved = true;
      idea.status = "Portfolio";
      state.ideaStatus = "Portfolio";
      state.allocations.unshift({ id: uid(), symbol: idea.symbol.toUpperCase(), amount: idea.proposal.amount });
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

function addEntry(title, amount, kind) {
  if (!amount || amount <= 0) return;
  state.entries.unshift({ id: uid(), title, amount, kind, recurring: true });
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

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js");
}
