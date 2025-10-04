// Service Worker for Unloq PWA
const CACHE_NAME = 'unloq-v1.0.0';
const STATIC_CACHE_NAME = 'unloq-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'unloq-dynamic-v1.0.0';

// キャッシュするリソース
const STATIC_ASSETS = [
  '/',
  '/static/unloq_professional.html',
  '/static/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest/dist/umd/lucide.js',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

// API エンドポイント
const API_ENDPOINTS = [
  '/stats',
  '/external-apis/status',
  '/news',
  '/health',
  '/api/suggestions'
];

// インストール時の処理
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker: Static assets cached');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Service Worker: Failed to cache static assets', error);
      })
  );
});

// アクティベート時の処理
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
              console.log('Service Worker: Deleting old cache', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Activated');
        return self.clients.claim();
      })
  );
});

// フェッチ時の処理
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // HTML リクエストの処理
  if (request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // ネットワークから取得できた場合
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE_NAME)
            .then(cache => cache.put(request, responseClone));
          return response;
        })
        .catch(() => {
          // ネットワークエラーの場合、キャッシュから返す
          return caches.match(request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // オフラインページを返す
              return caches.match('/');
            });
        })
    );
    return;
  }
  
  // API リクエストの処理
  if (url.pathname.startsWith('/api/') || API_ENDPOINTS.includes(url.pathname)) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // 成功した場合、キャッシュに保存
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE_NAME)
              .then(cache => cache.put(request, responseClone));
          }
          return response;
        })
        .catch(() => {
          // ネットワークエラーの場合、キャッシュから返す
          return caches.match(request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // オフライン用のレスポンスを返す
              return new Response(
                JSON.stringify({
                  error: 'オフラインです',
                  message: 'インターネット接続を確認してください',
                  offline: true
                }),
                {
                  status: 503,
                  statusText: 'Service Unavailable',
                  headers: { 'Content-Type': 'application/json' }
                }
              );
            });
        })
    );
    return;
  }
  
  // 静的リソースの処理
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        return fetch(request)
          .then(response => {
            // 成功した場合、キャッシュに保存
            if (response.ok) {
              const responseClone = response.clone();
              caches.open(DYNAMIC_CACHE_NAME)
                .then(cache => cache.put(request, responseClone));
            }
            return response;
          });
      })
  );
});

// バックグラウンド同期
self.addEventListener('sync', event => {
  console.log('Service Worker: Background sync', event.tag);
  
  if (event.tag === 'background-sync') {
    event.waitUntil(
      // バックグラウンドでデータを同期
      syncData()
    );
  }
});

// プッシュ通知
self.addEventListener('push', event => {
  console.log('Service Worker: Push received');
  
  const options = {
    body: event.data ? event.data.text() : 'Unloqから新しい通知があります',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: '開く',
        icon: '/static/icons/action-explore.png'
      },
      {
        action: 'close',
        title: '閉じる',
        icon: '/static/icons/action-close.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Unloq', options)
  );
});

// 通知クリック処理
self.addEventListener('notificationclick', event => {
  console.log('Service Worker: Notification clicked');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// メッセージ処理
self.addEventListener('message', event => {
  console.log('Service Worker: Message received', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});

// データ同期関数
async function syncData() {
  try {
    // 統計データを更新
    const statsResponse = await fetch('/stats');
    if (statsResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      await cache.put('/stats', statsResponse.clone());
    }
    
    // システム状況を更新
    const statusResponse = await fetch('/external-apis/status');
    if (statusResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      await cache.put('/external-apis/status', statusResponse.clone());
    }
    
    console.log('Service Worker: Data synced successfully');
  } catch (error) {
    console.error('Service Worker: Sync failed', error);
  }
}

// エラーハンドリング
self.addEventListener('error', event => {
  console.error('Service Worker: Error occurred', event.error);
});

self.addEventListener('unhandledrejection', event => {
  console.error('Service Worker: Unhandled promise rejection', event.reason);
});

// 定期的なキャッシュクリーンアップ
setInterval(() => {
  caches.open(DYNAMIC_CACHE_NAME)
    .then(cache => {
      return cache.keys();
    })
    .then(keys => {
      // 古いキャッシュエントリを削除（24時間以上古い）
      const now = Date.now();
      const maxAge = 24 * 60 * 60 * 1000; // 24時間
      
      return Promise.all(
        keys.map(request => {
          return cache.match(request)
            .then(response => {
              if (response) {
                const dateHeader = response.headers.get('date');
                if (dateHeader) {
                  const responseDate = new Date(dateHeader).getTime();
                  if (now - responseDate > maxAge) {
                    return cache.delete(request);
                  }
                }
              }
            });
        })
      );
    })
    .catch(error => {
      console.error('Service Worker: Cache cleanup failed', error);
    });
}, 60 * 60 * 1000); // 1時間ごと
