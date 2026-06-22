/**
 * offline-store.js — 十神架构 PWA 离线存储层 v1.0.0
 *
 * 阶段十九 19.3：离线功能与数据同步
 *
 * 功能：
 *  - IndexedDB 封装（Promise 化 API）
 *  - 八字记录本地缓存（离线可查看）
 *  - 案例库本地缓存（离线可浏览）
 *  - 同步队列状态查询（与 SW 共享同一 IndexedDB）
 *  - 网络状态检测与回调
 *  - 离线写操作入队（与 SW 的 handleOfflineWrite 互补）
 *
 * 数据库结构：
 *  - bazi_records: 本地缓存的八字排盘记录
 *  - cases_cache: 本地缓存的命例案例
 *  - pending-ops: 离线写操作队列（与 SW 共享）
 *  - meta: 元数据（最后同步时间等）
 */

const DB_NAME = "tengod-offline";
const DB_VERSION = 1;
const STORES = {
  BAZI_RECORDS: "bazi_records",
  CASES_CACHE: "cases_cache",
  PENDING_OPS: "pending-ops", // 与 SW 共享
  META: "meta",
};

// ─── IndexedDB 封装 ─────────────────────────────────────

let _db = null;

function openDB() {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORES.BAZI_RECORDS)) {
        const store = db.createObjectStore(STORES.BAZI_RECORDS, { keyPath: "local_id", autoIncrement: true });
        store.createIndex("by_created", "created_at", { unique: false });
        store.createIndex("by_day_master", "day_master", { unique: false });
      }
      if (!db.objectStoreNames.contains(STORES.CASES_CACHE)) {
        const store = db.createObjectStore(STORES.CASES_CACHE, { keyPath: "id" });
        store.createIndex("by_category", "category", { unique: false });
        store.createIndex("by_cached", "cached_at", { unique: false });
      }
      if (!db.objectStoreNames.contains(STORES.PENDING_OPS)) {
        db.createObjectStore(STORES.PENDING_OPS, { keyPath: "id", autoIncrement: true });
      }
      if (!db.objectStoreNames.contains(STORES.META)) {
        db.createObjectStore(STORES.META, { keyPath: "key" });
      }
    };
    req.onsuccess = () => {
      _db = req.result;
      resolve(_db);
    };
    req.onerror = () => reject(req.error);
  });
}

function tx(storeName, mode = "readonly") {
  return openDB().then((db) => db.transaction(storeName, mode).objectStore(storeName));
}

function reqToPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ─── 八字记录缓存 ───────────────────────────────────────

const OfflineStore = {
  /**
   * 保存八字记录到本地缓存
   * @param {Object} record - 八字记录 { year, month, day, hour, gender, pillars, analysis, ... }
   * @returns {Promise<number>} local_id
   */
  async saveBaziRecord(record) {
    const store = await tx(STORES.BAZI_RECORDS, "readwrite");
    const data = {
      ...record,
      day_master: record.analysis?.day_master || record.day_master,
      created_at: Date.now(),
    };
    const req = store.add(data);
    return reqToPromise(req);
  },

  /**
   * 获取所有本地缓存的八字记录
   * @returns {Promise<Array>}
   */
  async listBaziRecords() {
    const store = await tx(STORES.BAZI_RECORDS);
    const req = store.getAll();
    const records = await reqToPromise(req);
    return records.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
  },

  /**
   * 获取单个八字记录
   * @param {number} localId
   * @returns {Promise<Object|null>}
   */
  async getBaziRecord(localId) {
    const store = await tx(STORES.BAZI_RECORDS);
    const req = store.get(localId);
    return reqToPromise(req);
  },

  /**
   * 删除本地八字记录
   * @param {number} localId
   * @returns {Promise<void>}
   */
  async deleteBaziRecord(localId) {
    const store = await tx(STORES.BAZI_RECORDS, "readwrite");
    store.delete(localId);
  },

  /**
   * 清空八字记录缓存
   * @returns {Promise<void>}
   */
  async clearBaziRecords() {
    const store = await tx(STORES.BAZI_RECORDS, "readwrite");
    store.clear();
  },

  // ─── 案例库缓存 ─────────────────────────────────────

  /**
   * 批量缓存案例（覆盖式）
   * @param {Array} cases
   * @returns {Promise<void>}
   */
  async cacheCases(cases) {
    const store = await tx(STORES.CASES_CACHE, "readwrite");
    const now = Date.now();
    cases.forEach((c) => {
      store.put({ ...c, cached_at: now });
    });
  },

  /**
   * 获取缓存的案例列表
   * @param {string|null} category - 可选分类筛选
   * @param {number} limit
   * @returns {Promise<Array>}
   */
  async listCachedCases(category = null, limit = 50) {
    const store = await tx(STORES.CASES_CACHE);
    if (category) {
      const index = store.index("by_category");
      const req = index.getAll(category);
      const cases = await reqToPromise(req);
      return cases.slice(0, limit);
    }
    const req = store.getAll();
    const cases = await reqToPromise(req);
    return cases.slice(0, limit);
  },

  /**
   * 获取单个缓存案例
   * @param {number} caseId
   * @returns {Promise<Object|null>}
   */
  async getCachedCase(caseId) {
    const store = await tx(STORES.CASES_CACHE);
    const req = store.get(caseId);
    return reqToPromise(req);
  },

  /**
   * 清空案例缓存
   * @returns {Promise<void>}
   */
  async clearCasesCache() {
    const store = await tx(STORES.CASES_CACHE, "readwrite");
    store.clear();
  },

  // ─── 同步队列 ───────────────────────────────────────

  /**
   * 获取待同步的操作数量
   * @returns {Promise<number>}
   */
  async getPendingOpsCount() {
    const store = await tx(STORES.PENDING_OPS);
    const req = store.count();
    return reqToPromise(req);
  },

  /**
   * 获取所有待同步操作
   * @returns {Promise<Array>}
   */
  async listPendingOps() {
    const store = await tx(STORES.PENDING_OPS);
    const req = store.getAll();
    return reqToPromise(req);
  },

  /**
   * 手动触发同步（如果支持 Background Sync）
   * @returns {Promise<boolean>}
   */
  async triggerSync() {
    if (!("serviceWorker" in navigator) || !navigator.serviceWorker.registration) {
      return false;
    }
    const reg = await navigator.serviceWorker.ready;
    if (reg.sync) {
      await reg.sync.register("tengod-sync");
      return true;
    }
    return false;
  },

  // ─── 元数据 ─────────────────────────────────────────

  /**
   * 设置元数据
   * @param {string} key
   * @param {any} value
   * @returns {Promise<void>}
   */
  async setMeta(key, value) {
    const store = await tx(STORES.META, "readwrite");
    store.put({ key, value, updated_at: Date.now() });
  },

  /**
   * 获取元数据
   * @param {string} key
   * @returns {Promise<any|null>}
   */
  async getMeta(key) {
    const store = await tx(STORES.META);
    const req = store.get(key);
    const result = await reqToPromise(req);
    return result ? result.value : null;
  },

  /**
   * 记录最后同步时间
   * @returns {Promise<void>}
   */
  async markSynced() {
    await this.setMeta("last_sync", Date.now());
  },

  /**
   * 获取最后同步时间
   * @returns {Promise<number|null>}
   */
  async getLastSync() {
    return this.getMeta("last_sync");
  },

  // ─── 网络状态 ───────────────────────────────────────

  /**
   * 当前是否在线
   * @returns {boolean}
   */
  isOnline() {
    return navigator.onLine;
  },

  /**
   * 注册网络状态变化回调
   * @param {(online: boolean) => void} callback
   * @returns {() => void} 取消注册函数
   */
  onNetworkChange(callback) {
    const onOnline = () => callback(true);
    const onOffline = () => callback(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  },

  // ─── 统计 ───────────────────────────────────────────

  /**
   * 获取离线存储统计信息
   * @returns {Promise<Object>}
   */
  async getStats() {
    const [records, cases, pending] = await Promise.all([
      this.listBaziRecords(),
      this.listCachedCases(),
      this.getPendingOpsCount(),
    ]);
    const lastSync = await this.getLastSync();
    return {
      bazi_records: records.length,
      cached_cases: cases.length,
      pending_ops: pending,
      last_sync: lastSync,
      online: this.isOnline(),
    };
  },
};

// 导出（支持 CommonJS 和浏览器全局）
if (typeof module !== "undefined" && module.exports) {
  module.exports = { OfflineStore, STORES };
}
if (typeof window !== "undefined") {
  window.OfflineStore = OfflineStore;
}
