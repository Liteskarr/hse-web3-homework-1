import asyncio
import json
from pathlib import Path
from typing import Any

from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.types import TxReceipt


async def compile_all_contracts():
    project_root = Path(__file__).parent.parent

    process = await asyncio.create_subprocess_exec(
        "forge",
        "build",
        "--root",
        str(project_root / "contracts"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown compilation error"
        raise RuntimeError(f"Failed to compile RainswapBridge.sol: {error_msg}")


async def proccess_tx(w3: AsyncWeb3, private_key: str, txn: Any) -> TxReceipt:
    try:
        gas_estimate = await w3.eth.estimate_gas(txn)
        txn["gas"] = gas_estimate
    except Exception as e:
        raise RuntimeError(f"Failed to estimate gas for deployment: {e}")

    signed_txn = w3.eth.account.sign_transaction(txn, private_key)

    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    tx_receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)

    if tx_receipt["status"] != 1:
        raise RuntimeError(f"Contract deployment failed with status {tx_receipt['status']}")

    return tx_receipt


async def connect_to_contract(
    w3: AsyncWeb3,
    contract_address: str,
    abi: list[dict[str, Any]],
) -> AsyncContract:
    if not AsyncWeb3.is_address(contract_address):
        raise ValueError(f"Invalid contract address: {contract_address}")

    return w3.eth.contract(
        address=AsyncWeb3.to_checksum_address(contract_address),
        abi=abi,
    )


async def deploy_contract(
    w3: AsyncWeb3,
    deployer_private_key: str,
    abi: list[dict[str, Any]],
    bytecode: str,
    *args: tuple,
) -> tuple[AsyncContract, str]:
    deployer_address = w3.eth.account.from_key(deployer_private_key).address
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    tx_receipt = await proccess_tx(
        w3,
        deployer_private_key,
        await contract.constructor(*args).build_transaction(
            {
                "from": deployer_address,
                "nonce": await w3.eth.get_transaction_count(deployer_address),
                "gasPrice": await w3.eth.gas_price,
            }
        ),
    )

    return await connect_to_contract(w3, tx_receipt["contractAddress"], abi)


async def deploy_rainswap_bridge(
    w3: AsyncWeb3,
    deployer_private_key: str,
    initial_owner: str,
    token_address: str,
):
    project_root = Path(__file__).parent.parent
    contracts_dir = project_root / "contracts"
    output_file = contracts_dir / "out" / "RainswapBridge.sol" / "RainswapBridge.json"

    if not output_file.exists():
        await compile_all_contracts()

    with open(output_file, "r") as f:
        contract_json = json.load(f)

    return await deploy_contract(
        w3,
        deployer_private_key,
        contract_json["abi"],
        contract_json["bytecode"]["object"],
        AsyncWeb3.to_checksum_address(initial_owner),
        AsyncWeb3.to_checksum_address(token_address),
    )


async def deploy_bar_token(
    w3: AsyncWeb3,
    deployer_private_key: str,
    initial_owner: str,
) -> AsyncContract:
    project_root = Path(__file__).parent.parent
    contracts_dir = project_root / "contracts"
    output_file = contracts_dir / "out" / "BarToken.sol" / "BarToken.json"

    if not output_file.exists():
        await compile_all_contracts()

    with open(output_file, "r") as f:
        contract_json = json.load(f)

    return await deploy_contract(
        w3,
        deployer_private_key,
        contract_json["abi"],
        contract_json["bytecode"]["object"],
        AsyncWeb3.to_checksum_address(initial_owner),
    )


async def deploy_foo_token(
    w3: AsyncWeb3,
    deployer_private_key: str,
    initial_owner: str,
) -> AsyncContract:
    project_root = Path(__file__).parent.parent
    contracts_dir = project_root / "contracts"
    output_file = contracts_dir / "out" / "FooToken.sol" / "FooToken.json"

    if not output_file.exists():
        await compile_all_contracts()

    with open(output_file, "r") as f:
        contract_json = json.load(f)

    return await deploy_contract(
        w3,
        deployer_private_key,
        contract_json["abi"],
        contract_json["bytecode"]["object"],
        AsyncWeb3.to_checksum_address(initial_owner),
    )


async def grant_minter_role(
    w3: AsyncWeb3,
    owner_private_key: str,
    token_contract: str,
    minter_address: str,
):
    owner_address = w3.eth.account.from_key(owner_private_key).address

    await proccess_tx(
        w3,
        owner_private_key,
        await token_contract.functions.grantMinterRole(
            AsyncWeb3.to_checksum_address(minter_address),
        ).build_transaction(
            {
                "from": owner_address,
                "nonce": await w3.eth.get_transaction_count(owner_address),
                "gasPrice": await w3.eth.gas_price,
            }
        ),
    )
