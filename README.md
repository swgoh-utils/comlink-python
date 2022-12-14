# comlink-python

## Description

A python wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool.

## Installation
```buildoutcfg
pip install swgoh_comlink
```

## Usage

Usage example:

```python
import swgoh_comlink

comlink = swgoh_comlink.SwgohComlink(host='http://localhost', port='3000')
player_data = comlink.get_player(allycode=245866537)
player_name = player_data['name']
```

# Parameters

- _host_: the hostname where the swgoh-comlink service is running. Defaults to `http://localhost`
- _port_: the tcp port number the swgoh-comlink service is listening on. Defaults to `3000`
- _access_key_: The "public" portion of the shared key used in HMAC request signing. Defaults to '' which disables HMAC signing of requests. Can also be read from the ACCESS_KEY environment variable.
- _secret_key_: The "private" portion of the key used in HMAC request signing. Defaults to '' which disables HMAC signing of requests. Can also be read from the SECRET_KEY environment variable.

## Support

Issues can be reported in [GitLab](https://gitlab.com/swgoh-tools/comlink-python/-/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
