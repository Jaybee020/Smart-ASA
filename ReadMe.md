# Smart ASA

An algorand-smart-asset manager contract that adds royalties and delegate account spending of assets written in pyteal

The contract sends a royalty fee of 1 token for any transfer of the asset between holders.It also adds the function of delegating fellow holders to spend certain amounts of your assets for you.

# Install Dependencies

You need to have sandbox installed. You can do this by cloning the repo here.

```bash
  git clone https://github.com/algorand/sandbox.git
```

In whatever local directory the sandbox should reside. Then:

```bash
cd sandbox
./sandbox up dev
```

# Project Structure

This project is made up of 3 main folders

- contracts
- scripts
- test

## Contracts

The contracts folder contains the pyTeal code used to write the smart contracts.It is compiled to TEAL bytecode and can be deployed to mainnet or testnet.

To compile the pyteal

- Run the python file `smart_asa.py`. This also generates the app.teal bytecode and abi contract.json

## Scripts

This folder contains all the scripts written to interact with the smart contract in typescript.The code to deploy the contract is in `deploy.ts`.You are to input your account credentials in `config.ts`.The atomic transaction composer used to call ABI methods from the contract is in `call.ts`.

To deploy the contract,run

```bash
npx ts-node scripts/deploy.ts
```

This would log the appId to the console. It is to copied and set to the variable appID in config.ts

### Run Tests

The test folder contains the test for the smart asa contract and its interactions via the js sdk.Before running the test,make sure you fund your account on your sandbox node. To fund your account,run the following command

```
  ./sandbox goal clerk send -a AMOUNT -f GOAL_SENDER -t YOUR_ADDRESS
```

To run contracts test,run the following command

```
  npm run test
```
