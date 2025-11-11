from typing import Type, Any
from crewai.tools import BaseTool
from firecrawl import Firecrawl
import feedparser
import requests
from pydantic import BaseModel, Field
from env import (
    FIRECRAWL_API_KEY,
)


def _get_rss(rss_feeds: dict[str, str], each: int = 10):
    all_articles = []

    for source_name, feed_url in rss_feeds.items():
        try:
            response = requests.get(feed_url, timeout=10)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)

                for entry in feed.entries[:each]:
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
        "Global News RSS Tool. Collects news articles from major international RSS feeds."
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
        "Korean News RSS Tool. Collects news articles from major Korean news outlets."
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
        "Web Content Scraper Tool. This tool scrapes the content of a specific URL and returns it in text format."
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

            if hasattr(response, "metadata") and response.metadata:
                title = response.metadata.get("title", "No Title")

            if hasattr(response, "content"):
                content = response.content
            elif hasattr(response, "text"):
                content = response.text
            elif hasattr(response, "markdown"):
                content = response.markdown

            result = {"title": title, "url": url, "content": content}

            return result
        except Exception as e:
            return f"Error scraping URL {url}: {e}"


web_search_tool = WebSearchTool()
global_news_rss_tool = GlobalNewsRssTool()
korean_news_rss_tool = KoreanNewsRssTool()