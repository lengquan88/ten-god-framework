"""knowledge_sync.py — 知识库同步插件 v2.2.0

支持从 Wikipedia、百度百科、古籍数据库自动抓取知识。
"""
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, List, Optional, Tuple


class KnowledgeSyncPlugin:
    """知识库同步插件 — 从外部数据源自动抓取中华文明知识"""

    def __init__(self, kb=None):
        self._kb = kb
        self._sync_history: List[Dict] = []

    def set_knowledge_base(self, kb):
        self._kb = kb

    # ============ Wikipedia ============

    def sync_from_wikipedia(self, topics: List[str], language: str = "zh") -> Dict[str, Any]:
        """从 Wikipedia 同步知识

        Args:
            topics: 要同步的主题列表，如 ["儒家", "道家", "易经"]
            language: 语言代码，如 "zh"（中文）、"en"（英文）
        Returns:
            {"synced": int, "failed": int, "details": [...]}
        """
        results = {"synced": 0, "failed": 0, "details": []}

        for topic in topics:
            try:
                title, summary = self._fetch_wikipedia(topic, language)
                if title and summary and self._kb:
                    self._kb.add_node(
                        f"Wikipedia:{title}",
                        node_type="wikipedia",
                        properties={
                            "source": "Wikipedia",
                            "language": language,
                            "topic": topic,
                            "summary": summary[:500],
                            "url": f"https://{language}.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                            "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    )
                    results["synced"] += 1
                    results["details"].append({"topic": topic, "title": title, "status": "ok"})
                else:
                    results["failed"] += 1
                    results["details"].append({"topic": topic, "title": title, "status": "empty"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"topic": topic, "status": str(e)})

        self._sync_history.append({
            "source": "wikipedia",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        })
        return results

    def _fetch_wikipedia(self, topic: str, language: str = "zh") -> Tuple[Optional[str], Optional[str]]:
        """通过 Wikipedia API 获取摘要"""
        api_url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
            "titles": topic,
            "redirects": "1",
        }
        url = f"{api_url}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Tengod/2.2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    if page_id != "-1":
                        return page_info.get("title", topic), page_info.get("extract", "")
        except Exception:
            pass
        return None, None

    # ============ 百度百科 ============

    def sync_from_baidu_baike(self, topics: List[str]) -> Dict[str, Any]:
        """从百度百科同步知识（基于开放 API）"""
        results = {"synced": 0, "failed": 0, "details": []}

        for topic in topics:
            try:
                entry = self._fetch_baidu_baike(topic)
                if entry and self._kb:
                    self._kb.add_node(
                        f"百度百科:{topic}",
                        node_type="baidu_baike",
                        properties={
                            "source": "百度百科",
                            "topic": topic,
                            "summary": entry.get("abstract", "")[:500],
                            "url": entry.get("url", ""),
                            "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    )
                    results["synced"] += 1
                    results["details"].append({"topic": topic, "status": "ok"})
                else:
                    results["failed"] += 1
                    results["details"].append({"topic": topic, "status": "empty"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"topic": topic, "status": str(e)})

        self._sync_history.append({
            "source": "baidu_baike",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        })
        return results

    def _fetch_baidu_baike(self, topic: str) -> Optional[Dict]:
        """通过百度百科 API 获取词条"""
        url = f"https://baike.baidu.com/api/lemma?lemma_id=&lemma_title={urllib.parse.quote(topic)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Tengod/2.2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    # ============ 古籍数据库 ============

    def sync_from_classics(self, classics: Optional[List[str]] = None) -> Dict[str, Any]:
        """从古籍数据库同步知识

        支持的经典：易经、道德经、论语、孙子兵法、黄帝内经、诗经、史记
        """
        if classics is None:
            classics = ["易经", "道德经", "论语", "孙子兵法", "黄帝内经", "诗经", "史记"]

        results = {"synced": 0, "failed": 0, "details": []}

        classic_data = self._get_classic_data()

        for classic in classics:
            if classic in classic_data:
                info = classic_data[classic]
                if self._kb:
                    self._kb.add_node(
                        f"古籍:{classic}",
                        node_type="classic",
                        properties={
                            "source": "中华经典古籍库",
                            "title": classic,
                            "author": info.get("author", "不详"),
                            "dynasty": info.get("dynasty", "不详"),
                            "category": info.get("category", "不详"),
                            "summary": info.get("summary", ""),
                            "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    )
                    results["synced"] += 1
                    results["details"].append({"classic": classic, "status": "ok"})
            else:
                results["failed"] += 1
                results["details"].append({"classic": classic, "status": "not found"})

        self._sync_history.append({
            "source": "classics",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        })
        return results

    def _get_classic_data(self) -> Dict[str, Dict]:
        """内置古籍元数据"""
        return {
            "易经": {
                "author": "周文王/孔子",
                "dynasty": "周",
                "category": "哲学/占卜",
                "summary": "《易经》是中国最古老的经典之一，阐述阴阳变化之理，包含六十四卦和三百八十四爻。",
            },
            "道德经": {
                "author": "老子",
                "dynasty": "春秋",
                "category": "哲学",
                "summary": "道家核心经典，八十一章，阐述道法自然、无为而治的哲学思想。",
            },
            "论语": {
                "author": "孔子及弟子",
                "dynasty": "春秋",
                "category": "哲学",
                "summary": "儒家经典，记录孔子及其弟子的言行，是儒家思想的核心典籍。",
            },
            "孙子兵法": {
                "author": "孙武",
                "dynasty": "春秋",
                "category": "兵书",
                "summary": "中国现存最早的兵书，共十三篇，阐述军事战略和战术原则。",
            },
            "黄帝内经": {
                "author": "不详（托名黄帝）",
                "dynasty": "战国/汉",
                "category": "医学",
                "summary": "中医经典，分《素问》和《灵枢》两部分，奠定中医理论基础。",
            },
            "诗经": {
                "author": "不详（采集）",
                "dynasty": "周",
                "category": "文学",
                "summary": "中国最早的诗歌总集，收录305篇诗歌，分风、雅、颂三类。",
            },
            "史记": {
                "author": "司马迁",
                "dynasty": "汉",
                "category": "历史",
                "summary": "中国第一部纪传体通史，记载从黄帝到汉武帝三千余年的历史。",
            },
        }

    def sync_all(self) -> Dict[str, Any]:
        """一键同步所有数据源"""
        topics = ["儒家", "道家", "法家", "墨家", "易经", "阴阳", "五行", "八卦", "太极"]
        return {
            "wikipedia": self.sync_from_wikipedia(topics),
            "baidu_baike": self.sync_from_baidu_baike(topics),
            "classics": self.sync_from_classics(),
        }

    def get_history(self) -> List[Dict]:
        return self._sync_history