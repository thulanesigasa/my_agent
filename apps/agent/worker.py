"""Single background scheduler owner. API scheduling is off by default."""

import asyncio
import logging
from scheduler import agent_scheduler

logging.basicConfig(level=logging.INFO)


async def main():
    agent_scheduler.start()
    try:
        await asyncio.Event().wait()
    finally:
        agent_scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
