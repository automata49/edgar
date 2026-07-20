export default function handler(request, response) {
  response.status(200).json({
    answer: "",
    status: "disabled",
    note: "LLM processing is reserved for the Telegram bot backend."
  });
}
