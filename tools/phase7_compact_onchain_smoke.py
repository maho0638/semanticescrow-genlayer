"""Read-only preflight for current packed SemanticEscrow; no signing nor GEN."""
from pathlib import Path
from eth_account import Account
from genlayer_py.chains.testnet_bradbury import testnet_bradbury
from genlayer_py.client.genlayer_client import GenLayerClient

from tools.phase7_legacy_compat import _install_legacy_consensus_abi
from tools.phase7_deploy_preflight import preview_deploy

client=GenLayerClient(testnet_bradbury,Account.create())
client.provider.url="https://rpc.testnet-chain.genlayer.com"
_install_legacy_consensus_abi(client.chain.consensus_main_contract)
source=Path("contracts/semantic_escrow.py").read_text(encoding="utf-8")
result=preview_deploy(client,source)
print("SE7_PACKED_DEPLOY_ESTIMATE",result["estimated_gas"],flush=True)
print("SE7_PACKED_SAFE_GAS",result["padded_gas"],flush=True)
assert result["estimated_gas"]<14_000_000
assert result["padded_gas"]<15_000_000
print("SE7_PACKED_READONLY_Bradbury_PASS",flush=True)
