from typing import Type, Any
from crewai.tools import BaseTool
from firecrawl import Firecrawl
import feedparser
import requests
from pydantic import BaseModel, Field
from datetime import datetime
from time import mktime
import pytz
from env import (
    FIRECRAWL_API_KEY,
)


def _get_rss(rss_feeds: dict[str, str], each: int = 10):
    all_articles = []
    korea_tz = pytz.timezone("Asia/Seoul")
    today_korea = datetime.now(korea_tz).date()

    for source_name, feed_url in rss_feeds.items():
        try:
            response = requests.get(feed_url, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)

                for entry in feed.entries[:each]:
                    # published 날짜 파싱 및 한국 시간 기준으로 변환
                    published_date = None
                    
                    # 방법 1: published_parsed 사용
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            # published_parsed는 time.struct_time 형식
                            published_dt = datetime.fromtimestamp(
                                mktime(entry.published_parsed), tz=pytz.UTC
                            )
                            published_dt_korea = published_dt.astimezone(korea_tz)
                            published_date = published_dt_korea.date()
                        except Exception:
                            pass
                    
                    # 방법 2: published 문자열 직접 파싱 (방법 1 실패 시)
                    if published_date is None and hasattr(entry, "published") and entry.published:
                        try:
                            from dateutil import parser as date_parser
                            published_dt = date_parser.parse(entry.published)
                            # timezone 정보가 없으면 UTC로 가정
                            if published_dt.tzinfo is None:
                                published_dt = pytz.UTC.localize(published_dt)
                            published_dt_korea = published_dt.astimezone(korea_tz)
                            published_date = published_dt_korea.date()
                        except Exception:
                            pass
                    
                    # 방법 3: updated_parsed 사용 (published가 없을 경우)
                    if published_date is None and hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        try:
                            updated_dt = datetime.fromtimestamp(
                                mktime(entry.updated_parsed), tz=pytz.UTC
                            )
                            updated_dt_korea = updated_dt.astimezone(korea_tz)
                            published_date = updated_dt_korea.date()
                        except Exception:
                            pass

                    # 날짜 파싱 실패 시 해당 기사 제외 (오늘 날짜가 아니면 제외)
                    if published_date is None or published_date != today_korea:
                        continue

                    article = {
                        "title": getattr(entry, "title", "No Title"),
                        "link": getattr(entry, "link", ""),
                        "summary": getattr(entry, "summary", "No Summary"),
                        "published": getattr(entry, "published", ""),
                        "source": source_name,
                    }
                    all_articles.append(article)

        except Exception:
            continue

    return all_articles


class GlobalNewsRssToolInput(BaseModel):

    each: int = Field(
        default=10, description="Number of articles to fetch from each RSS feed."
    )


class GlobalNewsRssTool(BaseTool):
    name: str = "global_news_rss_tool"
    description: str = (
        "Global News RSS Tool. Collects news articles from major international RSS feeds. "
        "IMPORTANT: This tool automatically filters articles to only return news from today (Korea timezone). "
        "Only articles published today will be included in the results."
    )
    args_schema: Type[BaseModel] = GlobalNewsRssToolInput

    def _run(self, each: int = 10):
        global_rss_feeds = {
            "Google News": "https://news.google.com/rss/search?q=global",
            "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "CNN": "https://rss.cnn.com/rss/edition.rss",
        }

        return _get_rss(global_rss_feeds, each)


class KoreanNewsRssToolInput(BaseModel):

    each: int = Field(
        default=10, description="Number of articles to fetch from each RSS feed."
    )


class KoreanNewsRssTool(BaseTool):
    name: str = "korean_news_rss_tool"
    description: str = (
        "Korean News RSS Tool. Collects news articles from major Korean news outlets. "
        "IMPORTANT: This tool automatically filters articles to only return news from today (Korea timezone). "
        "Only articles published today will be included in the results."
    )
    args_schema: Type[BaseModel] = KoreanNewsRssToolInput

    def _run(self, each: int = 10):
        korean_rss_feeds = {
            "연합뉴스": "https://www.yna.co.kr/rss/news.xml",
            "조선일보": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
            "동아일보": "https://rss.donga.com/total.xml",
            "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
            "SBS": "https://news.sbs.co.kr/news/TopicRssFeed.do?plink=RSSREADER",
            "매일경제": "https://www.mk.co.kr/rss/30000001/",
            "한국경제": "https://www.hankyung.com/feed/all-news",
        }

        return _get_rss(korean_rss_feeds, each)


class WebSearchToolInput(BaseModel):

    url: str = Field(..., description="The URL to scrape content from.")


class WebSearchTool(BaseTool):
    name: str = "web_search_tool"
    description: str = (
        "Web Content Scraper Tool. This tool scrapes the content of a specific URL and returns it in text format. "
        "Returns a dictionary with 'title', 'url', and 'content' fields. "
        "Note: Google News redirect URLs may not work - use the actual article URL from the RSS feed when available."
    )
    args_schema: Type[BaseModel] = WebSearchToolInput

    def _run(self, url: str):
        try:
            app = Firecrawl(api_key=FIRECRAWL_API_KEY)

            response: Any = app.scrape(url)

            if not response:
                return f"Failed to scrape content from URL: {url}"

            title = "No Title"
            content = ""

            # Firecrawl v2: metadata는 DocumentMetadata 객체
            if hasattr(response, "metadata") and response.metadata:
                if hasattr(response.metadata, "title"):
                    title = response.metadata.title or "No Title"
                elif hasattr(response.metadata, "og_title"):
                    title = response.metadata.og_title or "No Title"

            # Firecrawl v2: markdown이 주요 콘텐츠
            if hasattr(response, "markdown") and response.markdown:
                content = response.markdown
            elif hasattr(response, "content") and response.content:
                content = response.content
            elif hasattr(response, "text") and response.text:
                content = response.text
            elif hasattr(response, "html") and response.html:
                content = response.html

            if not content:
                return f"Failed to extract content from URL: {url}"

            result = {"title": title, "url": url, "content": content}

            return result
        except Exception as e:
            return f"Error scraping URL {url}: {e}"


web_search_tool = WebSearchTool()
global_news_rss_tool = GlobalNewsRssTool()
korean_news_rss_tool = KoreanNewsRssTool()