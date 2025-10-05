import asyncio
from contextlib import asynccontextmanager
from typing import Any

from web3 import AsyncWeb3, AsyncHTTPProvider


class AnvilTestNet:
    def __init__(self, port: int, process: asyncio.subprocess.Process) -> None:
        self.port = port
        self.process = process
        self.url = f"http://127.0.0.1:{port}"
        self._w3: AsyncWeb3 | None = None

    @property
    def w3(self) -> AsyncWeb3:
        if self._w3 is None:
            self._w3 = AsyncWeb3(AsyncHTTPProvider(self.url))
        return self._w3

    async def is_ready(self) -> bool:
        try:
            await self.w3.eth.block_number
            return True
        except Exception:
            return False

    async def wait_until_ready(self, timeout: float = 10.0) -> None:
        start_time = asyncio.get_event_loop().time()
        while True:
            if await self.is_ready():
                return
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Anvil on port {self.port} did not become ready within {timeout}s")
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()


@asynccontextmanager
async def spawn_anvil_networks(n: int, base_port: int = 8545):
    networks: list[AnvilTestNet] = []
    try:
        for i in range(n):
            port = base_port + i
            process = await asyncio.create_subprocess_exec(
                "anvil",
                "--port",
                str(port),
                "--host",
                "127.0.0.1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            network = AnvilTestNet(port, process)
            networks.append(network)

        await asyncio.gather(*[network.wait_until_ready() for network in networks])

        yield networks
    finally:
        await asyncio.gather(
            *[network.stop() for network in networks],
            return_exceptions=True,
        )
