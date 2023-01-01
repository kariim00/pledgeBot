# Introduction to Pledge bot

As a Discord server owner, it's important to find ways to monetize and sustain your community. That's where Pledge bot comes in. Pledgebot allows users to pay for a monthly role using ETH, ensuring that only those who truly support your server have access to special perks and benefits.

But we don't stop there - we also offer a referral system, rewarding users who bring new members to your server. It's the perfect way to incentivize growth and keep your community thriving.

# Prerequisites

To get started with Pledge bot, you'll need to ensure that you have the following:
- Python 3.8 or higher installed on your system
- The necessary dependencies, which can be downloaded via `pip -r requirements.txt`
- An initialized SQLite3 database using the provided schema:

```sql
CREATE TABLE wallets (uid TEXT, address TEXT, privateKey TEXT, seed TEXT, expiry TEXT, gotRole INT, referral TEXT, txn TEXT);
```

Additionally, you'll need to edit the .env file to specify your Discord API key and other relevant information.

To run the bot, use the following command:

```sh
python3 bot.py
```

With these prerequisites in place, you'll be ready to start using Pledge bot and offering paid subscriptions to your Discord users. Try it out today!