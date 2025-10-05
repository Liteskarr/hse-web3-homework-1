import asyncio
import logging
from datetime import timedelta
from typing import Any

from web3.contract import AsyncContract

logger = logging.getLogger(__name__)


class BridgeInfo:
    def __init__(self, contract: AsyncContract):
        self.contract = contract
        self.name = f"Bridge@{contract.address}"
        self.last_processed_block: int | None = None


class Watchdog:
    def __init__(self, bridges: list[BridgeInfo], poll_interval: timedelta = None):
        self.bridges = bridges
        self.poll_interval = poll_interval or timedelta(seconds=2)
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info(f"Watchdog starting with {len(self.bridges)} bridges")

        for bridge in self.bridges:
            if bridge.last_processed_block is None:
                current_block = await bridge.contract.w3.eth.block_number
                bridge.last_processed_block = current_block
                logger.info(f"{bridge.name}: Starting from block {current_block}")

        while True:
            try:
                await asyncio.gather(
                    *[self._poll_bridge(bridge) for bridge in self.bridges],
                    return_exceptions=True,
                )
            except Exception as e:
                logger.error(f"Error in watchdog main loop: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval.total_seconds())

    async def _poll_bridge(self, bridge: BridgeInfo) -> None:
        try:
            current_block = await bridge.contract.w3.eth.block_number

            if current_block <= bridge.last_processed_block:
                return

            from_block = bridge.last_processed_block + 1
            to_block = current_block

            logger.debug(f"{bridge.name}: Polling blocks {from_block} to {to_block}")

            sended_filter = bridge.contract.events.Sended.create_filter(
                fromBlock=from_block,
                toBlock=to_block,
            )
            sended_events = await sended_filter.get_all_entries()

            received_filter = bridge.contract.events.Received.create_filter(
                fromBlock=from_block,
                toBlock=to_block,
            )
            received_events = await received_filter.get_all_entries()

            for event in sended_events:
                await self._handle_sended_event(bridge, event)

            for event in received_events:
                await self._handle_received_event(bridge, event)

            bridge.last_processed_block = current_block

        except Exception as e:
            logger.error(
                f"Error polling bridge {bridge.name}: {e}",
                exc_info=True,
            )

    async def _handle_sended_event(self, bridge: BridgeInfo, event: Any) -> None:
        args = event["args"]
        logger.info(
            f"{bridge.name}: Sended event - "
            f"nonce={args['nonce'].hex()}, "
            f"txID={args['txID']}, "
            f"value={args['value']}, "
            f"sender={args['sender']}, "
            f"receiver={args['receiver']}, "
            f"receiverURL={args['receiverURL']}"
        )

    async def _handle_received_event(self, bridge: BridgeInfo, event: Any) -> None:
        args = event["args"]
        logger.info(
            f"{bridge.name}: Received event - "
            f"nonce={args['nonce'].hex()}, "
            f"txID={args['txID']}, "
            f"value={args['value']}, "
            f"sender={args['sender']}, "
            f"receiver={args['receiver']}"
        )
