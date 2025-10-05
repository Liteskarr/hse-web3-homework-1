import asyncio

from web3.contract import AsyncContract

from bridge_watchdog.contract_utils import (
    deploy_bar_token,
    deploy_foo_token,
    deploy_rainswap_bridge,
)
from bridge_watchdog.tests.anvil import spawn_anvil_networks, AnvilTestNet
from bridge_watchdog.watchdog import BridgeInfo, Watchdog


DEPLOY_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


async def deploy_pair(
    n1: AnvilTestNet, n2: AnvilTestNet
) -> tuple[AsyncContract, AsyncContract, AsyncContract, AsyncContract]:
    bar_token = await deploy_bar_token(
        w3=n1.w3,
        deployer_private_key=DEPLOY_PRIVATE_KEY,
        initial_owner=n1.w3.eth.account.from_key(DEPLOY_PRIVATE_KEY).address,
    )

    foo_token = await deploy_foo_token(
        w3=n2.w3,
        deployer_private_key=DEPLOY_PRIVATE_KEY,
        initial_owner=n2.w3.eth.account.from_key(DEPLOY_PRIVATE_KEY).address,
    )

    bar2foo = await deploy_rainswap_bridge(
        w3=n1.w3,
        deployer_private_key=DEPLOY_PRIVATE_KEY,
        initial_owner=n1.w3.eth.account.from_key(DEPLOY_PRIVATE_KEY).address,
        token_address=bar_token.address,
    )

    foo2bar = await deploy_rainswap_bridge(
        w3=n2.w3,
        deployer_private_key=DEPLOY_PRIVATE_KEY,
        initial_owner=n2.w3.eth.account.from_key(DEPLOY_PRIVATE_KEY).address,
        token_address=foo_token.address,
    )

    return bar_token, foo_token, bar2foo, foo2bar


async def test_happy_path():
    async with spawn_anvil_networks(2, base_port=8545) as networks:
        bar_token, foo_token, bar2foo, foo2bar = await deploy_pair(*networks)

        watchdog = Watchdog(bridges=[BridgeInfo(bar2foo), BridgeInfo(foo2bar)])
        watchdog_task = asyncio.create_task(watchdog.run())
        try:
            await asyncio.wait_for(watchdog_task, timeout=5.0)
        except asyncio.TimeoutError:
            watchdog_task.cancel()
            try:
                await watchdog_task
            except asyncio.CancelledError:
                pass
