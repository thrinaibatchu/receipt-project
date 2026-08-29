from __future__ import annotations

from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel

from receipt_project.analytics.canonical_prices import (
    get_canonical_price_history,
    get_latest_canonical_price_at_store,
    get_latest_canonical_prices_by_store,
)
from receipt_project.analytics.canonical_products import (
    resolve_canonical_key_from_text,
)
from receipt_project.analytics.item_prices import (
    get_item_price_history,
    get_latest_item_price_at_store,
    get_latest_item_prices_by_store,
)
from receipt_project.analytics.nl_sql import (
    MODEL_NAME,
    create_gemini_client,
)


class PriceQuestionIntent(BaseModel):
    intent: Literal[
        "price_trend",
        "latest_across_stores",
        "latest_at_store",
        "not_price_question",
    ]
    item: str | None = None
    store: str | None = None


def classify_price_question(
    question: str,
) -> PriceQuestionIntent:
    client: genai.Client = (
        create_gemini_client()
    )

    prompt = f"""
Classify this receipt analytics question.

Question:
{question}

Supported intents:

1. price_trend
   The user wants the historical price of an item over time,
   including wording such as:
   - price trend
   - price history
   - how has the price changed
   - what have I paid over time
   - price after discount over time

2. latest_across_stores
   The user wants the latest known price of an item compared
   across stores.

3. latest_at_store
   The user wants the latest known price of an item at one
   specific store.

4. not_price_question
   Anything else.

Extraction rules:

- Extract only the meaningful item search term.
- Do not include words like price, latest, trend, store,
  discount, across, or over time in the item.
- Extract store only for latest_at_store.
- If no store is stated, store must be null.
- "after discount" does not change the intent; our analytics
  layer always returns effective price after item-level discount.

Examples:

"What was the price trend for Andouille over time after discount?"
intent=price_trend
item=Andouille
store=null

"What is the latest price for Okra across stores?"
intent=latest_across_stores
item=Okra
store=null

"What is the latest price for Okra at Costco?"
intent=latest_at_store
item=Okra
store=Costco

"How many times did I buy milk?"
intent=not_price_question
item=null
store=null
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type=(
                "application/json"
            ),
            response_schema=(
                PriceQuestionIntent
            ),
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty "
            "price-question intent."
        )

    return (
        PriceQuestionIntent.model_validate_json(
            response.text
        )
    )


def execute_price_intent(
    intent: PriceQuestionIntent,
) -> list[dict]:
    """
    Execute a classified price question.

    Explicitly registered canonical products use canonical
    price analytics.

    Unknown products retain the existing raw-description
    fallback behavior.
    """
    if (
        intent.intent
        == "not_price_question"
    ):
        return []

    if not intent.item:
        raise RuntimeError(
            "Price question did not identify "
            "an item."
        )

    canonical_key = (
        resolve_canonical_key_from_text(
            intent.item
        )
    )

    if intent.intent == "price_trend":
        if canonical_key is not None:
            return (
                get_canonical_price_history(
                    canonical_key
                )
            )

        return get_item_price_history(
            search_text=intent.item,
            limit=500,
        )

    if (
        intent.intent
        == "latest_across_stores"
    ):
        if canonical_key is not None:
            return (
                get_latest_canonical_prices_by_store(
                    canonical_key
                )
            )

        return (
            get_latest_item_prices_by_store(
                search_text=intent.item
            )
        )

    if intent.intent == "latest_at_store":
        if not intent.store:
            raise RuntimeError(
                "Store-specific price question "
                "did not identify a store."
            )

        if canonical_key is not None:
            row = (
                get_latest_canonical_price_at_store(
                    canonical_key,
                    intent.store,
                )
            )
        else:
            row = (
                get_latest_item_price_at_store(
                    search_text=intent.item,
                    store_name=intent.store,
                )
            )

        return (
            [row]
            if row is not None
            else []
        )

    raise RuntimeError(
        f"Unsupported price intent: "
        f"{intent.intent}"
    )


def answer_price_question(
    question: str,
) -> tuple[
    PriceQuestionIntent,
    list[dict],
]:
    intent = classify_price_question(
        question
    )

    rows = execute_price_intent(
        intent
    )

    return intent, rows
