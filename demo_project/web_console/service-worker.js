/* =============================================================================
 * Service Worker — TenGod PWA v2.3.0
 * 离线缓存 + 资源预缓存 + 运行时缓存策略
 * ========================================================================== */

const CACHE_VERSION = 'tengod-v2.3.0';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;

// 预缓存静态资源
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/icons/icon-192.svg',
    '/icons/icon-512.svg',
];

// 安装：预缓存静态资源
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        }).then(() => {
            self.skipWaiting();
        })
    );
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name.startsWith('tengod-') && name !== STATIC_CACHE && name !== RUNTIME_CACHE)
                    .map((name) => caches.delete(name))
            );
        }).then(() => {
            self.clients.claim();
        })
    );
});

// 拦截请求：不同资源不同策略
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // 只缓存 GET 请求
    if (request.method !== 'GET') return;

    // 跳过跨域请求（如第三方 CDN、Deepseek API）
    if (url.origin !== self.location.origin) return;

    // HTML 页面：网络优先，失败回退缓存
    if (request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
        event.respondWith(networkFirst(request));
        return;
    }

    // API 请求：网络优先，不缓存
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(request).catch(() => {
            return new Response(JSON.stringify({ error: 'offline' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            });
        }));
        return;
    }

    // 静态资源：缓存优先，失败回退网络
    event.respondWith(cacheFirst(request));
});

// 网络优先策略
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        const cache = await caches.open(RUNTIME_CACHE);
        cache.put(request, response.clone());
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        if (cached) return cached;
        // 返回离线页面
        return new Response('<html><body style="background:#0a0a0f;color:#f1c07c;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:serif;"><div style="text-align:center;"><div style="font-size:48px;margin-bottom:20px;">☯</div><div style="font-size:18px;">网络离线，请检查连接</div></div></body></html>', {
            status: 200,
            headers: { 'Content-Type': 'text/html;charset=utf-8' }
        });
    }
}

// 缓存优先策略
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        const cache = await caches.open(RUNTIME_CACHE);
        cache.put(request, response.clone());
        return response;
    } catch (err) {
        return Response.error();
    }
}

// 监听消息
self.addEventListener('message', (event) => {
    if (event.data === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
