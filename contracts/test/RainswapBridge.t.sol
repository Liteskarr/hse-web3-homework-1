// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.27;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Test} from "forge-std/Test.sol";
import {BarToken} from "../src/BarToken.sol";
import {FooToken} from "../src/FooToken.sol";
import {RainswapBridge, Address, Received, Sended} from "../src/RainswapBridge.sol";

contract TestRainswapBridge is Test {
    BarToken barToken;
    FooToken fooToken;
    RainswapBridge bar2foo;
    RainswapBridge foo2bar;

    string fooURL = "https://eth.llamarpc.com";

    function setUp() public {
        barToken = new BarToken(address(this));
        fooToken = new FooToken(address(this));
        bar2foo = new RainswapBridge(address(this), address(barToken));
        barToken.grantMinterRole(address(bar2foo));
        foo2bar = new RainswapBridge(address(this), address(fooToken));
        fooToken.grantMinterRole(address(foo2bar));
    }

    function getNonce(
        uint256 txID,
        uint256 value,
        Address memory sender,
        Address memory receiver,
        string memory receiverURL
    ) internal pure returns (bytes32) {
        return
            keccak256(abi.encode(txID, value, sender, receiver, receiverURL));
    }

    function test_BridgeHappyPath() public {
        address bar = makeAddr("0x1337");
        address foo = makeAddr("0x4242");

        Address memory barAddr = Address(address(bar2foo), bar);
        Address memory fooAddr = Address(address(foo2bar), foo);

        bytes32 nonce = getNonce(1, 1, barAddr, fooAddr, fooURL);

        barToken.mint(bar, 1);

        // Bar Net
        vm.startPrank(bar);

        IERC20(barToken).approve(address(bar2foo), 1);

        vm.expectEmit(address(bar2foo));
        emit Sended(nonce, 1, 1, barAddr, fooAddr, fooURL);
        bar2foo.startTx(1, bar, fooAddr, fooURL);

        vm.stopPrank();

        // Foo Net
        vm.expectEmit(address(foo2bar));
        emit Received(nonce, 1, 1, barAddr, fooAddr);
        foo2bar.commit(nonce, 1, 1, barAddr, address(foo), fooURL);

        vm.assertEq(IERC20(barToken).balanceOf(bar), 0);
        vm.assertEq(IERC20(fooToken).balanceOf(foo), 1);
    }
}
