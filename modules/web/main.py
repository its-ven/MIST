from utils import install_dependencies
install_dependencies([("newspaper4k", None), ("duckduckgo_search", "5.3.1b1")])

from duckduckgo_search import DDGS
from api import response, make_schema, SchemaValue, append_to_history
from functions import register
from newspaper import Article
from core import Session

def _days_to_word(days: int):
    if days is None:
        return None
    else:
        if days <= 2:
            return "d"
        elif days <= 7:
            return "w"
        elif days <= 31:
            return "m"
        else:
            return "y"

@register("Performs a web search and upserts results to your memory. You can specify result recency as a number of days")
def web_search(search_query: str, recency_in_days: int = None):
        timelimit = _days_to_word(recency_in_days)
        max_results = 5
        links = DDGS().text(keywords=search_query, max_results=max_results, timelimit=timelimit)
        results = []
        for link in links:
            try:
                url = link["href"]
                article = Article(url)
                article.download()
                article.parse()
                article.nlp()
                results.append(f"From {article.url}\n\n{article.summary}")
            except:
                pass
        if results:
            Session.external_memory.add(results, )
            Session.add_event("Self", "Search results upserted to memory.")
            return results
        else:
            return "No results were found."