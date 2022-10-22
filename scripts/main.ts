import algosdk, {
  encodeObj,
  makeAssetTransferTxnWithSuggestedParamsFromObject,
  makeBasicAccountTransactionSigner,
  OnApplicationComplete,
} from "algosdk";
import { call } from "./call";
import { appAddr, appId, assetId, user } from "./config";
import sha512 from "crypto-js/sha512";
import sha3 from "crypto-js/sha3";
import { Hash } from "node:crypto";
import { enc, lib, SHA256 } from "crypto-js";
import { sha512_256 } from "js-sha512";
import {
  algodClient,
  algoIndexer,
  checkAssetBalOfAddr,
  optInToAsset,
  sendAlgo,
} from "./utils";

(async () => {
  const ASAProps = {
    applicationId: 16,
  };
  const hash = SHA256(JSON.stringify(ASAProps)).toString(enc.Base64);
  var buff = Buffer.from(hash, "base64");
  const encode = Uint8Array.from(buff);
  // sendAlgo to smart contract for it to have a min balance
  await sendAlgo(user, appAddr, 1000000);
  const returnValue = await call(user, appId, "asset_create", [
    10000,
    10,
    false,
    "JBT",
    "Jaybee Token",
    "",
    encode,
    user.addr,
    user.addr,
    user.addr,
    user.addr,
  ]);
  if (returnValue) {
    const params = await algodClient.getTransactionParams().do();
    const enc = new TextEncoder();
    const note = enc.encode("OptIn");
    let optInTxn2 = makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: user.addr,
      to: user.addr,
      amount: 0,
      assetIndex: parseInt(returnValue.toString()),
      suggestedParams: params,
      note: note,
    });
    const txnwithSigner2 = {
      txn: optInTxn2,
      signer: makeBasicAccountTransactionSigner(user),
    };

    await call(
      user,
      appId,
      "asset_optin",
      [parseInt(returnValue.toString()), txnwithSigner2],
      OnApplicationComplete.OptInOC
    );
  }
})();
