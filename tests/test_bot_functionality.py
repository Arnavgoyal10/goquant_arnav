"""Test bot functionality without starting polling."""

import asyncio
from unittest.mock import Mock, AsyncMock
from telegram import Update, User, Message, CallbackQuery
from telegram.ext import ContextTypes

from src.bot import SpotHedgerBot


async def test_bot_creation():
    """Test that bot can be created and initialized."""
    print("Testing bot creation...")

    try:
        bot = SpotHedgerBot()
        print("✅ Bot created successfully")
        print(f"✅ Token loaded: {bot.token[:10]}...")
        return True
    except Exception as e:
        print(f"❌ Bot creation failed: {e}")
        return False


async def test_start_command():
    """Test the /start command handler."""
    print("\nTesting /start command...")

    try:
        bot = SpotHedgerBot()

        # Mock update
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 12345
        update.effective_user.first_name = "TestUser"
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()

        # Mock context
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)

        # Test start command
        await bot.start_command(update, context)

        # Verify reply was called
        update.message.reply_text.assert_called_once()

        # Check welcome text
        call_args = update.message.reply_text.call_args
        text = call_args[0][0]

        assert "Welcome to Spot Hedger Bot" in text
        assert "TestUser" in text

        print("✅ /start command works correctly")
        return True

    except Exception as e:
        print(f"❌ /start command test failed: {e}")
        return False


async def test_callback_handling():
    """Test callback query handling."""
    print("\nTesting callback handling...")

    try:
        bot = SpotHedgerBot()

        # Test each main menu option
        test_cases = ["portfolio", "hedge", "analytics", "risk_config", "back"]

        for callback_data in test_cases:
            # Mock update with callback query
            update = Mock(spec=Update)
            update.callback_query = Mock(spec=CallbackQuery)
            update.callback_query.answer = AsyncMock()
            update.callback_query.edit_message_text = AsyncMock()
            update.callback_query.data = callback_data

            # Mock context
            context = Mock(spec=ContextTypes.DEFAULT_TYPE)

            # Test callback handling
            await bot.handle_callback(update, context)

            # Verify answer was called
            update.callback_query.answer.assert_called_once()

            print(f"✅ Callback '{callback_data}' handled correctly")

        return True

    except Exception as e:
        print(f"❌ Callback handling test failed: {e}")
        return False


async def test_keyboard_generation():
    """Test keyboard generation."""
    print("\nTesting keyboard generation...")

    try:
        from src.bot.keyboards import (
            get_main_menu,
            get_back_button,
            encode_callback_data,
            decode_callback_data,
        )

        # Test main menu
        main_menu = get_main_menu()
        assert len(main_menu.inline_keyboard) == 2
        assert len(main_menu.inline_keyboard[0]) == 2
        assert len(main_menu.inline_keyboard[1]) == 2
        print("✅ Main menu keyboard generated correctly")

        # Test back button
        back_button = get_back_button()
        assert len(back_button.inline_keyboard) == 1
        assert len(back_button.inline_keyboard[0]) == 1
        print("✅ Back button keyboard generated correctly")

        # Test callback encoding/decoding
        test_data = {"qty": 5.0, "price": 108000.0}
        encoded = encode_callback_data("portfolio", "add_spot", test_data)
        flow, step, data = decode_callback_data(encoded)

        assert flow == "portfolio"
        assert step == "add_spot"
        assert data == test_data
        print("✅ Callback encoding/decoding works correctly")

        return True

    except Exception as e:
        print(f"❌ Keyboard generation test failed: {e}")
        return False


async def main():
    """Run all bot functionality tests."""
    print("🤖 Testing Spot Hedger Bot Functionality\n")

    tests = [
        test_bot_creation(),
        test_start_command(),
        test_callback_handling(),
        test_keyboard_generation(),
    ]

    results = await asyncio.gather(*tests, return_exceptions=True)

    passed = sum(1 for result in results if result is True)
    total = len(tests)

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Bot is ready to use.")
        print("\nTo start the bot, run:")
        print("python -m src.bot")
        print("\nThen send /start to your bot on Telegram.")
    else:
        print("❌ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
