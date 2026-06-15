/** service-worker.js — 十神控制台 PWA Service Worker v2.3.0

支持离线缓存 + 推送通知 + 后台同步
*/
const CACHE_NAME = "tengod-console-v2.3.0";
const ASSETS_TO_CACHE = [
    "/web_console/",
    "/web_console/index.html",
    "/web_console/manifest.json",
    "/",
    "/health",
];

// 安装：预缓存核心资源
self.addEventListener("install", (event) => {
    console.log("[Tengod SW] Installing...");
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
                console.warn("[Tengod SW] Cache preload partial:", err);
            });
        })
    );
    self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener("activate", (event) => {
    console.log("[Tengod SW] Activating...");
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// 请求拦截：缓存优先，网络回退
self.addEventListener("fetch", (event) => {
    // 跳过 API 请求（不缓存动态数据）
    if (event.request.url.includes("/api/")) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            const fetchPromise = fetch(event.request)
                .then((response) => {
                    // 缓存成功的响应
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, clone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // 网络失败时返回缓存
                    return cached || new Response("Offline", { status: 503 });
                });

            return cached || fetchPromise;
        })
    );
});

// 推送通知
self.addEventListener("push", (event) => {
    const data = event.data ? event.data.json() : {};
    const options = {
        body: data.body || "十神架构通知",
        icon: "/web_console/icon-192.png",
        badge: "/web_console/icon-192.png",
        data: data.url || "/web_console/",
        vibrate: [200, 100, 200],
        actions: [
            { action: "open", title: "查看" },
            { action: "close", title: "关闭" },
        ],
    };
    event.waitUntil(
        self.registration.showNotification(data.title || "十神架构", options)
    );
});

// 通知点击
self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.action === "close") return;
    event.waitUntil(
        clients.matchAll({ type: "window" }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes("/web_console/") && "focus" in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow("/web_console/index.html");
            }
        })
    );
});

// 后台同步
self.addEventListener("sync", (event) => {
    if (event.tag === "sync-tengod-status") {
        event.waitUntil(syncStatus());
    }
});

async function syncStatus() {
    try {
        const resp = await fetch("/api/status");
        const data = await resp.json();
        // 存储状态到 IndexedDB
        console.log("[Tengod SW] Status synced:", data);
    } catch (e) {
        console.warn("[Tengod SW] Sync failed:", e);
    }
}