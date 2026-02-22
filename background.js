const SERVER_URL = "http://127.0.0.1:8080/url";

function isHttpUrl(url) {
  return typeof url === "string" &&
    (url.startsWith("http://") || url.startsWith("https://"));
}

async function classify(tab) {
  if (!tab?.url || !isHttpUrl(tab.url)) return;

  const payload = {
    url:   tab.url,
    tabId: tab.id,
    title: tab.title ?? ""
  };

  console.log("[SENDING]", payload);

  try {
    const res = await fetch(SERVER_URL, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload)
    });

    if (!res.ok) {
      console.error("[SERVER ERROR]", res.status, await res.text());
      return;
    }

    const data = await res.json();
    const emoji = data.classification === "productive"   ? "✅" :
                  data.classification === "unproductive" ? "❌" : "❓";

    console.log(`${emoji} [${data.classification.toUpperCase()}]${data.cached ? " (cached)" : ""}  ${data.url}`);

  } catch (err) {
    console.error("[FETCH ERROR]", err.message);
  }
}

// Tab switched
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const tab = await chrome.tabs.get(tabId);
  classify(tab);
});

// Tab navigated (catches typing a new URL in the same tab)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    classify(tab);
  }
});

console.log("[background.js] loaded");