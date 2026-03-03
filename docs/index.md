# SwgohComlink

This project provides:

- `SwgohComlink` for network calls to a running `swgoh-comlink` service.
- `StatCalc` for local stat and GP calculation for game units.

## Quick Start

```python
from swgoh_comlink import SwgohComlink, StatCalc

comlink = SwgohComlink(url="http://localhost:3000")
calc = StatCalc()
```

## Choosing a Stats Method

`SwgohComlink.get_unit_stats()` and `StatCalc.calc_player_stats()` are similar in outcome but different in execution model:

- `SwgohComlink.get_unit_stats()` calls an external `swgoh-stats` service over HTTP (`stats_url`).
- `StatCalc.calc_player_stats()` runs calculations locally in-process using Python game data.

Use `get_unit_stats()` when you already operate against hosted comlink/stat services.  
Use `StatCalc.calc_player_stats()` when you want local/offline control and no dependency on a separate stats container.
