import {
  mnemonicToSecretKey,
  generateAccount,
  getApplicationAddress,
} from "algosdk";
import { algoIndexer } from "./utils";

const addr = "RQAQ2RX2XGSCNVQSKYC6MTYO3ZQ7LQ7XUBQISV3RTYN6VOYQBUK2N6QCJM";
export const user = mnemonicToSecretKey(
  "void baby seed hockey island move mirror flash ordinary coffee impact pledge lounge mule brown budget response decade impact glue powder whale squeeze abandon feature"
);
export const appId = 961;
export const appAddr = getApplicationAddress(appId);

export const assetId = 964;

export async function getAppCreator(applId: number) {
  const appData = await algoIndexer.lookupApplications(applId).do();
  const appCreator = appData.application.params.creator;
  return appCreator;
}

console.log(user.addr);
