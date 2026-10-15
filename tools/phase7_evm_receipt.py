"""Strict read-only EVM receipt checks, robust to equivalent hex representations."""

def parse_evm_status(value):
    if isinstance(value, bool):
        raise AssertionError("boolean is not a valid EVM receipt status")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if not value.startswith("0x"):
            raise AssertionError("status must be 0x-hex string or integer")
        try:
            return int(value, 16)
        except ValueError:
            pass
    raise AssertionError("unrecognized EVM receipt status")


def verify_confirmed_value_transfer(receipt, txid, expected_recipient):
    if not isinstance(receipt, dict):
        raise AssertionError("missing EVM receipt")
    if parse_evm_status(receipt.get("status")) != 1:
        raise AssertionError("EVM transaction execution failed")
    # A receipt missing hash/recipient cannot attest delivery; fail closed.
    if receipt.get("transactionHash") is None or receipt.get("to") is None:
        raise AssertionError("receipt missing transaction identity or recipient")
    if str(receipt["transactionHash"]).lower() != str(txid).lower():
        raise AssertionError("transaction hash mismatch")
    if str(receipt["to"]).lower() != str(expected_recipient).lower():
        raise AssertionError("transaction recipient mismatch")
    if receipt.get("blockNumber") in (None, "0x0", 0):
        raise AssertionError("EVM transaction is not confirmed in a non-genesis block")
    return True
