import {
  encodeUint64,
  getApplicationAddress,
  makeApplicationNoOpTxn,
  makeBasicAccountTransactionSigner,
  makeApplicationOptInTxn,
  Transaction,
  ABIContract,
  AtomicTransactionComposer,
  ABIMethod,
  Account,
  TransactionWithSigner,
  OnApplicationComplete,
} from "algosdk";
import { getMethodByName } from "./utils";
// import { appId, user } from "./config";
import { algodClient, submitTransaction } from "./utils";

async function OptIn(user: Account, appId: number) {
  let txId: string;
  let txn;

  // get transaction params
  const params = await algodClient.getTransactionParams().do();

  // deposit
  //@ts-ignore
  const enc = new TextEncoder();
  const depositAmount = 1e6; // 1 ALGO

  // create and send OptIn
  txn = makeApplicationOptInTxn(user.addr, params, appId);
  txId = await submitTransaction(txn, user.sk);

  // display results
  let transactionResponse = await algodClient
    .pendingTransactionInformation(txId)
    .do();
  console.log("Opted-in to app-id:", transactionResponse["txn"]["txn"]["apid"]);
}

export async function call(
  user: Account,
  appId: number,
  method: string,
  methodArgs: any[],
  OnComplete?: OnApplicationComplete
) {
  const params = await algodClient.getTransactionParams().do();
  const newParams = { ...params, fee: 20000 };

  const commonParams = {
    appID: appId,
    sender: user.addr,
    suggestedParams: newParams,
    signer: makeBasicAccountTransactionSigner(user),
  };

  let atc = new AtomicTransactionComposer();

  atc.addMethodCall({
    method: getMethodByName(method),
    methodArgs: methodArgs,
    ...commonParams,
    onComplete: OnComplete,
  });

  const result = await atc.execute(algodClient, 2);
  return result.methodResults[0].returnValue;
}
