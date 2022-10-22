import { call } from "../scripts/call";
import algosdk, {
  encodeObj,
  generateAccount,
  makeAssetTransferTxnWithSuggestedParamsFromObject,
  makeBasicAccountTransactionSigner,
  OnApplicationComplete,
  Transaction,
  Account,
} from "algosdk";
import {
  appAddr,
  appId,
  assetId,
  getAppCreator,
  user,
} from "../scripts/config";

import {
  algodClient,
  algoIndexer,
  checkAssetBalOfAddr,
  optInToAsset,
  sendAlgo,
} from "../scripts/utils";

async function optInToAssetandContract(user: Account) {
  const params = await algodClient.getTransactionParams().do();
  const enc = new TextEncoder();
  const note = enc.encode("OptIn");
  let optInTxn1 = makeAssetTransferTxnWithSuggestedParamsFromObject({
    from: user.addr,
    to: user.addr,
    amount: 0,
    assetIndex: assetId,
    suggestedParams: params,
    note: note,
  });

  // opt addr1  into the asset and contract
  const txnwithSigner1 = {
    txn: optInTxn1,
    signer: makeBasicAccountTransactionSigner(user),
  };
  await call(
    user,
    appId,
    "asset_optin",
    [assetId, txnwithSigner1],
    OnApplicationComplete.OptInOC
  );
}

describe("Smart-ASA", () => {
  test("It should return the Smart ASA parameters", async () => {
    const returnVal = await call(user, appId, "get_asset_config", [assetId]);
    //@ts-ignore
    expect(returnVal.length).toBe(12);
  });
  test("It should transfer asset and pay royalty to creator", async () => {
    const addr1 = generateAccount();
    await sendAlgo(user, addr1.addr, 20000000);
    const creatorAddr: string = await getAppCreator(appId);
    const initialBalanceofcreator = await checkAssetBalOfAddr(
      creatorAddr,
      assetId
    );
    await optInToAssetandContract(addr1);

    //do a basic asset transfer txn
    const amount = 100;
    const royaltyAmount = 2;
    const amountSent = amount - royaltyAmount;
    await call(user, appId, "asset_transfer", [
      assetId,
      amount,
      appAddr,
      addr1.addr,
      creatorAddr,
    ]);
    const finalBallanceofaddr1 = await checkAssetBalOfAddr(addr1.addr, assetId);
    const finalBalanceofcreator = await checkAssetBalOfAddr(user.addr, assetId);
    expect(finalBallanceofaddr1).toBe(amountSent);
    console.log(finalBalanceofcreator);
    expect(finalBalanceofcreator - initialBalanceofcreator).toBe(2);
  });

  test("It should delegate account", async () => {
    const addr1 = generateAccount();
    const addr2 = generateAccount();
    await sendAlgo(user, addr1.addr, 20000000);
    await sendAlgo(user, addr2.addr, 20000000);
    await optInToAssetandContract(addr1);
    await optInToAssetandContract(addr2);
    const creatorAddr: string = await getAppCreator(appId);

    const amount = 30;
    //credit the first user with asset
    await call(user, appId, "asset_transfer", [
      assetId,
      amount,
      appAddr,
      addr1.addr,
      creatorAddr,
    ]);

    //delegate second user
    await call(addr1, appId, "asset_delegate", [
      assetId,
      amount / 2,
      addr2.addr,
    ]);
    const balance = await call(user, appId, "get_delegate_allowance", [
      assetId,
      addr1.addr,
      addr2.addr,
    ]);
    if (balance) {
      expect(parseInt(balance?.toString())).toBe(amount / 2);
    }
  });

  test("it should delegate transfer and reduce delegate balance", async () => {
    const addr1 = generateAccount();
    const addr2 = generateAccount();
    const addr3 = generateAccount();
    await sendAlgo(user, addr1.addr, 20000000);
    await sendAlgo(user, addr2.addr, 20000000);
    await sendAlgo(user, addr3.addr, 20000000);
    await optInToAssetandContract(addr1);
    await optInToAssetandContract(addr2);
    await optInToAssetandContract(addr3);
    const amount = 30;
    const creatorAddr: string = await getAppCreator(appId);
    //credit the first user with asset
    await call(user, appId, "asset_transfer", [
      assetId,
      amount,
      appAddr,
      addr1.addr,
      creatorAddr,
    ]);

    //delegate second user
    await call(addr1, appId, "asset_delegate", [
      assetId,
      amount / 2,
      addr2.addr,
    ]);

    const delegatetransferAmount = 10;
    await call(addr2, appId, "delegate_asset_transfer", [
      assetId,
      delegatetransferAmount,
      addr1.addr,
      addr3.addr,
      creatorAddr,
    ]);
    const balance = await call(user, appId, "get_delegate_allowance", [
      assetId,
      addr1.addr,
      addr2.addr,
    ]);
    if (balance) {
      expect(parseInt(balance?.toString())).toBe(
        amount / 2 - delegatetransferAmount
      );
    }
  });
});
