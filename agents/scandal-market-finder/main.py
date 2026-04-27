"""FastAPI entrypoint for scandal-market-finder."""
from shared.api import create_app


app = create_app("scandal-market-finder")

