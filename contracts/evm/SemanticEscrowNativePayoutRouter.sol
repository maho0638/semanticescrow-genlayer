// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title SemanticEscrowNativePayoutRouter
 * @notice Narrowly scoped GenLayer Ghost -> EVM native GEN payout bridge.
 * Only the pre-bound, source-pinned SemanticEscrow v2 Ghost may instruct this
 * contract to send value. Each immutable 32-byte intent can succeed at most
 * once. NativeIntentPaid is emitted only after a successful EVM CALL, in the
 * same atomic EVM transaction.
 *
 * This router cannot independently verify GenVM finality. A separate
 * authenticated GenLayer parent receipt is mandatory before credit claims.
 * This is NOT failed-GenLayer-child value recovery.
 */
contract SemanticEscrowNativePayoutRouter {
    address public immutable escrowGhost;
    uint256 public immutable expectedChainId;

    mapping(bytes32 => bool) public delivered;
    uint256 private entered = 1;

    event NativeIntentPaid(
        bytes32 indexed intentId,
        address indexed recipient,
        address indexed ghost,
        uint256 amountWei
    );

    error UnauthorizedGhost();
    error WrongChain();
    error InvalidIntent();
    error InvalidRecipient();
    error ZeroValue();
    error AlreadyDelivered();
    error ReentrantCall();
    error TransferFailed();
    error DirectFundingForbidden();

    constructor(address escrowGhost_, uint256 chainId_) {
        if (escrowGhost_ == address(0)) revert UnauthorizedGhost();
        if (chainId_ != block.chainid) revert WrongChain();
        escrowGhost = escrowGhost_;
        expectedChainId = chainId_;
    }

    /**
     * GenVM v0.2.16 EVM interface uses a fixed bytes32 intent and Address.
     * EVM selector: disburse(bytes32,address).
     */
    function disburse(bytes32 intentId, address payable recipient) external payable {
        if (block.chainid != expectedChainId) revert WrongChain();
        if (msg.sender != escrowGhost) revert UnauthorizedGhost();
        if (recipient == address(0) || recipient == address(this) || recipient == escrowGhost) {
            revert InvalidRecipient();
        }
        if (msg.value == 0) revert ZeroValue();
        if (entered != 1) revert ReentrantCall();
        if (intentId == bytes32(0)) revert InvalidIntent();
        if (delivered[intentId]) revert AlreadyDelivered();

        entered = 2;
        delivered[intentId] = true;
        (bool ok,) = recipient.call{value: msg.value}("");
        if (!ok) revert TransferFailed();

        emit NativeIntentPaid(intentId, recipient, msg.sender, msg.value);
        entered = 1;
    }

    receive() external payable {
        revert DirectFundingForbidden();
    }
}
