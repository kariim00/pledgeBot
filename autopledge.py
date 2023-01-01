from discord.ext import commands
import discord, time, requests, os, dotenv, sys, sqlite3, asyncio
from secrets import token_hex
from contextlib import closing
from threading import Thread

if not dotenv.load_dotenv():
    print("please setup the .env file")
    sys.exit()


guild_id = os.getenv("GUILD")  # server id righ click on serve icon and get id
role_id = os.getenv(
    "ROLE"
)  # role id open server settings and copy the wanted role's id
owner = os.getenv("OWNER")
TOKEN = os.getenv("TOKEN")
localhost = os.getenv("LOCALHOST")

if localhost == "true":
    from web3 import Web3
    url = os.getenv("URL")
    w3 = Web3(Web3.HTTPProvider(url))
    
else:
    from web3.auto.infura import w3


def query(uid):
    with closing(sqlite3.connect("wallets.db")) as connection:
        with closing(connection.cursor()) as cursor:
            return cursor.execute(
                "select * from wallets where uid=?", (uid,)
            ).fetchone()


def update(uid, y_n):
    with closing(sqlite3.connect("wallets.db")) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                "UPDATE wallets SET gotRole = ?, expiry = ? WHERE uid=?",
                (y_n, int(time.time() + 30 * 24 * 3600), uid),
            )
            connection.commit()


def gen_account(id, refer):
    seed = "".join([token_hex(10) + " " for _ in range(3)])
    acct = w3.eth.account.create(seed)
    with closing(sqlite3.connect("wallets.db")) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                "INSERT INTO wallets values (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    id,
                    acct.address,
                    acct.privateKey.hex(),
                    seed,
                    int(time.time() + 30 * 24 * 3600),
                    0,
                    refer,
                    "",
                ),
            )
            connection.commit()

    return acct.address


def handle_acc(acc, acc_addy):

    acc_balance = w3.eth.getBalance(acc_addy)
    if acc_balance >= 0.1 * 10**18:
        headers = {"content-type": "application/json", "Authorization": f"Bot {TOKEN}"}
        requests.put(
            f"https://discord.com/api/v8/guilds/{guild_id}/members/{acc}/roles/{role_id}",
            headers=headers,
        )
        drain(acc)
        update(acc, 1)


def drain(id):
    print("draining")
    k = query(id)
    acc_address = k[1]
    acc_privateKey = k[2]
    refer = k[6]
    tx = None
    if refer:
        tx = send_eth(acc_address, acc_privateKey, refer, 20 / 100)[
            "transactionHash"
        ].hex()

    send_eth(acc_address, acc_privateKey, owner, 1)

    with closing(sqlite3.connect("wallets.db")) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute("UPDATE wallets SET txn = ? WHERE uid=?", (tx, id))
            connection.commit()


def send_eth(sender_address, sender_privateKey, reciever_address, percent):

    w3.eth.generateGasPrice()
    print(f"sending to {reciever_address}")
    transaction = {
        "from": sender_address,
        "to": reciever_address,  # owner wallet
        "value": int(w3.eth.getBalance(sender_address) * percent)
        - (21000 * w3.eth.gasPrice),
        "gas": 21000,
        "gasPrice": w3.eth.gasPrice,
        "nonce": w3.eth.getTransactionCount(sender_address),
    }
    signed_txn = w3.eth.account.signTransaction(transaction, sender_privateKey[2:])
    txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(txn_hash)
    return tx_receipt


def check_expiry():
    with closing(sqlite3.connect("wallets.db")) as connection:
        with closing(connection.cursor()) as cursor:
            wallets = cursor.execute(
                "select * from wallets where gotRole = 1"
            ).fetchall()

        for acc in wallets:
            with closing(sqlite3.connect("wallets.db")) as connection:
                with closing(connection.cursor()) as cursor:
                    expiry_date = cursor.execute(
                        "select expiry from wallets where gotRole = 1 and uid=?",
                        (acc[0],),
                    ).fetchone()[0]
                    if int(expiry_date) <= time.time():
                        data = f'{{"roles":["{role_id}"]}}'
                        headers = {
                            "content-type": "application/json",
                            "Authorization": f"Bot {TOKEN}",
                        }
                        update(acc[0], 0)
                        requests.delete(
                            f"https://discord.com/api/v8/guilds/{guild_id}/members/{acc[0]}/roles/{role_id}",
                            headers=headers,
                            data=data,
                        )


def log_loop(poll_interval):
    while True:
        check_expiry()

        with closing(sqlite3.connect("wallets.db")) as connection:
            with closing(connection.cursor()) as cursor:
                wallets = cursor.execute(
                    "select * from wallets where gotRole = 0"
                ).fetchall()

        for acc in wallets:
            try:
                handle_acc(acc[0], acc[1])
            except Exception as e:
                print(e)
        time.sleep(poll_interval)


worker = Thread(target=log_loop, args=([30]), daemon=True)
worker.start()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    while True:
        btcprice = requests.get(
            "http://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        ).json()["bitcoin"]["usd"]
        print(btcprice)
        ethprice = requests.get(
            "http://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "ethereum",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        ).json()["ethereum"]["usd"]
        print(ethprice)
        await bot.change_presence(
            activity=discord.Game(name="Ƀ " + str(btcprice) + " || Ξ " + str(ethprice))
        )
        await asyncio.sleep(60)


@bot.command(name="pledge")
async def grant_role(ctx):
    wallets = query(ctx.author.id)
    args = ctx.message.content
    if len(args) <= 7:
        args = ""
    else:
        args = args[8:]

    if not w3.isAddress(args) and args != "":
        try:
            await ctx.author.send(
                embed=discord.Embed(
                    title="FALSE ADDRESS SUPPLIED !!!",
                    description="Supply a valid address",
                    color=0x00FF00,
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )
        except:
            message = (
                "I couldn't send you a PM!! "
                + ctx.author.mention
                + " Open dms for this server for the time of the pledge process. :smiling_face_with_3_hearts:"
            )
            await ctx.channel.send(
                embed=discord.Embed(
                    title="ERROR! DMS CLOSED!", description=message, color=0x00FF00
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )
        return
    if wallets == None:
        response = gen_account(ctx.author.id, args)
        message = "Deposit 1 eth to \n`" + str(response) + "`:sunglasses:"
        try:
            await ctx.author.send(
                embed=discord.Embed(
                    title="PLEDGE ADDRESS", description=message, color=0x00FF00
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )
        except:
            message = (
                "I couldn't send you a PM!! "
                + ctx.author.mention
                + " Open dms for this server for the time of the pledge process. :smiling_face_with_3_hearts:"
            )
            await ctx.channel.send(
                embed=discord.Embed(
                    title="ERROR! DMS CLOSED!", description=message, color=0x00FF00
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )
    else:
        if int(role_id) in [x.id for x in ctx.author.roles]:
            message = ":partying_face::dancer::partying_face: You are already pledged! let's gooo!!!! :partying_face::dancer::partying_face:"
            await ctx.author.send(
                embed=discord.Embed(
                    title="ALREADY PLEDGED!", description=message, color=0x00FF00
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )

        else:
            message = (
                "you already have a wallet for deposit! :eyes: \n`"
                + str(wallets[1])
                + "`"
            )
            await ctx.author.send(
                embed=discord.Embed(
                    title="WALLET ALREADY PROVIDED", description=message, color=0x00FF00
                ).set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
            )


bot.run(TOKEN)
