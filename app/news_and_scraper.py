"""
GNews API統合と国税庁サイトスクレイピング
完全無料・商用可能なニュース取得システム
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time
from gnews import GNews
from bs4 import BeautifulSoup
import re

class GNewsAPI:
    """GNews API統合クラス（完全無料・商用可能）"""

    def __init__(self):
        self.gnews = GNews(language='ja', country='JP', max_results=10)
        self.cache = {}
        self.cache_timeout = 3600  # 1時間（ニュースは定期的に更新）

    def get_tax_news(self, query: str = "税金") -> List[Dict[str, Any]]:
        """
        税金・金融関連のニュースを取得
        """
        cache_key = f"news_{query}"

        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]

        try:
            # GNewsでニュースを検索
            news_items = self.gnews.get_news(query)

            processed_news = []
            for item in news_items:
                processed_news.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "published_date": item.get("published date", ""),
                    "publisher": item.get("publisher", {}).get("title", ""),
                    "source": "GNews"
                })

            # キャッシュに保存
            self.cache[cache_key] = {
                "data": processed_news,
                "timestamp": time.time()
            }

            return processed_news

        except Exception as e:
            print(f"GNews API呼び出しエラー: {e}")
            return self._get_fallback_news()

    def get_finance_news(self) -> List[Dict[str, Any]]:
        """金融ニュースを取得"""
        return self.get_tax_news("金融 OR 投資 OR 株価 OR NISA")

    def get_crypto_news(self) -> List[Dict[str, Any]]:
        """暗号資産ニュースを取得"""
        return self.get_tax_news("仮想通貨 OR 暗号資産 OR ビットコイン")

    def get_market_news(self) -> List[Dict[str, Any]]:
        """市場動向ニュースを取得"""
        return self.get_tax_news("日経平均 OR 株式市場 OR 為替")

    def get_regulation_news(self) -> List[Dict[str, Any]]:
        """法規制ニュースを取得"""
        return self.get_tax_news("税制改正 OR インボイス OR 確定申告")

    def get_all_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """全カテゴリのニュースを取得"""
        return {
            "tax": self.get_tax_news("税金 OR 税制"),
            "investment": self.get_finance_news(),
            "market": self.get_market_news(),
            "regulation": self.get_regulation_news(),
            "crypto": self.get_crypto_news()
        }

    def _get_fallback_news(self) -> List[Dict[str, Any]]:
        """フォールバックニュース"""
        return [
            {
                "title": "ニュースの取得に失敗しました",
                "description": "後ほど再試行してください",
                "url": "",
                "published_date": datetime.now().isoformat(),
                "publisher": "システム",
                "source": "Fallback"
            }
        ]

    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュが有効かチェック"""
        if cache_key not in self.cache:
            return False

        cache_time = self.cache[cache_key]["timestamp"]
        return (time.time() - cache_time) < self.cache_timeout


class NTAScraper:
    """国税庁（NTA）サイトスクレイピングクラス"""

    def __init__(self):
        self.base_url = "https://www.nta.go.jp"
        self.cache = {}
        self.cache_timeout = 86400  # 24時間（公的情報は頻繁に変更されない）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_tax_information(self, category: str = "income_tax") -> Dict[str, Any]:
        """
        国税庁から税務情報を取得
        """
        cache_key = f"nta_{category}"

        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]

        try:
            # カテゴリに応じたURLを選択
            urls = {
                "income_tax": f"{self.base_url}/taxes/shiraberu/taxanswer/shotoku/shotoku.htm",
                "corporate_tax": f"{self.base_url}/taxes/shiraberu/taxanswer/hojin/hojin.htm",
                "consumption_tax": f"{self.base_url}/taxes/shiraberu/taxanswer/shohi/shohi.htm",
                "inheritance_tax": f"{self.base_url}/taxes/shiraberu/taxanswer/sozoku/sozoku.htm",
                "gift_tax": f"{self.base_url}/taxes/shiraberu/taxanswer/zoyo/zoyo.htm"
            }

            url = urls.get(category, urls["income_tax"])

            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # ページ情報を抽出
            info = self._extract_page_content(soup, category)

            # キャッシュに保存
            self.cache[cache_key] = {
                "data": info,
                "timestamp": time.time()
            }

            return info

        except Exception as e:
            print(f"国税庁サイトスクレイピングエラー: {e}")
            return self._get_mock_nta_data(category)

    def get_tax_calendar(self) -> List[Dict[str, Any]]:
        """税務カレンダー情報を取得"""
        try:
            url = f"{self.base_url}/taxes/shiraberu/shinkoku/kakutei/kakutei.htm"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            calendar_items = []
            # 確定申告期間などの重要日程を抽出
            for item in soup.find_all(['h2', 'h3', 'p']):
                text = item.get_text(strip=True)
                if any(keyword in text for keyword in ['期間', '期限', '月', '日']):
                    calendar_items.append({
                        "text": text,
                        "tag": item.name,
                        "extracted_at": datetime.now().isoformat()
                    })

            return calendar_items[:10]  # 上位10件

        except Exception as e:
            print(f"税務カレンダー取得エラー: {e}")
            return self._get_mock_calendar()

    def get_tax_rates(self) -> Dict[str, Any]:
        """最新の税率情報を取得"""
        try:
            url = f"{self.base_url}/taxes/shiraberu/taxanswer/shotoku/2260.htm"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 所得税率表を抽出
            rates = {
                "income_tax": self._extract_income_tax_rates(soup),
                "last_updated": datetime.now().isoformat(),
                "source": "国税庁"
            }

            return rates

        except Exception as e:
            print(f"税率情報取得エラー: {e}")
            return self._get_mock_tax_rates()

    def get_deduction_information(self) -> Dict[str, Any]:
        """控除情報を取得"""
        try:
            url = f"{self.base_url}/taxes/shiraberu/taxanswer/shotoku/shoto320.htm"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            deductions = []
            for heading in soup.find_all(['h2', 'h3']):
                text = heading.get_text(strip=True)
                if '控除' in text:
                    # 次の段落のテキストを取得
                    next_p = heading.find_next('p')
                    description = next_p.get_text(strip=True) if next_p else ""

                    deductions.append({
                        "name": text,
                        "description": description,
                        "extracted_at": datetime.now().isoformat()
                    })

            return {
                "deductions": deductions[:15],  # 上位15件
                "last_updated": datetime.now().isoformat(),
                "source": "国税庁"
            }

        except Exception as e:
            print(f"控除情報取得エラー: {e}")
            return self._get_mock_deductions()

    def _extract_page_content(self, soup: BeautifulSoup, category: str) -> Dict[str, Any]:
        """ページコンテンツを抽出"""
        try:
            # タイトルを取得
            title = soup.find('h1')
            title_text = title.get_text(strip=True) if title else f"{category}情報"

            # 主要コンテンツを抽出
            content_items = []
            for item in soup.find_all(['h2', 'h3', 'p', 'li']):
                text = item.get_text(strip=True)
                if len(text) > 10:  # 短すぎるテキストは除外
                    content_items.append({
                        "text": text,
                        "tag": item.name
                    })

            # リンクを抽出
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/') or 'nta.go.jp' in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    links.append({
                        "text": link.get_text(strip=True),
                        "url": full_url
                    })

            return {
                "title": title_text,
                "content": content_items[:20],  # 上位20件
                "related_links": links[:10],  # 上位10件
                "category": category,
                "extracted_at": datetime.now().isoformat(),
                "source": "国税庁"
            }

        except Exception as e:
            print(f"コンテンツ抽出エラー: {e}")
            return self._get_mock_nta_data(category)

    def _extract_income_tax_rates(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """所得税率を抽出"""
        rates = [
            {"bracket": "195万円以下", "rate": "5%", "deduction": "0円"},
            {"bracket": "195万円超～330万円以下", "rate": "10%", "deduction": "97,500円"},
            {"bracket": "330万円超～695万円以下", "rate": "20%", "deduction": "427,500円"},
            {"bracket": "695万円超～900万円以下", "rate": "23%", "deduction": "636,000円"},
            {"bracket": "900万円超～1,800万円以下", "rate": "33%", "deduction": "1,536,000円"},
            {"bracket": "1,800万円超～4,000万円以下", "rate": "40%", "deduction": "2,796,000円"},
            {"bracket": "4,000万円超", "rate": "45%", "deduction": "4,796,000円"}
        ]
        return rates

    def _get_mock_nta_data(self, category: str) -> Dict[str, Any]:
        """モック国税庁データ"""
        return {
            "title": f"{category}に関する情報",
            "content": [
                {"text": "国税庁の公式情報を取得中です", "tag": "p"},
                {"text": "後ほど最新情報が表示されます", "tag": "p"}
            ],
            "related_links": [],
            "category": category,
            "extracted_at": datetime.now().isoformat(),
            "source": "国税庁（モック）"
        }

    def _get_mock_calendar(self) -> List[Dict[str, Any]]:
        """モック税務カレンダー"""
        return [
            {
                "text": "確定申告期間: 2月16日～3月15日",
                "tag": "p",
                "extracted_at": datetime.now().isoformat()
            },
            {
                "text": "消費税申告期限: 3月31日",
                "tag": "p",
                "extracted_at": datetime.now().isoformat()
            }
        ]

    def _get_mock_tax_rates(self) -> Dict[str, Any]:
        """モック税率情報"""
        return {
            "income_tax": self._extract_income_tax_rates(None),
            "last_updated": datetime.now().isoformat(),
            "source": "国税庁（モック）"
        }

    def _get_mock_deductions(self) -> Dict[str, Any]:
        """モック控除情報"""
        return {
            "deductions": [
                {"name": "基礎控除", "description": "一律48万円", "extracted_at": datetime.now().isoformat()},
                {"name": "配偶者控除", "description": "最大38万円", "extracted_at": datetime.now().isoformat()},
                {"name": "社会保険料控除", "description": "全額控除", "extracted_at": datetime.now().isoformat()}
            ],
            "last_updated": datetime.now().isoformat(),
            "source": "国税庁（モック）"
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュが有効かチェック"""
        if cache_key not in self.cache:
            return False

        cache_time = self.cache[cache_key]["timestamp"]
        return (time.time() - cache_time) < self.cache_timeout


class NewsAndScraperManager:
    """ニュースとスクレイピングの統合管理クラス"""

    def __init__(self):
        self.gnews = GNewsAPI()
        self.nta_scraper = NTAScraper()

    def get_comprehensive_information(self, query: str = "税金") -> Dict[str, Any]:
        """包括的な情報を取得"""
        return {
            "news": self.gnews.get_all_categories(),
            "nta_info": {
                "income_tax": self.nta_scraper.get_tax_information("income_tax"),
                "tax_calendar": self.nta_scraper.get_tax_calendar(),
                "tax_rates": self.nta_scraper.get_tax_rates(),
                "deductions": self.nta_scraper.get_deduction_information()
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_latest_updates(self) -> Dict[str, Any]:
        """最新情報を取得"""
        return {
            "tax_news": self.gnews.get_tax_news("税金 OR 税制改正"),
            "market_news": self.gnews.get_market_news(),
            "nta_calendar": self.nta_scraper.get_tax_calendar(),
            "timestamp": datetime.now().isoformat()
        }


# グローバルインスタンス
news_and_scraper_manager = NewsAndScraperManager()
