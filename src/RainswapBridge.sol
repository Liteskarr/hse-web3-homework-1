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

contract RainswapBridge is Ownable {
    event TxStarted(address sender, address receiver, address secretHash, uint256 value, uint256 timeout);
    event TxAborted(address secretHash, uint256 secret);
    event TxCommited(address secretHash, uint256 secret);

    error SecretHashCollision();

    constructor(address initialOwner, address f, address t) Ownable(initialOwner) {
        from = f;
        to = t;
    }

    function startTx(address receiver, address secretHash, uint256 value, uint256 timeout) public {
        if (txes[secretHash].active) {
            revert SecretHashCollision();
        }

        address sender = _msgSender();
        txes[secretHash] = TxBody(true, sender, receiver, value, timeout);

        require(IERC20(from).transferFrom(sender, address(this), value));

        emit TxStarted(sender, receiver, secretHash, value, timeout);
    }

    function commit(address secretHash, uint256 secret) public {
        TxBody memory body = txes[secretHash];
        require(body.active, "No active Tx with the secret hash");
        require(block.timestamp <= body.timeout, "Tx commiting are able only before timeout. Now you can abort it.");

        Burnable(from).burn(body.value);
        Mintable(to).mint(body.receiver, body.value);

        delete txes[secretHash];
        emit TxCommited(secretHash, secret);
    }

    function abort(address secretHash, uint256 secret) public {
        TxBody memory body = txes[secretHash];
        require(body.active, "No active Tx with the secret hash");
        require(block.timestamp > body.timeout, "Tx aborting are able only after timeout");

        require(IERC20(from).transfer(body.sender, body.value));

        delete txes[secretHash];
        emit TxAborted(secretHash, secret);
    }

    struct TxBody {
        bool active;
        address sender;
        address receiver;
        uint256 value;
        uint256 timeout;
    }

    address internal from;
    address internal to;
    mapping(address => TxBody) internal txes;
}
