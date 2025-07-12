import pytest
from unittest.mock import Mock, AsyncMock
from telegram import Update, User, Message, CallbackQuery, Chat
from telegram.ext import ContextTypes

from src.bot.keyboards import (
    encode_callback_data,
    decode_callback_data,
    get_main_menu,
    get_back_button,
)


def test_encode_decode_callback_data():
    """Test encoding and decoding callback data."""
    # Test simple data
    flow = "portfolio"
    step = "add_spot"
    data = {"qty": 5.0, "price": 108000.0}

    encoded = encode_callback_data(flow, step, data)
    decoded_flow, decoded_step, decoded_data = decode_callback_data(encoded)

    assert decoded_flow == flow
    assert decoded_step == step
    assert decoded_data == data

    # Test without data
    encoded = encode_callback_data(flow, step)
    decoded_flow, decoded_step, decoded_data = decode_callback_data(encoded)

    assert decoded_flow == flow
    assert decoded_step == step
    assert decoded_data == {}


def test_decode_simple_callback_data():
    """Test decoding simple callback data without encoding."""
    # Test simple callback data
    callback_data = "portfolio"
    flow, step, data = decode_callback_data(callback_data)

    assert flow == "portfolio"
    assert step == ""
    assert data == {}


def test_main_menu_buttons():
    """Test that main menu has correct buttons."""
    keyboard = get_main_menu()

    # Check that we have 2 rows
    assert len(keyboard.inline_keyboard) == 2

    # Check first row
    first_row = keyboard.inline_keyboard[0]
    assert len(first_row) == 2
    assert first_row[0].text == "📊 Portfolio"
    assert first_row[0].callback_data == "portfolio"
    assert first_row[1].text == "🛡️ Hedge"
    assert first_row[1].callback_data == "hedge"

    # Check second row
    second_row = keyboard.inline_keyboard[1]
    assert len(second_row) == 2
    assert second_row[0].text == "📈 Analytics"
    assert second_row[0].callback_data == "analytics"
    assert second_row[1].text == "⚙️ Risk Config"
    assert second_row[1].callback_data == "risk_config"


def test_back_button():
    """Test that back button has correct structure."""
    keyboard = get_back_button()

    # Check that we have 1 row with 1 button
    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 1

    back_button = keyboard.inline_keyboard[0][0]
    assert back_button.text == "🔙 Back"
    assert back_button.callback_data == "back"


@pytest.mark.asyncio
async def test_bot_start_command():
    """Test bot start command handler."""
    from src.bot import SpotHedgerBot

    # Mock environment
    import os

    os.environ["TELEGRAM_TOKEN"] = "test_token"

    # Create bot instance
    bot = SpotHedgerBot()

    # Mock update
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.first_name = "Test"
    update.message = Mock(spec=Message)
    update.message.reply_text = AsyncMock()

    # Mock context
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)

    # Test start command
    await bot.start_command(update, context)

    # Verify reply was called
    update.message.reply_text.assert_called_once()

    # Check that welcome text contains expected content
    call_args = update.message.reply_text.call_args
    text = call_args[0][0]  # First positional argument
    assert "Welcome to Spot Hedger Bot" in text
    assert "Test" in text  # User's first name


@pytest.mark.asyncio
async def test_bot_callback_handling():
    """Test bot callback query handling."""
    from src.bot import SpotHedgerBot

    # Mock environment
    import os

    os.environ["TELEGRAM_TOKEN"] = "test_token"

    # Create bot instance
    bot = SpotHedgerBot()

    # Mock update with callback query
    update = Mock(spec=Update)
    update.callback_query = Mock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = "portfolio"

    # Mock context
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)

    # Test callback handling
    await bot.handle_callback(update, context)

    # Verify answer was called
    update.callback_query.answer.assert_called_once()

    # Verify edit_message_text was called (for portfolio menu)
    update.callback_query.edit_message_text.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
