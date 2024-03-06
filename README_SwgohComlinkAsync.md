# comlink_python

## SwgohComlinkAsync

## Installation

Install from [PyPi package repository](https://pypi.org/project/swgoh-comlink/) using the following shell command.

```buildoutcfg
mkdir comlink-async
cd comlink-async
git clone --branch SwghComlinkAsyncio https://github.com/swgoh-utils/comlink-python.git
cd comlink-python/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
```

## Usage

Basic default usage example for **asyncio**:

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync


async def async_main():
    comlink = SwgohComlinkAsync()
    player_data = await comlink.get_player(245866537)
    player_name = player_data['name']
    guild_id = player_data['guildId']

    guild = await comlink.get_guild(guild_id)
    guild_name = guild['profile']['name']
    print(f'{player_name=} {guild_name=}')
    await comlink.client_session.close()


if __name__ == '__main__':
    asyncio.run(async_main())

```

# Parameters

- **_url_**: the URL where the swgoh-comlink service is running. Defaults to `http://localhost:3000`
- **_access_key_**: The "public" portion of the shared key used in HMAC request signing. Defaults to `None` which
  disables HMAC signing of requests. Can also be read from the ACCESS_KEY environment variable.
- **_secret_key_**: The "private" portion of the key used in HMAC request signing. Defaults to `None` which disables
  HMAC signing of requests. Can also be read from the SECRET_KEY environment variable.

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

# Examples

Please see the [Examples](examples/SwgohComlinkAsync) folder for more detailed code examples.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
