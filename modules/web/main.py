from utils import install_dependencies
install_dependencies([("newspaper4k", None), ("duckduckgo_search", "5.3.1b1")])

from duckduckgo_search import DDGS
from api import response, make_schema, SchemaValue, append_to_history
import threading
from functions import register
from newspaper import Article
from core import Session

timeout = 60
timeout_thread = None

def _timed_out():
    global timeout_thread
    if timeout_thread is None:
        return False
    if not timeout_thread.is_alive():
        return False
    else:
        return True

def _start_timeout():
    global timeout_thread
    timer = threading.Timer(timeout, lambda: None)
    timer.start()
    timeout_thread = timer

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

@register("Perform a web search query. You can specify result recency as a number of days")
def web_search(query: str, recency_in_days: int = None):
    if not _timed_out():
        timelimit = _days_to_word(recency_in_days)
        max_results = 1
        links = DDGS().text(keywords=query, max_results=max_results, timelimit=timelimit)
        agent_history = []
        relevant_links = []
        for link in links:
            title = link["title"]
            prompt = f"Website title: \"{title}\""
            relevancy_agent = response(
                system=f"""
                    You are a JSON boolean emitter. You are given a partial title to a website.
                    Set the boolean to True if website title **is relevant** to the following query: "{query}"
                    Otherwise, set boolean to False.
                """,
                prompt=prompt,
                history=agent_history,
                temperature=0.5,
                top_p=0.2,
                json_schema=make_schema(is_relevant=SchemaValue.boolean)
            )
            is_relevant = relevancy_agent["is_relevant"]
            if is_relevant:
                relevant_links.append(link)
            append_to_history(agent_history, "user", prompt)
            append_to_history(agent_history, "assistant", relevancy_agent)
        results = []
        for relevant_link in relevant_links:
            try:
                url = relevant_link["href"]
                article = Article(url)
                article.download()
                article.parse()
                article.nlp()
                publish_date = article.publish_date
                if publish_date is None:
                    publish_date = "Unknown"
                else:
                    publish_date = publish_date.strftime("%A, %B %d %Y")
                results.append(f"Published on: {article.publish_date}\n{article.summary}")
            except Exception as e:
                print(e)
                pass
        if results:
            _start_timeout()
            Session.add_event("web_search", results)
            Session.learn([str(result) for result in results])
            return "Search results upserted to memory."
        else:
            return "No results were found."
    else:
        return f"Web search has reached rate limit. Resets in {timeout} seconds."