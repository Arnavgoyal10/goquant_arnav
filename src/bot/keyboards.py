"""Inline keyboard layouts for the Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any
import json


def encode_callback_data(flow: str, step: str, data: Dict[str, Any] = None) -> str:
    """Encode callback data in the form FLOW|STEP|JSON.

    Args:
        flow: Flow identifier (e.g., 'portfolio', 'hedge')
        step: Step identifier (e.g., 'add_spot', 'confirm')
        data: Optional data dictionary

    Returns:
        Encoded callback data string
    """
    if data is None:
        data = {}

    json_data = json.dumps(data)
    return f"{flow}|{step}|{json_data}"


def decode_callback_data(callback_data: str) -> tuple[str, str, Dict[str, Any]]:
    """Decode callback data from the form FLOW|STEP|JSON.

    Args:
        callback_data: Encoded callback data string

    Returns:
        Tuple of (flow, step, data)
    """
    try:
        parts = callback_data.split("|", 2)
        if len(parts) == 3:
            flow, step, json_data = parts
            data = json.loads(json_data)
        elif len(parts) == 2:
            flow, step = parts
            data = {}
        else:
            flow, step, data = callback_data, "", {}

        return flow, step, data
    except (json.JSONDecodeError, ValueError):
        # Fallback for simple callback data
        return callback_data, "", {}


def get_main_menu() -> InlineKeyboardMarkup:
    """Get the main menu keyboard.

    Returns:
        InlineKeyboardMarkup with main menu options
    """
    keyboard = [
        [
            InlineKeyboardButton("📊 Portfolio", callback_data="portfolio"),
            InlineKeyboardButton("🛡️ Hedge", callback_data="hedge"),
        ],
        [
            InlineKeyboardButton("📈 Analytics", callback_data="analytics"),
            InlineKeyboardButton("⚙️ Risk Config", callback_data="risk_config"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_back_button() -> InlineKeyboardMarkup:
    """Get a keyboard with just a back button.

    Returns:
        InlineKeyboardMarkup with back button
    """
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]

    return InlineKeyboardMarkup(keyboard)


def get_portfolio_menu() -> InlineKeyboardMarkup:
    """Get the portfolio menu keyboard.

    Returns:
        InlineKeyboardMarkup with portfolio options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Spot",
                callback_data=encode_callback_data("portfolio", "add_spot"),
            ),
            InlineKeyboardButton(
                "➖ Remove Spot",
                callback_data=encode_callback_data("portfolio", "remove_spot"),
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ Add Future",
                callback_data=encode_callback_data("portfolio", "add_future"),
            ),
            InlineKeyboardButton(
                "➖ Remove Future",
                callback_data=encode_callback_data("portfolio", "remove_future"),
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Refresh", callback_data=encode_callback_data("portfolio", "refresh")
            ),
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_hedge_menu() -> InlineKeyboardMarkup:
    """Get the hedge menu keyboard.

    Returns:
        InlineKeyboardMarkup with hedge options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "⚖️ Perp Δ-Neutral",
                callback_data=encode_callback_data("hedge", "perp_delta_neutral"),
            ),
            InlineKeyboardButton(
                "🛡️ Protective Put",
                callback_data=encode_callback_data("hedge", "protective_put"),
            ),
        ],
        [
            InlineKeyboardButton(
                "📈 Covered Call",
                callback_data=encode_callback_data("hedge", "covered_call"),
            ),
            InlineKeyboardButton(
                "🔒 Collar", callback_data=encode_callback_data("hedge", "collar")
            ),
        ],
        [
            InlineKeyboardButton(
                "♻️ Dynamic Hedge",
                callback_data=encode_callback_data("hedge", "dynamic_hedge"),
            ),
            InlineKeyboardButton(
                "📂 View Hedges",
                callback_data=encode_callback_data("hedge", "view_hedges"),
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑️ Remove Hedge",
                callback_data=encode_callback_data("hedge", "remove_hedge"),
            ),
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_analytics_menu() -> InlineKeyboardMarkup:
    """Get the analytics menu keyboard.

    Returns:
        InlineKeyboardMarkup with analytics options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "📊 Risk Summary",
                callback_data=encode_callback_data("analytics", "risk_summary"),
            ),
            InlineKeyboardButton(
                "💰 P&L Attribution",
                callback_data=encode_callback_data("analytics", "pnl_attribution"),
            ),
        ],
        [
            InlineKeyboardButton(
                "📈 Correlation Matrix",
                callback_data=encode_callback_data("analytics", "correlation_matrix"),
            ),
            InlineKeyboardButton(
                "🧪 Stress Test",
                callback_data=encode_callback_data("analytics", "stress_test"),
            ),
        ],
        [
            InlineKeyboardButton(
                "📅 History", callback_data=encode_callback_data("analytics", "history")
            ),
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_risk_config_menu() -> InlineKeyboardMarkup:
    """Get the risk configuration menu keyboard.

    Returns:
        InlineKeyboardMarkup with risk config options
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "✏️ Edit Delta Limit",
                callback_data=encode_callback_data("risk_config", "edit_delta"),
            ),
            InlineKeyboardButton(
                "✏️ Edit VaR Limit",
                callback_data=encode_callback_data("risk_config", "edit_var"),
            ),
        ],
        [
            InlineKeyboardButton(
                "✏️ Edit Max Drawdown",
                callback_data=encode_callback_data("risk_config", "edit_drawdown"),
            ),
            InlineKeyboardButton("🔙 Back", callback_data="back"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_confirmation_buttons(
    action: str, data: Dict[str, Any] = None
) -> InlineKeyboardMarkup:
    """Get confirmation buttons for an action.

    Args:
        action: Action to confirm
        data: Additional data for the action

    Returns:
        InlineKeyboardMarkup with confirm/cancel buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Confirm",
                callback_data=encode_callback_data(action, "confirm", data or {}),
            ),
            InlineKeyboardButton(
                "❌ Cancel", callback_data=encode_callback_data(action, "cancel")
            ),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_pagination_buttons(
    current_page: int, total_pages: int, base_action: str, data: Dict[str, Any] = None
) -> InlineKeyboardMarkup:
    """Get pagination buttons.

    Args:
        current_page: Current page number (1-based)
        total_pages: Total number of pages
        base_action: Base action for the pagination
        data: Additional data

    Returns:
        InlineKeyboardMarkup with pagination buttons
    """
    keyboard = []

    # Navigation buttons
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "◀️",
                callback_data=encode_callback_data(
                    base_action, "page", {"page": current_page - 1}
                ),
            )
        )

    nav_buttons.append(
        InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop")
    )

    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                "▶️",
                callback_data=encode_callback_data(
                    base_action, "page", {"page": current_page + 1}
                ),
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Back button
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

    return InlineKeyboardMarkup(keyboard)
