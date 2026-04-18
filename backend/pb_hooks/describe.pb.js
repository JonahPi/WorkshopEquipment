/// <reference path="../pb_data/types.d.ts" />

routerAdd("POST", "/api/describe", (e) => {
  const info = e.requestInfo();
  const image    = String(info.body["image"]      ?? "");
  const apiKey   = String(info.body["api_key"]    ?? "");
  const mimeType = String(info.body["media_type"] ?? "image/jpeg");

  if (!image || !apiKey) {
    return e.json(400, { error: "Missing image or api_key" });
  }

  const payload = {
    model: "claude-haiku-4-5-20251001",
    max_tokens: 300,
    messages: [{
      role: "user",
      content: [
        {
          type: "image",
          source: { type: "base64", media_type: mimeType, data: image },
        },
        {
          type: "text",
          text: "Describe the contents of this storage box in German. List the main items you can see. Be concise — 1 to 3 short sentences, no bullet points.",
        },
      ],
    }],
  };

  const res = $http.send({
    url:     "https://api.anthropic.com/v1/messages",
    method:  "POST",
    headers: {
      "x-api-key":         apiKey,
      "anthropic-version": "2023-06-01",
      "content-type":      "application/json",
    },
    body:    JSON.stringify(payload),
    timeout: 30,
  });

  if (res.statusCode !== 200) {
    return e.json(502, { error: "Claude API error", status: res.statusCode, detail: res.raw });
  }

  let result;
  try {
    result = res.json ?? JSON.parse(res.raw);
  } catch (_) {
    return e.json(502, { error: "Failed to parse Claude response", detail: res.raw });
  }

  const description = result?.content?.[0]?.text ?? "";
  if (!description) {
    return e.json(502, { error: "Empty response from Claude", detail: JSON.stringify(result) });
  }
  return e.json(200, { description });
});
