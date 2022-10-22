import {
  Algodv2,
  Transaction,
  waitForConfirmation,
  makePaymentTxnWithSuggestedParamsFromObject,
  makeAssetTransferTxnWithSuggestedParamsFromObject,
} from "algosdk";
import {
  encodeUint64,
  getApplicationAddress,
  makeApplicationNoOpTxn,
  ABIContract,
  AtomicTransactionComposer,
  ABIMethod,
  Indexer,
  Account,
} from "algosdk";
import { spawnSync } from "child_process";
import { readFileSync } from "fs";

// create client object to connect to sandbox's algod client
const algodToken =
  "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const algodServer = "http://localhost";
const algodPort = 4001;
const indexerPort = 8980;
export const algodClient = new Algodv2(algodToken, algodServer, algodPort);
export const algoIndexer = new Indexer("", algodServer, indexerPort);
// Read in the local contract.json file
const buff = readFileSync("contracts/contract.json");

// Parse the json file into an object, pass it to create an ABIContract object
const contract = new ABIContract(JSON.parse(buff.toString()));

// Utility function to return an ABIMethod by its name
export function getMethodByName(name: string): ABIMethod {
  const m = contract.methods.find((mt: ABIMethod) => {
    return mt.name == name;
  });
  if (m === undefined) throw Error("Method undefined: " + name);
  return m;
}

export async function sendAlgo(
  senderaccount: Account,
  receiverAddr: string,
  amount: number
) {
  let params = await algodClient.getTransactionParams().do();
  const enc = new TextEncoder();
  const note = enc.encode("Hello");
  let txn = makePaymentTxnWithSuggestedParamsFromObject({
    from: senderaccount.addr,
    to: receiverAddr,
    amount: amount,
    suggestedParams: params,
    note: note,
  });
  const txId = await submitTransaction(txn, senderaccount.sk);
  return txId;
}

export async function optInToAsset(user: Account, assetId: number) {
  let params = await algodClient.getTransactionParams().do();
  const enc = new TextEncoder();
  const note = enc.encode("OptIn");
  let txn = makeAssetTransferTxnWithSuggestedParamsFromObject({
    from: user.addr,
    to: user.addr,
    amount: 0,
    assetIndex: assetId,
    suggestedParams: params,
    note: note,
  });
  const txId = await submitTransaction(txn, user.sk);
  return txId;
}

export async function checkAssetBalOfAddr(addr: string, assetId: number) {
  let account = await algodClient.accountInformation(addr).do();
  var assetBalance = 0;
  let assetsOwned = account["assets"];
  assetsOwned.forEach((asset: any) => {
    if (asset["asset-id"] == assetId) {
      assetBalance = asset["amount"];
    }
  });
  return assetBalance;
}

export async function submitTransaction(
  txn: Transaction,
  sk: Uint8Array
): Promise<string> {
  const signedTxn = txn.signTxn(sk);
  const { txId } = await algodClient.sendRawTransaction(signedTxn).do();
  await waitForConfirmation(algodClient, txId, 1000);
  return txId;
}

export function compilePyTeal(path: string): string {
  const pythonProcess = spawnSync(
    "/Users/jaybee/Desktop/Code/Algorand/Smart-ASA/venv/bin/python3",
    [`${path}.py`]
  );
  if (pythonProcess.stderr) console.log(pythonProcess.stderr.toString());
  return pythonProcess.stdout.toString();
}

export async function compileTeal(programSource: string): Promise<Uint8Array> {
  //@ts-ignore
  const enc = new TextEncoder();
  const programBytes = enc.encode(programSource);
  const compileResponse = await algodClient.compile(programBytes).do();
  return new Uint8Array(Buffer.from(compileResponse.result, "base64"));
}
