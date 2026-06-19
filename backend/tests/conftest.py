import asyncio
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    asyncio.set_event_loop_policy(event_loop_policy)
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()
