import os
from dotenv import load_dotenv

load_dotenv()


PROXY_URL = os.environ.get("WEBSHARE_PROXY_URL")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

DB_PATH = os.environ.get("DB_PATH", "jobs.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "chroma_index")

JITTER_MIN = 2.5
JITTER_MAX = 8.0
RESULTS_PER_SEARCH = 25
RESULTS_PER_TERM = 38

SEARCH_TERM_POOLS = {
    "mle": [
        "Junior Machine Learning Engineer",
        "Entry Level Machine Learning Engineer",
        "Machine Learning Engineer, New Grad",
        "Machine Learning Engineer"
        "ML Engineer",
        "ML/AI Engineer",
        "AI Engineer",
        "ML/AI Forward Deployed Engineer",
        "Research Engineer",
        "Deep Learning Engineer",
        "NLP Engineer",
        
    ],
    "data_scientist": [
        "Junior Data Scientist",
        "Entry Level Data Scientist",
        "Data Scientist, New Grad",
        "Data Scientist",
        "Customer Data Scientist",
        "Product Data Scientist",
        "Data Science Engineer",
"Applied Scientist",
"Research Scientist",
"Machine Learning Scientist",
        "Data Analyst",
    ],
}