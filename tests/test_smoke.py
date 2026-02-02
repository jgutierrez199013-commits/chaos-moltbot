import asyncio
import pytest

from moltbot import AIBot, BotConfig

@pytest.mark.asyncio
async def test_bot_start_and_stop():
    config = BotConfig(enable_moltbook=False, check_interval_minutes=0.01, owner_name="TestUser")
    bot = AIBot(config)

    # Start the bot and let the heartbeat run briefly
    await bot.start()
    await asyncio.sleep(1)
    await bot.stop()

    assert not bot.is_running
