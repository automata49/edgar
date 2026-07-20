const table = "invest_flow_states";

function supabaseConfig() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY || process.env.SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error("Supabase is not configured");
  }
  return { url: url.replace(/\/$/, ""), key };
}

async function supabaseRequest(path, options = {}) {
  const { url, key } = supabaseConfig();
  const response = await fetch(`${url}/rest/v1/${path}`, {
    ...options,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(typeof payload === "string" ? payload : JSON.stringify(payload));
  }
  return payload;
}

async function getState(familyId) {
  const encoded = encodeURIComponent(familyId);
  const rows = await supabaseRequest(
    `${table}?family_id=eq.${encoded}&select=family_id,payload,updated_at&limit=1`
  );
  return Array.isArray(rows) && rows.length ? rows[0] : null;
}

async function saveState(familyId, payload) {
  const rows = await supabaseRequest(`${table}?on_conflict=family_id`, {
    method: "POST",
    body: JSON.stringify({ family_id: familyId, payload: payload || {} })
  });
  return Array.isArray(rows) && rows.length ? rows[0] : {};
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (request.method === "OPTIONS") {
    response.status(204).end();
    return;
  }

  try {
    if (request.method === "GET") {
      const familyId = String(request.query.family_id || "family");
      const state = await getState(familyId);
      response.status(200).json({
        found: Boolean(state),
        family_id: familyId,
        payload: state ? state.payload : null,
        updated_at: state ? state.updated_at : null
      });
      return;
    }

    if (request.method === "POST") {
      const body = typeof request.body === "string" ? JSON.parse(request.body || "{}") : request.body || {};
      const familyId = String(body.family_id || "family");
      const saved = await saveState(familyId, body.payload || {});
      response.status(200).json({
        ok: true,
        family_id: familyId,
        updated_at: saved.updated_at || null
      });
      return;
    }

    response.status(405).json({ error: "Method not allowed" });
  } catch (error) {
    response.status(502).json({ error: error.message || String(error) });
  }
}
