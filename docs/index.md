<div class="center">
<p style="margin: 0 0 10px">
  <img width="208" height="208" src="http://127.0.0.1:8000/swgoh-utils/comlink-python/img/swgoh-utils-icon.png" alt='swgoh-comlink-python'>
</p>
</div>

<h1 class="center" style="font-size: 3rem; margin: -15px 0">
SwgohComlink
</h1>
<br>
<div class="center">
<p>
<img src="https://github.com/swgoh-utils/comlink-python/actions/workflows/tests.yml/badge.svg?branch=1.13.0rc1" alt="Test Suite">
<a href="https://badge.fury.io/py/swgoh-comlink"><img src="https://badge.fury.io/py/swgoh-comlink.svg" alt="PyPI version" height="18"></a></p>
</div>
<div class="center">
<em>A Python wrapper for the <a href="https://github.com/swgoh-utils/swgoh-comlink">swgoh-comlink</a> API service</em>
</div>

---

**SwgohComlink** is a native Python library that provides interface methods to the available endpoints that
the `swgoh-comlink` API service exposes.

The package also includes a collection of utility functions for common tasks while interacting with
the [Star Wars&trade; : Galaxy of Heroes](https://www.ea.com/games/starwars/galaxy-of-heroes) mobile game data.

Before we can get started, the package needs to be installed.

### Install using pip

```shell
$ pip install swgoh-comlink-python
```

!!! note
It is recommended to install the `swgoh-comlink-python` package into a virtual environment, as described in the full
installation instructions below.

## Basic usage

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url="http://localhost:3000")
player = comlink.get_player(allycode=123456789)
```

## Advanced usage

```python
from swgoh_comlink import SwgohComlink

# Create a SwgohComlink instance with links to both the swgoh-comlink and swgoh-stats proxy services
# Also include access key and secret key assignments to prevent unwanted usage
comlink = SwgohComlink(url="http://localhost:3000", stats_url="http://localhost:3223", access_key="someRandomString",
                       secret_key="AnotherSecretRandomString")

# Get player details for a specific allycode. Note the example below is fictitious. Replace with a real
# allycode if trying for real.
player = comlink.get_player(allycode=123456789)

# If the player is a member of a guild, get a list of all the guild members
guild_members = comlink.get_guild(guild_id=player['guildId'])['member']

# The guild member list contains player objects, but there is only a 'playerId' element, no 'allyCode'
guild_member_player_ids = [p['playerId'] for p in guild_members]

# To get the individual guild member allycodes, we need to call either the get_player() or get_player_arena() methods.
# The get_player() method returns the entire character and ship roster for a player, which can be quite large.
# Since we are collecting information for up to 50 players in a guild, it is quicker to use the get_player_arena() method.
# The get_player_arena() method also contains an optional flag that can be used to request just the bare minimum
# information for a player. Setting the 'player_details_only' parameter to 'True' will reduce bandwidth on the network
# and speed up the response time overall

# While we could write a dedicated function to make call to get_player_arena() with a passed in 'player_id' argument,
# leveraging the Python map() function and lambda expression makes a one line example easy to produce.
guild_member_allycodes = list(
    map(lambda x: comlink.get_player_arena(player_id=x, player_details_only=True)['allyCode'], guild_member_player_ids))

```

## Installation

It is recommended to install the `swgoh-comlink-python` package into a virtual environment

```shell
# python3 -m venv venv
# source venv/bin/activate
(venv) # python3 -m pip install swgoh-comlink-python
```

!!! attention "Minimum Python version requirement"
Starting with version 2.0.0 of the `swgoh-comlink-python` library, the minimum Python version required is 3.10
