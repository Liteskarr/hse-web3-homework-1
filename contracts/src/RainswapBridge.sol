// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.27;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

interface Mintable {
    function mint(address to, uint256 value) external;
}

interface Burnable {
    function burn(uint256 value) external;
}

struct Address {
    address bridge;
    address wallet;
}

event Sended(bytes32 nonce, uint256 txID, uint256 value, Address sender, Address receiver, string receiverURL);

event Received(bytes32 nonce, uint256 txID, uint256 value, Address sender, Address receiver);

contract RainswapBridge is Ownable {
    constructor(address initialOwner, address t) Ownable(initialOwner) {
        token = t;
        lastID = 1;
    }

    function startTx(uint256 value, address sender, Address calldata receiver, string calldata receiverURL) public {
        uint256 txID = lastID;
        lastID++;

        Address memory senderAddr = Address(address(this), sender);
        bytes32 nonce = keccak256(abi.encode(txID, value, senderAddr, receiver, receiverURL));

        require(IERC20(token).transferFrom(sender, address(this), value));
        Burnable(token).burn(value);

        emit Sended(nonce, txID, value, senderAddr, receiver, receiverURL);
    }

    function commit(
        bytes32 nonce,
        uint256 txID,
        uint256 value,
        Address calldata sender,
        address receiver,
        string calldata receiverURL
    ) public {
        Address memory receiverAddr = Address(address(this), receiver);
        bytes32 localNonce = keccak256(abi.encode(txID, value, sender, receiverAddr, receiverURL));
        require(nonce == localNonce);

        require(!receivedTxes[nonce]);
        receivedTxes[nonce] = true;

        Mintable(token).mint(receiver, value);

        emit Received(nonce, txID, value, sender, receiverAddr);
    }

    address internal token;
    uint256 internal lastID;
    mapping(bytes32 => bool) receivedTxes;
}
