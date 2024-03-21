# SwgohComlinkAsync

The SwgohComlinkAsync module implements the same methods as SwgohComlink with async http requests. It is intended
to be used in implementations that require interactions with the comlink library via asynchronous methods.

## Usage

Basic default usage example for **asyncio**:

```python
import asyncio
from comlink_python import SwgohComlinkAsync


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

### Parameters

- **_url_**: the URL where the swgoh-comlink service is running. Defaults to `http://localhost:3000`
- **_access_key_**: The "public" portion of the shared key used in HMAC request signing. Defaults to `None` which
  disables HMAC signing of requests. Can also be read from the ACCESS_KEY environment variable.
- **_secret_key_**: The "private" portion of the key used in HMAC request signing. Defaults to `None` which disables
  HMAC signing of requests. Can also be read from the SECRET_KEY environment variable.

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

## Module Methods

Complete details for the SwgohComlinkAsync module can be found [here]()

## Examples

Please see the [Examples](https://github.com/swgoh-utils/comlink-python/tree/main/examples/SwgohComlinkAsync) folder for
more detailed code examples.

