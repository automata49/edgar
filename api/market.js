const lightweightMarketData = {
  SPY: { price: 0, change: 0, change_percent: 0, previous_close: 0 },
  QQQ: { price: 0, change: 0, change_percent: 0, previous_close: 0 },
  BTC: { price: 0, change: 0, change_percent: 0, previous_close: 0 },
  ETH: { price: 0, change: 0, change_percent: 0, previous_close: 0 }
};

export default function handler(request, response) {
  response.status(200).json({
    updated_at: new Date().toISOString(),
    data: lightweightMarketData,
    status: "mock",
    note: "Live market collection is reserved for the Telegram bot backend."
  });
}
