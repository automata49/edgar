export default function handler(request, response) {
  response.status(200).json({
    ok: true,
    frontend: "vercel",
    mode: "lightweight",
    supabase_state: "/api/investflow/state",
    heavy_jobs: "telegram-bot-only"
  });
}
