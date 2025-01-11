from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import pandas as pd
from tavily import TavilyClient

class SentimentAgent:
    def __init__(self, timeframe, tavily_api_key, model="gpt-4"):
        self.timeframe = timeframe  # '30d', '15d', or '3d'
        self.tavily_client = TavilyClient(api_key=tavily_api_key)
        self.chat_model = ChatOpenAI(model=model)
        
    def analyze_sentiment(self, symbol):
        # Fetch news articles using Tavily
        news_data = self._fetch_news(symbol)
        
        # Analyze sentiment using LLM
        system_prompt = self._get_system_prompt()
        news_context = self._prepare_news_context(news_data)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=news_context)
        ]
        
        response = self.chat_model(messages)
        return self._parse_response(response.content, news_data)
    
    def _fetch_news(self, symbol):
        query = f"{symbol} stock news last {self.timeframe}"
        search_results = self.tavily_client.search(
            query=query,
            search_depth="advanced",
            include_domains=["reuters.com", "bloomberg.com", "seekingalpha.com", "fool.com"]
        )
        return search_results
    
    def _get_system_prompt(self):
        return f"""
        You are a financial news sentiment analyzer focusing on {self.timeframe} trends.
        Analyze the provided news articles and provide:
        1. Overall sentiment score (-1 to 1)
        2. Key themes and topics
        3. Notable events or announcements
        4. Potential market impact
        5. Risk factors
        
        Consider:
        - Article source credibility
        - Publication timing
        - Market reaction to news
        - Sentiment consistency across sources
        """
    
    def _prepare_news_context(self, news_data):
        news_summary = "\n".join([
            f"Title: {article['title']}\n"
            f"Source: {article['source']}\n"
            f"Date: {article['date']}\n"
            f"Summary: {article['snippet']}\n"
            for article in news_data
        ])
        
        return f"""
        News Analysis for past {self.timeframe}:
        
        {news_summary}
        
        Please analyze the sentiment and potential market impact of these articles.
        """
    
    def _parse_response(self, response, news_data):
        return {
            'timeframe': self.timeframe,
            'analysis': response,
            'news_count': len(news_data),
            'timestamp': pd.Timestamp.now()
        }
