import { mnemonicToSecretKey, generateAccount } from "algosdk";

const addr = "RQAQ2RX2XGSCNVQSKYC6MTYO3ZQ7LQ7XUBQISV3RTYN6VOYQBUK2N6QCJM";
export const user = mnemonicToSecretKey(
  "void baby seed hockey island move mirror flash ordinary coffee impact pledge lounge mule brown budget response decade impact glue powder whale squeeze abandon feature"
);
export const appId = 215;
export const appAddr =
  "QO2BIQENKKIXITY4MMBN7YFGOTLFB6XTOVJZCNNN6FCS25QBL4HDX73MSE";
export const assetId = 218;

console.log(user.addr);
