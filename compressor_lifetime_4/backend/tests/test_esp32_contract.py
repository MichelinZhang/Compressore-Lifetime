import asyncio

import pytest

from app.adapters.esp32_http import Esp32HttpDriver


def test_esp32_driver_is_placeholder() -> None:
    driver = Esp32HttpDriver()
    with pytest.raises(NotImplementedError):
        asyncio.run(driver.connect("esp32-001"))
