/** service-worker.js — 十神控制台 PWA Service Worker v3.0.0
 *
 * 阶段十九升级：
 *  - 版本化缓存（自动清理旧版本）
 *  - 离线回退页
 *  - API 缓存策略（只读 GET 请求缓存，写请求走网络）
 *  - 后台同步队列（离线操作排队，联网后同步）
 *  - 缓存大小控制
 */
const SW_VERSION = "3.0.0";
const CACHE_NAME = `tengod-console-v${SW_VERSION}`;
const OFFLINE_URL = "/app/offline.html";

// 预缓存核心资源
const PRECACHE_URLS = [
    "/app/",
    "/app/index.html",
    "/app/manifest.json",
    "/app/offline.html",
    "/",
    "/api/health",
];

// API GET 请求缓存（短时缓存，提升离线体验）
const API_CACHE_NAME = `tengod-api-v${SW_VERSION}`;
const API_CACHE_TTL = 5 * 60 * 1000; // 5 分钟
const API_CACHEABLE_PATTERNS = [
    /\/api\/health/,
    /\/api\/stats/,
    /\/api\/knowledge\//,
    /\/api\/graph\//,
    /\/api\/cases$/,
    /\/api\/cases\/categories\/list/,
    /\/api\/cases\/tags\/list/,
    /\/api\/cases\/stats\/summary/,
    /\/api\/records$/,
];

// 后台同步队列（离线时存储写操作）
const SYNC_QUEUE_DB = "tengod-sync-queue";
const SYNC_QUEUE_STORE = "pending-ops";
const SYNC_TAG = "tengod-sync";

// ─── 工具函数 ───────────────────────────────────────────

/** 打开 IndexedDB */
function openIDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(SYNC_QUEUE_DB, 1);
        req.onupgradeneeded = () => {
            const db = req.result;
            if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
                db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: "id", autoIncrement: true });
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

/** 判断 URL 是否可缓存的 API GET 请求 */
function isCacheableAPI(url, method) {
    if (method !== "GET") return false;
    return API_CACHEABLE_PATTERNS.some((p) => p.test(url));
}

/** 缓存是否过期 */
function isCacheExpired(cached) {
    if (!cached || !cached.metadata) return true;
    return Date.now() - cached.metadata.timestamp > API_CACHE_TTL;
}

// ─── 安装：预缓存 ───────────────────────────────────────

self.addEventListener("install", (event) => {
    console.log(`[Tengod SW v${SW_VERSION}] Installing...`);
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) =>
            cache.addAll(PRECACHE_URLS).catch((err) => {
                console.warn("[Tengod SW] Precache partial:", err);
            })
        )
    );
    self.skipWaiting();
});

// ─── 激活：清理旧缓存 ───────────────────────────────────

self.addEventListener("activate", (event) => {
    console.log(`[Tengod SW v${SW_VERSION}] Activating...`);
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME && key !== API_CACHE_NAME)
                    .map((key) => {
                        console.log("[Tengod SW] Deleting old cache:", key);
                        return caches.delete(key);
                    })
            );
        })
    );
    self.clients.claim();
});

// ─── 请求拦截：分层缓存策略 ─────────────────────────────

self.addEventListener("fetch", (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // 非 GET 请求（写操作）：网络优先，失败时加入同步队列
    if (request.method !== "GET") {
        event.respondWith(writeWithQueue(request));
        return;
    }

    // 静态资源：缓存优先，网络回退
    if (url.pathname.startsWith("/app/") || url.pathname === "/") {
        event.respondWith(cacheFirst(request, OFFLINE_URL));
        return;
    }

    // 可缓存 API：stale-while-revalidate 策略
    if (isCacheableAPI(url.pathname, request.method)) {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }

    // 其他请求：网络优先，缓存回退
    event.respondWith(networkFirst(request));
});

/** 写请求处理：先尝试网络，失败时加入离线同步队列 */
async function writeWithQueue(request) {
    try {
        return await fetch(request);
    } catch (err) {
        // 网络失败，加入同步队列
        return handleOfflineWrite(request);
    }
}

/** 缓存优先策略（静态资源） */
async function cacheFirst(request, fallbackUrl) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const fallback = await caches.match(fallbackUrl);
        return fallback || new Response("Offline", { status: 503, statusText: "Offline" });
    }
}

/** Stale-While-Revalidate 策略（API GET） */
async function staleWhileRevalidate(request) {
    const cache = await caches.open(API_CACHE_NAME);
    const cached = await cache.match(request);

    const fetchPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                // 包装响应，附加时间戳元数据
                const responseClone = response.clone();
                const headers = new Headers(responseClone.headers);
                headers.set("x-cache-timestamp", Date.now().toString());
                const metaResponse = new Response(responseClone.body, {
                    status: responseClone.status,
                    statusText: responseClone.statusText,
                    headers,
                });
                cache.put(request, metaResponse);
            }
            return response;
        })
        .catch(() => cached);

    // 返回缓存（即使过期），同时后台更新
    return cached || fetchPromise;
}

/** 网络优先策略 */
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        return cached || new Response("Offline", { status: 503, statusText: "Offline" });
    }
}

/** 处理离线写请求：加入同步队列 */
async function handleOfflineWrite(request) {
    try {
        const body = await request.clone().text();
        const op = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: body || null,
            timestamp: Date.now(),
        };
        const db = await openIDB();
        await new Promise((resolve, reject) => {
            const tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
            tx.objectStore(SYNC_QUEUE_STORE).add(op);
            tx.oncomplete = resolve;
            tx.onerror = () => reject(tx.error);
        });
        // 注册后台同步
        if (self.registration && self.registration.sync) {
            await self.registration.sync.register(SYNC_TAG);
        }
        return new Response(
            JSON.stringify({ queued: true, message: "操作已加入离线同步队列" }),
            { status: 202, headers: { "Content-Type": "application/json" } }
        );
    } catch (e) {
        console.error("[Tengod SW] Queue write failed:", e);
        return new Response(JSON.stringify({ error: "离线存储失败" }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
        });
    }
}

// ─── 推送通知 ───────────────────────────────────────────

self.addEventListener("push", (event) => {
    const data = event.data ? event.data.json() : {};
    const options = {
        body: data.body || "十神架构通知",
        icon: "/app/icon-192.png",
        badge: "/app/icon-192.png",
        data: data.url || "/app/index.html",
        vibrate: [200, 100, 200],
        actions: [
            { action: "open", title: "查看" },
            { action: "close", title: "关闭" },
        ],
    };
    event.waitUntil(self.registration.showNotification(data.title || "十神架构", options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.action === "close") return;
    event.waitUntil(
        clients.matchAll({ type: "window" }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes("/app/") && "focus" in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data || "/app/index.html");
            }
        })
    );
});

// ─── 后台同步 ───────────────────────────────────────────

self.addEventListener("sync", (event) => {
    if (event.tag === SYNC_TAG) {
        event.waitUntil(processSyncQueue());
    }
});

/** 处理同步队列中的离线操作 */
async function processSyncQueue() {
    let db;
    try {
        db = await openIDB();
        const ops = await new Promise((resolve, reject) => {
            const tx = db.transaction(SYNC_QUEUE_STORE, "readonly");
            const req = tx.objectStore(SYNC_QUEUE_STORE).getAll();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });

        const successIds = [];
        for (const op of ops) {
            try {
                const response = await fetch(op.url, {
                    method: op.method,
                    headers: op.headers,
                    body: op.body,
                });
                if (response.ok) {
                    successIds.push(op.id);
                    console.log("[Tengod SW] Synced op:", op.id);
                } else {
                    console.warn("[Tengod SW] Sync failed for op", op.id, response.status);
                }
            } catch (e) {
                console.warn("[Tengod SW] Sync error for op", op.id, e);
                break; // 网络仍不可用，停止处理
            }
        }

        // 删除已同步的操作
        if (successIds.length) {
            await new Promise((resolve, reject) => {
                const tx = db.transaction(SYNC_QUEUE_STORE, "readwrite");
                successIds.forEach((id) => tx.objectStore(SYNC_QUEUE_STORE).delete(id));
                tx.oncomplete = resolve;
                tx.onerror = () => reject(tx.error);
            });
        }

        // 通知客户端同步完成
        const clientList = await clients.matchAll({ type: "window" });
        clientList.forEach((client) =>
            client.postMessage({ type: "sync-complete", synced: successIds.length })
        );
    } catch (e) {
        console.error("[Tengod SW] Process sync queue failed:", e);
    }
}

// ─── 消息通信 ───────────────────────────────────────────

self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
    if (event.data && event.data.type === "GET_VERSION") {
        event.ports[0].postMessage({ version: SW_VERSION });
    }
    if (event.data && event.data.type === "GET_QUEUE_SIZE") {
        openIDB()
            .then((db) =>
                new Promise((resolve) => {
                    const tx = db.transaction(SYNC_QUEUE_STORE, "readonly");
                    const req = tx.objectStore(SYNC_QUEUE_STORE).count();
                    req.onsuccess = () => resolve(req.result);
                    req.onerror = () => resolve(0);
                })
            )
            .then((count) => {
                event.ports[0].postMessage({ queueSize: count });
            });
    }
});
