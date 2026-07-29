"""
Naive rule-based command parser.

This is intentionally NOT real NLP — it's a placeholder so the voice
command LIFECYCLE (create -> understand -> execute -> confirm) can be
built and tested end-to-end now, before Step 7 swaps this module out for
a real LLM/NLP-based parser. Swapping it out means changing ONLY this
file — VoiceCommandService only depends on `parse_command()`'s return
shape, not on how the parsing happens.

Supported patterns (case-insensitive), matching the doc's example command
"Today I sold 20 pickle bottles for 100 rupees each":
  - "sold 20 pickle bottles for 100 [rupees] each"       -> SALE
  - "sold 20 pickle bottles for 100 [rupees]" (total)     -> SALE
  - "spent 500 [rupees] on rent"                          -> EXPENSE
  - "restocked 20 pickle bottles" / "added 20 pickle bottles" -> STOCK_UPDATE
Anything else -> UNKNOWN, confidence 0.0 (triggers clarification).
"""
import re
from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    intent: str  # SALE, EXPENSE, STOCK_UPDATE, UNKNOWN
    entities: dict = field(default_factory=dict)
    confidence: float = 0.0


_SALE_EACH = re.compile(
    r"sold\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<product>[a-zA-Z ]+?)\s+for\s+(?P<price>\d+(?:\.\d+)?)\s*(?:rupees?)?\s*each",
    re.IGNORECASE,
)
_SALE_TOTAL = re.compile(
    r"sold\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<product>[a-zA-Z ]+?)\s+for\s+(?P<price>\d+(?:\.\d+)?)\s*(?:rupees?)?(?!\s*each)",
    re.IGNORECASE,
)
_EXPENSE = re.compile(
    r"spent\s+(?P<amount>\d+(?:\.\d+)?)\s*(?:rupees?)?\s+on\s+(?P<category>[a-zA-Z ]+)",
    re.IGNORECASE,
)
_STOCK_UPDATE = re.compile(
    r"(?:restocked|added)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<product>[a-zA-Z ]+)",
    re.IGNORECASE,
)


def parse_command(text: str) -> ParsedCommand:
    text = text.strip()

    m = _SALE_EACH.search(text)
    if m:
        return ParsedCommand(
            intent="SALE",
            entities={
                "product_name": m.group("product").strip(),
                "quantity": float(m.group("qty")),
                "unit_price": float(m.group("price")),
            },
            confidence=0.9,
        )

    m = _SALE_TOTAL.search(text)
    if m:
        qty = float(m.group("qty"))
        total = float(m.group("price"))
        return ParsedCommand(
            intent="SALE",
            entities={
                "product_name": m.group("product").strip(),
                "quantity": qty,
                "unit_price": round(total / qty, 2) if qty else 0,
            },
            confidence=0.75,  # lower confidence: we're inferring unit price from a total
        )

    m = _EXPENSE.search(text)
    if m:
        return ParsedCommand(
            intent="EXPENSE",
            entities={
                "amount": float(m.group("amount")),
                "category": m.group("category").strip(),
            },
            confidence=0.9,
        )

    m = _STOCK_UPDATE.search(text)
    if m:
        return ParsedCommand(
            intent="STOCK_UPDATE",
            entities={
                "product_name": m.group("product").strip(),
                "quantity": float(m.group("qty")),
            },
            confidence=0.85,
        )

    return ParsedCommand(intent="UNKNOWN", entities={}, confidence=0.0)
