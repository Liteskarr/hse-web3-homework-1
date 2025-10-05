// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.27;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Test} from "forge-std/Test.sol";
import {BarToken} from "../src/BarToken.sol";
import {FooToken} from "../src/FooToken.sol";
import {RainswapBridge} from "../src/RainswapBridge.sol";

contract TestRainswapBridge is Test {
    event TxStarted(address sender, address receiver, address secretHash, uint256 value, uint256 timeout);
    event TxAborted(address secretHash, uint256 secret);
    event TxCommited(address secretHash, uint256 secret);

    BarToken barToken;
    FooToken fooToken;
    RainswapBridge bar2foo;

    function setUp() public {
        barToken = new BarToken(address(this));
        fooToken = new FooToken(address(this));
        bar2foo = new RainswapBridge(address(this), address(barToken), address(fooToken));
        barToken.grantMinterRole(address(bar2foo));
        fooToken.grantMinterRole(address(bar2foo));
    }

    function test_BridgeHappyPath() public {
        address bar = makeAddr("0x1337");
        address foo = makeAddr("0x4242");
        address secretHash;
        uint256 secret;
        (secretHash, secret) = makeAddrAndKey("somesecretkey");
        uint256 timeout = vm.getBlockTimestamp() + 10 hours;

        barToken.mint(bar, 1);
        barToken.mint(foo, 0);

        vm.startPrank(bar);

        IERC20(barToken).approve(address(bar2foo), 1);

        vm.expectEmit(address(bar2foo));
        emit TxStarted(bar, foo, secretHash, 1, timeout);
        bar2foo.startTx(foo, secretHash, 1, timeout);

        vm.expectEmit(address(bar2foo));
        emit TxCommited(secretHash, secret);
        bar2foo.commit(secretHash, secret);

        vm.stopPrank();

        vm.assertEq(IERC20(barToken).balanceOf(bar), 0);
        vm.assertEq(IERC20(fooToken).balanceOf(foo), 1);
    }

    function test_BridgeAbortHappyPath() public {
        address bar = makeAddr("0x1337");
        address foo = makeAddr("0x4242");
        address secretHash;
        uint256 secret;
        (secretHash, secret) = makeAddrAndKey("somesecretkey");
        uint256 timeout = 0;

        barToken.mint(bar, 1);
        barToken.mint(foo, 0);

        vm.startPrank(bar);

        IERC20(barToken).approve(address(bar2foo), 1);

        vm.expectEmit(address(bar2foo));
        emit TxStarted(bar, foo, secretHash, 1, timeout);
        bar2foo.startTx(foo, secretHash, 1, timeout);

        vm.expectEmit(address(bar2foo));
        emit TxAborted(secretHash, secret);
        bar2foo.abort(secretHash, secret);

        vm.stopPrank();

        vm.assertEq(IERC20(barToken).balanceOf(bar), 1);
        vm.assertEq(IERC20(fooToken).balanceOf(foo), 0);
    }
}
