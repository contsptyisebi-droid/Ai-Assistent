# =============================================================================
# web_search.py — Web Search & Information Skills for J.A.R.V.I.S
# =============================================================================
# This module handles all internet-based information retrieval:
# - Web searches using DuckDuckGo (no API key needed!)
# - Weather information using the free wttr.in service
# - Random jokes from a public API
# - Fun facts from a public API
# - News headlines using DuckDuckGo news search
# =============================================================================

import requests                    # For making HTTP requests to web APIs
from duckduckgo_search import DDGS  # DuckDuckGo search library


# ---------------------------------------------------------------------------
# WEB SEARCH
# ---------------------------------------------------------------------------

def search_web(query: str) -> str:
    """
    Search the web using DuckDuckGo and return the top results.
    
    DuckDuckGo search requires no API key, making it perfect for this project.
    
    Args:
        query: The search terms to look up.
        
    Returns:
        A formatted string with the top search results.
    """
    try:
        results_text = []
        
        # Create a DDGS (DuckDuckGo Search) instance and search
        # max_results=5 gives us the top 5 results
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        
        if not results:
            return f"I found no results for '{query}', sir. Perhaps try different search terms."
        
        # Format each result nicely
        results_text.append(f"Search results for '{query}':\n")
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            href = result.get("href", "")
            
            # Truncate long descriptions to keep things readable
            if len(body) > 200:
                body = body[:200] + "..."
                
            results_text.append(f"{i}. {title}")
            results_text.append(f"   {body}")
            if href:
                results_text.append(f"   Source: {href}")
            results_text.append("")  # Empty line between results
        
        return "\n".join(results_text)
        
    except Exception as e:
        return (
            f"I encountered an issue with the web search, sir. "
            f"Error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# WEATHER
# ---------------------------------------------------------------------------

def get_weather(city: str = "London") -> str:
    """
    Get the current weather for a city using the free wttr.in service.
    
    wttr.in is a free weather service that requires no API key.
    It uses format=3 which returns a simple one-line summary.
    
    Args:
        city: The city to get weather for. Defaults to "London".
        
    Returns:
        A string with the current weather information.
    """
    
    # Use London as default if no city is specified
    if not city or city.strip() == "":
        city = "London"
    
    try:
        # Build the URL — format=3 gives us a compact, readable format
        # Example output: "London: ⛅️  +15°C"
        url = f"https://wttr.in/{city}?format=3"
        
        # Make the HTTP request with a timeout to avoid hanging
        response = requests.get(url, timeout=10)
        
        # Check if the request was successful (status code 200 = OK)
        response.raise_for_status()
        
        weather_text = response.text.strip()
        
        if weather_text:
            return f"Current weather — {weather_text}"
        else:
            return f"I was unable to retrieve weather data for {city}, sir."
            
    except requests.exceptions.ConnectionError:
        return (
            "I'm afraid I cannot reach the weather service at the moment, sir. "
            "Please check your internet connection."
        )
    except requests.exceptions.Timeout:
        return "The weather service took too long to respond, sir. Please try again."
    except requests.exceptions.HTTPError as e:
        return f"The weather service returned an error for '{city}', sir. {str(e)}"
    except Exception as e:
        return f"I encountered an issue retrieving the weather, sir. Error: {str(e)}"


# ---------------------------------------------------------------------------
# JOKES
# ---------------------------------------------------------------------------

def tell_joke() -> str:
    """
    Fetch a random joke from an online joke API.
    
    Uses the Official Joke API which is free and requires no authentication.
    
    Returns:
        A formatted joke string (setup + punchline).
    """
    try:
        # The Official Joke API — completely free, no key needed
        url = "https://official-joke-api.appspot.com/random_joke"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        joke_data = response.json()
        
        setup = joke_data.get("setup", "")
        punchline = joke_data.get("punchline", "")
        
        if setup and punchline:
            return f"{setup}\n\n...{punchline}"
        else:
            return "I appear to have misplaced the joke, sir. How embarrassing."
            
    except requests.exceptions.ConnectionError:
        return (
            "The joke API appears to be offline, sir. "
            "I could tell you one myself, but my humour requires significantly more setup."
        )
    except Exception as e:
        # Fallback joke if the API fails
        return (
            "I'm afraid the joke API is temporarily unavailable, sir. "
            "Here is a backup: Why do Java developers wear glasses? "
            "Because they don't C#. I'll see myself out."
        )


# ---------------------------------------------------------------------------
# FUN FACTS
# ---------------------------------------------------------------------------

def get_fun_fact() -> str:
    """
    Fetch a random interesting fact from an online API.
    
    Uses the Useless Facts API which provides random interesting facts.
    
    Returns:
        A random fun fact as a string.
    """
    try:
        # Useless Facts API — free, no authentication needed
        url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        fact_data = response.json()
        fact = fact_data.get("text", "")
        
        if fact:
            return f"Here is an interesting fact, sir: {fact}"
        else:
            return "I appear to have run out of facts, sir. Most unusual."
            
    except requests.exceptions.ConnectionError:
        return "I cannot connect to the facts database, sir. Perhaps invent your own?"
    except Exception as e:
        # Fallback fact if the API fails
        return (
            "The facts API is currently unavailable, sir. "
            "However, I can tell you that honey never spoils — "
            "archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible."
        )


# ---------------------------------------------------------------------------
# NEWS HEADLINES
# ---------------------------------------------------------------------------

def get_news() -> str:
    """
    Fetch the latest news headlines using DuckDuckGo news search.
    
    Returns:
        A formatted string with the top news headlines.
    """
    try:
        headlines = []
        
        # Use DuckDuckGo's news search to get current headlines
        with DDGS() as ddgs:
            news_results = list(ddgs.news(keywords="latest news today", max_results=5))
        
        if not news_results:
            return "I was unable to retrieve any news headlines at the moment, sir."
        
        headlines.append("Here are the latest news headlines, sir:\n")
        
        for i, article in enumerate(news_results, 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown source")
            date = article.get("date", "")
            
            # Format: "1. Headline (Source)"
            headline_line = f"{i}. {title}"
            if source:
                headline_line += f" — {source}"
            headlines.append(headline_line)
        
        return "\n".join(headlines)
        
    except Exception as e:
        return (
            f"I encountered an issue retrieving the news, sir. "
            f"Error: {str(e)}"
        )
