
import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("COMBINED_API_URL")


def fetch_data():
    if not API_URL or API_URL == "your_combined_api_endpoint":
        raise ValueError(
            "Set your actual COMBINED_API_URL in the .env file."
        )

    response = requests.get(API_URL, timeout=60)
    response.raise_for_status()

    payload = response.json()

    # Support common API response formats.
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get(
            "data",
            payload.get("results", payload.get("rows"))
        )

        if rows is None:
            raise ValueError(
                "Could not find row data in the API response. "
                "Inspect the response structure."
            )
    else:
        raise ValueError("Unexpected API response format.")

    if not isinstance(rows, list):
        raise ValueError("The API data is not a list of rows.")

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("The API returned no records.")

    return df
