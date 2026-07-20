const DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";
const ALLOWED_KINDS = new Set(["income", "expense", "transfer"]);
const ALLOWED_BUCKETS = new Set(["essential", "discretionary", "investing", "income", "transfer"]);
const ALLOWED_EXPENSE_CATEGORIES = new Set([
  "groceries", "utilities", "fuel_transport", "housing", "healthcare", "insurance", "education", "loan_interest",
  "dining", "shopping", "entertainment", "travel", "subscriptions", "savings_investments", "debt_principal", "other"
]);

export const config = { maxDuration: 60 };

function cleanTransaction(item) {
  return {
    id: String(item?.id || "").slice(0, 100),
    title: String(item?.title || "Transaction").slice(0, 120),
    amount: Math.abs(Number(item?.amount || 0)),
    kind: ALLOWED_KINDS.has(item?.kind) ? item.kind : "expense",
    bucket: ALLOWED_BUCKETS.has(item?.bucket) ? item.bucket : "discretionary",
    expenseCategory: ALLOWED_EXPENSE_CATEGORIES.has(item?.expenseCategory) ? item.expenseCategory : "other",
    currency: item?.currency === "USD" ? "USD" : "KRW",
    date: String(item?.date || "").slice(0, 10),
    institution: String(item?.institution || "Manual paste").slice(0, 80),
    raw: String(item?.raw || "").slice(0, 500)
  };
}

function validDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`));
}

function normalizeResult(originals, result) {
  const byId = new Map(originals.map((item) => [item.id, item]));
  const seenIds = new Set();
  const transactions = [];
  for (const proposed of Array.isArray(result?.transactions) ? result.transactions : []) {
    const original = byId.get(String(proposed?.id || ""));
    if (!original || seenIds.has(original.id) || proposed?.duplicate === true) continue;
    const kind = ALLOWED_KINDS.has(proposed.kind) ? proposed.kind : original.kind;
    let bucket = ALLOWED_BUCKETS.has(proposed.bucket) ? proposed.bucket : original.bucket;
    if (kind === "income") bucket = "income";
    if (kind === "transfer") bucket = "transfer";
    if (kind === "expense" && ["income", "transfer"].includes(bucket)) bucket = "discretionary";
    transactions.push({
      ...original,
      title: String(proposed.title || original.title).trim().slice(0, 120) || original.title,
      amount: Number(proposed.amount) > 0 ? Math.abs(Number(proposed.amount)) : original.amount,
      date: validDate(String(proposed.date || "")) ? proposed.date : original.date,
      kind,
      bucket,
      expenseCategory: kind === "expense" && ALLOWED_EXPENSE_CATEGORIES.has(proposed.expenseCategory)
        ? proposed.expenseCategory
        : original.expenseCategory,
      reason: String(proposed.reason || "DeepSeek verified").slice(0, 180),
      included: kind !== "transfer"
    });
    seenIds.add(original.id);
  }
  return transactions;
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "POST,OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (request.method === "OPTIONS") return response.status(204).end();
  if (request.method !== "POST") return response.status(405).json({ error: "Method not allowed" });

  try {
    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (!apiKey) return response.status(503).json({ error: "DEEPSEEK_API_KEY is not configured" });
    const body = typeof request.body === "string" ? JSON.parse(request.body || "{}") : request.body || {};
    const transactions = (Array.isArray(body.transactions) ? body.transactions : []).slice(0, 150).map(cleanTransaction).filter((item) => item.id && item.amount > 0);
    const existing = (Array.isArray(body.existing_transactions) ? body.existing_transactions : []).slice(0, 500).map(cleanTransaction);
    const classificationRules = (Array.isArray(body.classification_rules) ? body.classification_rules : []).slice(0, 200)
      .filter((rule) => ALLOWED_BUCKETS.has(rule?.bucket) && ALLOWED_EXPENSE_CATEGORIES.has(rule?.expenseCategory))
      .map((rule) => ({
        title: String(rule.title || "").slice(0, 120),
        bucket: rule.bucket,
        expenseCategory: rule.expenseCategory
      }));
    if (!transactions.length) return response.status(400).json({ error: "No valid transactions" });

    const prompt = `Validate Korean/English bank and card transactions for a 50-30-20 budget.
Return JSON only: {"transactions":[{"id":"input id","title":"merchant","amount":123,"date":"YYYY-MM-DD","kind":"income|expense|transfer","bucket":"essential|discretionary|investing|income|transfer","expenseCategory":"category code","reason":"short reason","duplicate":false}]}.
Keep every unique input id exactly once. Mark duplicate=true for repeated transactions within input or transactions already present in existing_transactions. A duplicate requires the same real-world transaction (date, amount, merchant/institution and direction); similar recurring purchases on different dates are not duplicates. Correct obvious merchant/date/type/category parsing errors, but never invent a transaction or change a plausible amount. Internal account transfers and card-bill payments are transfer. Income uses income bucket; transfer uses transfer bucket. Housing, utilities, groceries, medical, insurance, transit and necessary education are essential. Lifestyle, dining, shopping, entertainment and travel are discretionary. Savings, debt principal and securities purchases are investing.
For every expense choose exactly one expenseCategory: groceries (food ingredients/supermarkets), utilities (electricity/gas/water/management fees), fuel_transport (fuel/transit/taxi/tolls), housing, healthcare, insurance, education, loan_interest, dining, shopping, entertainment, travel, subscriptions, savings_investments, debt_principal, or other. Loan interest is an essential expense; debt principal is investing. For income/transfer use other.
USER_CLASSIFICATION_RULES are prior explicit corrections and have priority when the merchant/title clearly matches. Do not apply a rule to an unrelated merchant.
USER_CLASSIFICATION_RULES=${JSON.stringify(classificationRules)}
INPUT=${JSON.stringify(transactions)}
EXISTING_TRANSACTIONS=${JSON.stringify(existing)}`;

    const model = process.env.DEEPSEEK_MODEL || "deepseek-v4-flash";
    const deepseekResponse = await fetch(DEEPSEEK_URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: "You are a precise financial transaction validator. Produce JSON only." },
          { role: "user", content: prompt }
        ],
        response_format: { type: "json_object" },
        thinking: { type: "disabled" },
        temperature: 0,
        max_tokens: 12000
      })
    });
    const payload = await deepseekResponse.json();
    if (!deepseekResponse.ok) throw new Error(payload?.error?.message || "DeepSeek request failed");
    const parsed = JSON.parse(payload?.choices?.[0]?.message?.content || "{}");
    const verified = normalizeResult(transactions, parsed);
    response.status(200).json({
      status: "ok",
      model,
      transactions: verified,
      duplicates_removed: transactions.length - verified.length
    });
  } catch (error) {
    response.status(502).json({ error: error.message || String(error) });
  }
}
