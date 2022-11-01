from pyteal import *
import json
is_creator = Txn.sender() == Global.creator_address()
is_manager = Txn.sender() == App.globalGet(Bytes("manager_addr"))
smart_asa_id = App.globalGet(Bytes("smart_asa_id"))
current_royalty_amount = App.globalGet(Bytes("royalty_amount"))
current_clawback_addr = App.globalGet(Bytes("clawback_addr"))
current_reserve_addr = App.globalGet(Bytes("reserve_addr"))
current_freeze_addr = App.globalGet(Bytes("freeze_addr"))
current_manager_addr = App.globalGet(Bytes("manager_addr"))


class Smart_ASA_Config(abi.NamedTuple):
    total: abi.Field[abi.Uint64]
    decimals: abi.Field[abi.Uint32]
    default_frozen: abi.Field[abi.Bool]
    royalty_amount: abi.Field[abi.Uint64]
    unit_name: abi.Field[abi.String]
    name: abi.Field[abi.String]
    url: abi.Field[abi.String]
    metadata_hash: abi.Field[abi.DynamicBytes]
    manager_addr: abi.Field[abi.Address]
    reserve_addr: abi.Field[abi.Address]
    freeze_addr: abi.Field[abi.Address]
    clawback_addr: abi.Field[abi.Address]


@ Subroutine(TealType.uint64)
def calculate_circulating_supply(asset_id: Expr):
    smart_asa_reserve = AssetHolding.balance(
        Global.current_application_address(), asset_id
    )
    return Seq(smart_asa_reserve, Int(2**64 - 1) - smart_asa_reserve.value())


@Subroutine(TealType.none)
def set_global_vars(total: Expr, decimals: Expr, default_frozen: Expr, unit_name: Expr, name: Expr, url: Expr, metadata_hash: Expr, manager_addr: Expr, reserve_addr: Expr, freeze_addr: Expr, clawback_addr: Expr):
    return Seq(
        App.globalPut(Bytes("total"), total),
        App.globalPut(Bytes("decimals"), decimals),
        App.globalPut(Bytes("default_frozen"), default_frozen),
        App.globalPut(Bytes("unit_name"), unit_name),
        App.globalPut(Bytes("name"), name),
        App.globalPut(Bytes("url"), url),
        App.globalPut(Bytes("metadata_hash"), metadata_hash),
        App.globalPut(Bytes("manager_addr"), manager_addr),
        App.globalPut(Bytes("reserve_addr"), reserve_addr),
        App.globalPut(Bytes("freeze_addr"), freeze_addr),
        App.globalPut(Bytes("clawback_addr"), clawback_addr),
    )


@ABIReturnSubroutine
def asset_create(total: abi.Uint64, decimals: abi.Uint32, default_frozen: abi.Bool, unit_name: abi.String, name: abi.String, url: abi.String, metadata_hash: abi.DynamicArray[abi.Byte], manager_addr: abi.Address, reserve_addr: abi.Address, freeze_addr: abi.Address, clawback_addr: abi.Address, *, output: abi.Uint64) -> Expr:
    return Seq(
        # Assert that the deployer is the creator and the contract doesn't control an ASA already
        Assert(
            And(
                is_creator,
                Not(smart_asa_id),
                Len(manager_addr.get()) == Int(32),
                Len(freeze_addr.get()) == Int(32),
                Len(reserve_addr.get()) == Int(32),
                Len(clawback_addr.get()) == Int(32)

            )
        ),
        # Create a new ASA
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetConfig,
            # set to max value possible
            TxnField.config_asset_total:  Int(2**64 - 1),
            TxnField.config_asset_decimals: Int(0),
            TxnField.config_asset_default_frozen: Int(1),
            TxnField.config_asset_name: Bytes("SMART-ASA"),
            TxnField.config_asset_unit_name: Bytes("S-ASA"),
            TxnField.config_asset_url: url.get(),
            TxnField.config_asset_metadata_hash: Sha256(Itob(Global.current_application_id())),
            TxnField.config_asset_manager: Global.current_application_address(),
            TxnField.config_asset_reserve: Global.current_application_address(),
            TxnField.config_asset_freeze: Global.current_application_address(),
            TxnField.config_asset_clawback: Global.current_application_address(),
            TxnField.fee: Int(0),
        }),
        InnerTxnBuilder.Submit(),
        App.globalPut(Bytes("smart_asa_id"), InnerTxn.created_asset_id()),
        # Update Global Vars of Smart Contact

        set_global_vars(total.get(), decimals.get(), default_frozen.get(), unit_name.get(), name.get(), url.get(),
                        metadata_hash.encode(), manager_addr.get(), reserve_addr.get(), freeze_addr.get(), clawback_addr.get()),
        output.set(InnerTxn.created_asset_id()),
    )


@ABIReturnSubroutine
def asset_config(asset: abi.Asset, total: abi.Uint64, decimals: abi.Uint32, default_frozen: abi.Bool, unit_name: abi.String, name: abi.String, url: abi.String, metadata_hash: abi.DynamicArray[abi.Byte], manager_addr: abi.Address, reserve_addr: abi.Address, freeze_addr: abi.Address, clawback_addr: abi.Address) -> Expr:
    update_manager = manager_addr.get() != current_manager_addr
    update_reserve = reserve_addr.get() != current_reserve_addr
    update_freeze = freeze_addr.get() != current_freeze_addr
    update_clawback = clawback_addr.get() != current_clawback_addr
    return Seq(

        Assert(
            And(
                is_manager,
                smart_asa_id,
                asset.asset_id() == smart_asa_id,
                total.get() >= calculate_circulating_supply(asset.asset_id())

            )
        ),
        # prevent updating once set to zero address
        If(update_manager).Then(
            Assert(current_manager_addr != Global.zero_address())),
        If(update_reserve).Then(
            Assert(reserve_addr.get() != Global.zero_address())),
        If(update_clawback).Then(
            Assert(clawback_addr.get() != Global.zero_address())),
        If(update_freeze).Then(Assert(freeze_addr.get() != Global.zero_address())),
        # update global vars
        set_global_vars(total.get(), decimals.get(), default_frozen.get(), unit_name.get(), name.get(), url.get(),
                        metadata_hash.encode(), manager_addr.get(), reserve_addr.get(), freeze_addr.get(), clawback_addr.get()),
        Approve()
    )


@ABIReturnSubroutine
def get_asset_config(asset: abi.Asset, *, output: Smart_ASA_Config):
    total = abi.make(abi.Uint64)
    decimals = abi.make(abi.Uint32)
    default_frozen = abi.make(abi.Bool)
    royalty_amount = abi.make(abi.Uint64)
    unit_name = abi.make(abi.String)
    name = abi.make(abi.String)
    url = abi.make(abi.String)
    metadata_hash_str = abi.make(abi.String)
    metadata_hash = abi.make(abi.DynamicBytes)
    manager_addr = abi.make(abi.Address)
    reserve_addr = abi.make(abi.Address)
    freeze_addr = abi.make(abi.Address)
    clawback_addr = abi.make(abi.Address)

    return Seq(
        Assert(
            asset.asset_id() == smart_asa_id
        ),
        total.set(App.globalGet(Bytes("total"))),
        decimals.set(App.globalGet(Bytes("decimals"))),
        default_frozen.set(App.globalGet(Bytes("default_frozen"))),
        royalty_amount.set(current_royalty_amount),
        unit_name.set(App.globalGet(Bytes("unit_name"))),
        name.set(App.globalGet(Bytes("name"))),
        url.set(App.globalGet(Bytes("url"))),
        metadata_hash_str.set(App.globalGet(Bytes("metadata_hash"))),
        metadata_hash.decode(metadata_hash_str.encode()),
        manager_addr.set(current_manager_addr),
        reserve_addr.set(current_reserve_addr),
        freeze_addr.set(current_freeze_addr),
        clawback_addr.set(current_clawback_addr),
        output.set(total, decimals, default_frozen, royalty_amount, unit_name, name, url,
                   metadata_hash, manager_addr, reserve_addr, freeze_addr, clawback_addr),
    )


@ABIReturnSubroutine
def asset_transfer(xfer_asset: abi.Asset, asset_amount: abi.Uint64, asset_sender: abi.Account, asset_receiver: abi.Account, royalty_receiver: abi.Account):
    is_sender = Txn.sender() == asset_sender.address()
    asset_frozen = App.globalGet(Bytes("frozen"))
    is_smartASA_id = xfer_asset.asset_id() == smart_asa_id
    is_clawback = Txn.sender() == current_clawback_addr
    sender_frozen = App.localGet(asset_sender.address(), Bytes("frozen"))
    receiver_frozen = App.localGet(asset_receiver.address(), Bytes("frozen"))
    # only reserve addr can mint token and the tokens must come from the smart contract
    is_minting = And(
        Txn.sender() == current_reserve_addr,
        asset_sender.address() == Global.current_application_address()
    )
    # only reserve addr can burn tokens and reserve can only burn its own tokens to be sent to
    is_burning = And(
        is_sender,
        asset_sender.address() == current_reserve_addr,
        asset_receiver.address() == Global.current_application_address()
    )
    users_opted_in = And(
        smart_asa_id == App.localGet(
            asset_sender.address(), Bytes("smart_asa_id")),
        smart_asa_id == App.localGet(
            asset_receiver.address(), Bytes("smart_asa_id")),
    )
    return Seq(
        Assert(
            And(
                royalty_receiver.address() == Global.creator_address(),
                smart_asa_id,
                is_smartASA_id,
                Len(asset_sender.address()) == Int(32),
                Len(asset_receiver.address()) == Int(32),
                asset_amount.get() > current_royalty_amount
            )
        ),
        # if it is a normal transaction and not clawback addr
        If(And(is_sender, Not(is_clawback))).Then(
            Assert(
                And(
                    Not(sender_frozen),
                    Not(receiver_frozen),
                    Not(asset_frozen),
                    users_opted_in)
            )
        ).ElseIf(is_minting).Then(
            # make sure mint doesnt carry it over the total
            Assert(
                And(
                    Not(asset_frozen),
                    Not(receiver_frozen),
                    smart_asa_id == App.localGet(
                        asset_receiver.address(), Bytes("smart_asa_id")),
                    calculate_circulating_supply(xfer_asset.asset_id(
                    ))+asset_amount.get() <= App.globalGet(Bytes("total"))
                )

            )
        ).ElseIf(is_burning).Then(
            Assert(
                And(
                    Not(asset_frozen),
                    Not(sender_frozen),
                    smart_asa_id == App.localGet(
                        asset_sender.address(), Bytes("smart_asa_id")),
                )
            )
        ).Else(
            Assert(And(is_clawback, users_opted_in)),
        ),
        # Group transaction to transfer asset and pay royalty sum to creator
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: smart_asa_id,
                TxnField.asset_amount: asset_amount.get()-current_royalty_amount,
                TxnField.asset_sender: asset_sender.address(),
                TxnField.asset_receiver: asset_receiver.address(),
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: smart_asa_id,
                TxnField.asset_amount: current_royalty_amount,
                TxnField.asset_sender: asset_sender.address(),
                TxnField.asset_receiver: royalty_receiver.address(),
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@ABIReturnSubroutine
def asset_freeze(freeze_asset: abi.Asset, asset_frozen: abi.Bool):
    is_freezer = Txn.sender() == current_freeze_addr
    return Seq(
        Assert(
            And(
                smart_asa_id,
                freeze_asset.asset_id() == smart_asa_id,
                is_freezer)
        ),
        App.globalPut(Bytes("frozen"), asset_frozen.get())
    )


@ABIReturnSubroutine
def account_freeze(freeze_asset: abi.Asset, freeze_account: abi.Account, asset_frozen: abi.Bool):
    is_freezer = Txn.sender() == current_freeze_addr
    return Seq(
        Assert(
            And(
                smart_asa_id,
                freeze_asset.asset_id() == smart_asa_id,
                Len(freeze_account.address()) == Int(32),
                smart_asa_id == App.localGet(
                    freeze_account.address(), Bytes("smart_asa_id")),
                is_freezer,
            )
        ),

        App.localPut(freeze_account.address(),
                     Bytes("frozen"), asset_frozen.get())
    )


@ABIReturnSubroutine
def get_asset_frozen(freeze_asset: abi.Asset, *, output: abi.Bool):
    return Seq(
        Assert(
            And(
                smart_asa_id,
                freeze_asset.asset_id() == smart_asa_id)

        ),
        output.set(App.globalGet(Bytes("frozen")))
    )


@ABIReturnSubroutine
def get_account_frozen(freeze_asset: abi.Asset, freeze_account: abi.Account, *, output: abi.Bool):
    return Seq(
        Assert(
            And(
                smart_asa_id,
                freeze_asset.asset_id() == smart_asa_id,
                Len(freeze_account.address()) == Int(32),
                smart_asa_id == App.localGet(
                    freeze_account.address(), Bytes("smart_asa_id")))
        ),
        output.set(App.localGet(freeze_account.address(), Bytes("frozen")))
    )


@ABIReturnSubroutine
def get_circulating_supply(asset: abi.Asset, *, output: abi.Uint64):
    return Seq(
        Assert(
            And(
                smart_asa_id,
                asset.asset_id() == smart_asa_id)

        ),
        output.set(calculate_circulating_supply(asset.asset_id()))

    )


@ABIReturnSubroutine
def asset_destroy(destroy_asset: abi.Asset):
    return Seq(
        Assert(
            And(
                smart_asa_id,
                destroy_asset.asset_id() == smart_asa_id),
            is_manager

        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.fee: Int(0),
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset: smart_asa_id,
            }
        ),
        InnerTxnBuilder.Submit(),
        # re-initialize global variables by creating again
        handle_Creation,
        Approve()
    )


@ABIReturnSubroutine
def asset_optin(optin_asset: abi.Asset, optin_txn: abi.AssetTransferTransaction):
    is_frozen = App.globalGet(Bytes("default_frozen"))
    asset_balance = AssetHolding.balance(
        Txn.sender(), optin_asset.asset_id())
    has_opted_in = asset_balance.hasValue()
    return Seq(
        asset_balance,
        Assert(
            And(
                smart_asa_id,
                optin_asset.asset_id() == smart_asa_id,
                has_opted_in,
                optin_txn.get().type_enum() == TxnType.AssetTransfer,
                optin_txn.get().asset_amount() == Int(0),
                optin_txn.get().xfer_asset() == smart_asa_id,
                optin_txn.get().sender() == Txn.sender(),
                optin_txn.get().asset_receiver() == Txn.sender(),
                optin_txn.get().asset_close_to() == Global.zero_address(),
            )
        ),
        App.localPut(Txn.sender(), Bytes("smart_asa_id"), smart_asa_id),
        App.localPut(Txn.sender(), Bytes("frozen"), Int(0)),
        If(Or(asset_balance.value() > Int(0), is_frozen)).Then(
            App.localPut(Txn.sender(), Bytes("frozen"), Int(1))),
        Approve()
    )


@ABIReturnSubroutine
def asset_optout(optout_asset: abi.Asset, closeto_account: abi.Account):
    closeto_optedIn = smart_asa_id == App.localGet(
        closeto_account.address(), Bytes("smart_asa_id"))
    sender_optedIn = closeto_optedIn = smart_asa_id == App.localGet(
        Txn.sender(), Bytes("smart_asa_id"))
    asa_optout_tx_index = Txn.group_index()+Int(1)
    asset_frozen = App.globalGet(Bytes("frozen"))
    creator = AssetParam.creator(optout_asset.asset_id())
    account_balance = AssetHolding.balance(
        Txn.sender(), optout_asset.asset_id())
    account_frozen = App.localGet(Txn.sender(), Bytes("frozen"))
    closeto_frozen = App.localGet(closeto_account.address(), Bytes("frozen"))
    return Seq(
        Assert(
            And(
                optout_asset.asset_id() == smart_asa_id,
                Len(closeto_account.address()) == Int(32),
                smart_asa_id,
                Global.group_size() > asa_optout_tx_index,
                Gtxn[asa_optout_tx_index].type_enum() == TxnType.AssetTransfer,
                Gtxn[asa_optout_tx_index].sender() == Txn.sender(),
                Gtxn[asa_optout_tx_index].xfer_asset() == smart_asa_id,
                Gtxn[asa_optout_tx_index].asset_amount() == Int(0),
                Gtxn[asa_optout_tx_index].asset_close_to()
                == Global.current_application_address(),
            )
        ),
        creator,

        If(creator.hasValue()).Then(
            Assert(sender_optedIn),
            If(Or(asset_frozen, account_frozen, closeto_frozen)).Then(
                Assert(closeto_account.address() ==
                       Global.current_application_address())
            ),
            If(closeto_account.address() != Global.current_application_address()).Then(
                Assert(closeto_optedIn)
            ),
            account_balance,
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: smart_asa_id,
                    TxnField.asset_amount: account_balance.value(),
                    TxnField.asset_sender: Txn.sender(),
                    TxnField.asset_receiver: closeto_account.address(),
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
        ),
        Approve()
    )


# Give access to another account to spend out of your tokens
@ABIReturnSubroutine
def asset_delegate(delegate_asset: abi.Asset, amount: abi.Uint64, spender: abi.Account):
    asset_frozen = App.globalGet(Bytes("default_frozen"))
    is_smartASA_id = smart_asa_id == delegate_asset.asset_id()
    owner_optedIn = smart_asa_id == App.localGet(
        Txn.sender(), Bytes("smart_asa_id"))
    owner_frozen = App.localGet(Txn.sender(), Bytes("frozen"))
    owner_balance = AssetHolding.balance(
        Txn.sender(), delegate_asset.asset_id()
    )
    spender_optedIn = smart_asa_id == App.localGet(
        spender.address(), Bytes("smart_asa_id"))
    spender_frozen = App.localGet(spender.address(), Bytes("frozen"))
    return Seq(
        # check spender and owner are opted in and are not frozen and you cant delegate yourself
        Assert(
            And(
                smart_asa_id,
                spender.address() != Txn.sender(),
                Not(asset_frozen),
                is_smartASA_id,
                owner_optedIn,
                Not(owner_frozen),
                spender_optedIn,
                Not(spender_frozen)
            )
        ),
        owner_balance,
        # assert that amount to be delegated is not more than user balance
        Assert(
            And(
                owner_balance.hasValue(),
                amount.get() <= owner_balance.value()
            )
        ),
        App.localPut(Txn.sender(), spender.address(), amount.get()),
        Approve()
    )


@ABIReturnSubroutine
def get_delegate_allowance(delegate_asset: abi.Asset, owner: abi.Account, spender: abi.Account, *, output: abi.Uint64):
    is_smartASA_id = delegate_asset.asset_id() == smart_asa_id
    owner_optedIn = smart_asa_id == App.localGet(
        owner.address(), Bytes("smart_asa_id"))
    spender_optedIn = smart_asa_id == App.localGet(
        spender.address(), Bytes("smart_asa_id"))
    return Seq(
        Assert(
            And(
                smart_asa_id,
                is_smartASA_id,
                owner_optedIn,
                spender_optedIn
            ),
        ),
        output.set(App.localGet(owner.address(), spender.address()))
    )


@ABIReturnSubroutine
def delegate_asset_transfer(xfer_asset: abi.Asset, asset_amount: abi.Uint64, asset_owner: abi.Account, asset_receiver: abi.Account, royalty_receiver: abi.Account):
    asset_frozen = App.globalGet(Bytes("default_frozen"))
    is_smartASA_id = xfer_asset.asset_id() == smart_asa_id
    owner_optedIn = smart_asa_id == App.localGet(
        asset_owner.address(), Bytes("smart_asa_id"))
    owner_frozen = App.localGet(asset_owner.address(), Bytes("frozen"))
    spender_optedIn = App.localGet(Txn.sender(), Bytes("smart_asa_id"))
    spender_frozen = App.localGet(Txn.sender(), Bytes("frozen"))
    spender_allowance = App.localGet(asset_owner.address(), Txn.sender())
    return Seq(
        Assert(
            And(
                royalty_receiver.address() == Global.creator_address(),
                smart_asa_id,
                Not(asset_frozen),
                is_smartASA_id,
                owner_optedIn,
                Not(owner_frozen),
                spender_optedIn,
                Not(spender_frozen),
                asset_amount.get() <= spender_allowance,
                asset_amount.get() > current_royalty_amount
            )
        ),
        App.localPut(asset_owner.address(), Txn.sender(),
                     spender_allowance-asset_amount.get()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: smart_asa_id,
                TxnField.asset_amount: asset_amount.get()-current_royalty_amount,
                TxnField.asset_sender: asset_owner.address(),
                TxnField.asset_receiver: asset_receiver.address(),
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Next(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: smart_asa_id,
                TxnField.asset_amount: current_royalty_amount,
                TxnField.asset_sender: asset_owner.address(),
                TxnField.asset_receiver: royalty_receiver.address(),
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),

    )


# store the deployer of the contract in global storage and initialize global vars
handle_Creation = Seq(
    App.globalPut(Bytes("smart_asa_id"), Int(0)),
    App.globalPut(Bytes("royalty_amount"), Int(2)),
    App.globalPut(Bytes("frozen"), Int(0)),
    set_global_vars(Int(0), Int(0), Int(0), Bytes(""), Bytes(""), Bytes(""), Bytes(
        ""), Global.zero_address(), Global.zero_address(), Global.zero_address(), Global.zero_address()),
    Approve()


)

# handle routing logic of your contract
router = Router(
    name="Smart ASA",
    bare_calls=BareCallActions(
        no_op=OnCompleteAction(
            action=handle_Creation, call_config=CallConfig.CREATE
        ),
        opt_in=OnCompleteAction(
            action=Reject(), call_config=CallConfig.CALL
        ),
        clear_state=OnCompleteAction(
            action=Reject(), call_config=CallConfig.CALL
        ),
        close_out=OnCompleteAction(
            action=Reject(), call_config=CallConfig.CALL
        ),
        # Prevent updating and deleting of this application
        update_application=OnCompleteAction(
            action=Reject(), call_config=CallConfig.CALL
        ),
        delete_application=OnCompleteAction(
            action=Reject(), call_config=CallConfig.CALL
        ),

    )
)

router.add_method_handler(asset_create)
# router.add_method_handler(asset_config)
router.add_method_handler(get_asset_config)
router.add_method_handler(
    asset_optin, method_config=MethodConfig(opt_in=CallConfig.CALL))
router.add_method_handler(asset_transfer)
# router.add_method_handler(asset_freeze)
# router.add_method_handler(get_asset_frozen)
# router.add_method_handler(get_account_frozen)
# router.add_method_handler(get_circulating_supply)
# router.add_method_handler(asset_destroy)
# router.add_method_handler(
#     asset_optout, method_config=MethodConfig(close_out=CallConfig.CALL))
router.add_method_handler(asset_delegate)
router.add_method_handler(get_delegate_allowance)
router.add_method_handler(delegate_asset_transfer)


approval_program, clear_state_program, contract = router.compile_program(
    version=7, optimize=OptimizeOptions(scratch_slots=True)
)


with open("contracts/app.teal", "w") as f:
    f.write(approval_program)

with open("contracts/clear.teal", "w") as f:
    f.write(clear_state_program)


with open("contracts/contract.json", "w") as f:
    f.write(json.dumps(contract.dictify(), indent=4))


if __name__ == "__main__":
    print(approval_program)
