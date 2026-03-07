"""
streaming_guild_roster_advanced.py
Advanced example: fetch all guild member profiles concurrently with retry logic,
error handling, data validation, and optional verbose/debug timing output.

Usage:
    python streaming_guild_roster_advanced.py <allycode_or_guild_id> [options]

    # Fetch guild by ally code with verbose timing
    python streaming_guild_roster_advanced.py 314927874 -v

    # Fetch guild by guild ID with debug output and 5 retries
    python streaming_guild_roster_advanced.py 8RhppbbqR_ShmjY5S6ZtQg -d -r 5

Unlike the basic streaming_guild_roster.py example, this version:
  - Accepts ally code or guild ID as a CLI argument
  - Does NOT cancel all fetches when a single member fetch fails
  - Retries failed fetches with exponential backoff
  - Validates response data structure
  - Provides colored terminal output for warnings and errors
  - Tracks per-fetch and aggregate timing statistics
"""
import sys

if sys.version_info < (3, 11):
    sys.exit("This example requires Python 3.11+ (asyncio.TaskGroup support).")

import argparse
import asyncio
import statistics
import time

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException

# ---------------------------------------------------------------------------
# ANSI color codes (no external dependencies)
# ---------------------------------------------------------------------------
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[32m"
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Keys expected in a valid player response
_REQUIRED_PLAYER_KEYS = {"name", "allyCode"}

# Base delay (seconds) for exponential backoff
_BACKOFF_BASE = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch all guild member profiles concurrently with retry logic."
    )
    parser.add_argument(
        "identifier",
        help="Ally code (numeric) or guild ID (alphanumeric string)",
    )
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts per member fetch (default: 3)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show per-fetch timing information",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Show detailed debug output including retry delays and response validation",
    )
    parser.add_argument(
            "--host",
            default="localhost",
            help="Comlink server host/IP (default: localhost)",
            )
    parser.add_argument(
            "--port",
            type=int,
            default=3200,
            help="Comlink server port (default: 3000)",
            )
    return parser.parse_args()


def is_allycode(identifier: str) -> bool:
    """Determine if the identifier is an ally code (all digits) or a guild ID."""
    return identifier.isdigit()


def extract_gp(player: dict) -> int:
    """Extract galactic power from a player profile dict."""
    for stat in player.get("profileStat", []):
        if stat.get("nameKey") == "STAT_GALACTIC_POWER_ACQUIRED_NAME":
            return int(stat.get("value", 0))
    return 0


def validate_player_response(data: dict, debug: bool = False) -> bool:
    """Validate that the response contains expected player data keys."""
    if not isinstance(data, dict):
        if debug:
            print(f"  {DIM}[debug] Response is not a dict: {type(data)}{RESET}")
        return False
    missing = _REQUIRED_PLAYER_KEYS - data.keys()
    if missing:
        if debug:
            print(f"  {DIM}[debug] Response missing keys: {missing}{RESET}")
        return False
    return True


async def fetch_member(
    comlink: SwgohComlinkAsync,
    player_id: str,
    index: int,
    total: int,
    max_retries: int,
    verbose: bool = False,
    debug: bool = False,
) -> dict | None:
    """
    Fetch a single guild member's profile with retry logic.

    Returns the player dict on success, or None if all retries are exhausted.
    Exceptions are caught internally so that asyncio.TaskGroup does not cancel
    sibling tasks.
    """
    for attempt in range(max_retries):
        fetch_start = time.perf_counter()
        try:
            player = await comlink.get_player(player_id=player_id)
            fetch_elapsed = time.perf_counter() - fetch_start

            # Validate response structure
            if not validate_player_response(player, debug=debug):
                raise ValueError(
                    f"Invalid response structure for player_id={player_id}"
                )

            gp = extract_gp(player)
            timing_str = f" {DIM}({fetch_elapsed:.2f}s){RESET}" if verbose or debug else ""
            print(f"  {GREEN}[{index}/{total}]{RESET} {player['name']} — GP: {gp:,}{timing_str}")
            return player

        except (SwgohComlinkException, ValueError, KeyError, Exception) as exc:
            fetch_elapsed = time.perf_counter() - fetch_start
            remaining = max_retries - attempt - 1

            if remaining > 0:
                delay = _BACKOFF_BASE * (2 ** attempt)
                print(
                    f"  {YELLOW}{BOLD}⚠ WARNING{RESET}{YELLOW} "
                    f"[{index}/{total}] Attempt {attempt + 1}/{max_retries} failed "
                    f"for player_id={player_id}: {exc}{RESET}"
                )
                if debug:
                    print(
                        f"  {DIM}[debug] Fetch took {fetch_elapsed:.2f}s | "
                        f"Retrying in {delay:.1f}s | "
                        f"{remaining} attempt(s) remaining{RESET}"
                    )
                await asyncio.sleep(delay)
            else:
                print(
                    f"  {RED}{BOLD}✗ FAILED{RESET}{RED} "
                    f"[{index}/{total}] All {max_retries} attempts exhausted "
                    f"for player_id={player_id}: {exc}{RESET}"
                )
                return None


async def main():
    args = parse_args()
    verbose = args.verbose or args.debug
    debug = args.debug

    async with SwgohComlinkAsync(host=args.host, port=args.port) as comlink:
        # Step 1: Resolve guild ID
        if is_allycode(args.identifier):
            if debug:
                print(f"{DIM}[debug] Detected ally code, resolving player profile...{RESET}")
            resolve_start = time.perf_counter()
            try:
                player = await comlink.get_player(allycode=int(args.identifier))
            except SwgohComlinkException as exc:
                print(f"{RED}Failed to resolve ally code {args.identifier}: {exc}{RESET}")
                return
            guild_id = player.get("guildId")
            if not guild_id:
                print(f"{RED}Player {player.get('name', 'Unknown')} is not in a guild.{RESET}")
                return
            if debug:
                print(f"{DIM}[debug] Player lookup took {time.perf_counter() - resolve_start:.2f}s{RESET}")
            print(f"Player: {player['name']}")
        else:
            guild_id = args.identifier
            if debug:
                print(f"{DIM}[debug] Using provided guild ID: {guild_id}{RESET}")

        # Step 2: Fetch guild data
        if debug:
            print(f"{DIM}[debug] Fetching guild data...{RESET}")
        guild_start = time.perf_counter()
        try:
            guild = await comlink.get_guild(guild_id)
        except SwgohComlinkException as exc:
            print(f"{RED}Failed to fetch guild {guild_id}: {exc}{RESET}")
            return
        if debug:
            print(f"{DIM}[debug] Guild lookup took {time.perf_counter() - guild_start:.2f}s{RESET}")

        guild_name = guild.get("profile", {}).get("name", guild.get("name", "Unknown"))
        members = guild.get("member", [])
        member_ids = [m.get("playerId") for m in members if m.get("playerId")]
        total = len(member_ids)

        print(f"Guild:  {guild_name}")
        print(f"Fetching {total} member profiles (max {args.retries} retries each)...\n")

        # Step 3: Fetch all members concurrently using TaskGroup
        fetch_times: list[float] = []
        results: list[dict | None] = []
        overall_start = time.perf_counter()

        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    fetch_member(
                        comlink, pid, i + 1, total,
                        max_retries=args.retries,
                        verbose=verbose,
                        debug=debug,
                    )
                )
                for i, pid in enumerate(member_ids)
            ]

        results = [task.result() for task in tasks]
        overall_elapsed = time.perf_counter() - overall_start

        # Step 4: Summary
        successful = [r for r in results if r is not None]
        failed_count = len(results) - len(successful)

        # Collect per-member GP
        total_gp = sum(extract_gp(p) for p in successful)

        print(f"\n{'=' * 60}")
        print(f"  {BOLD}Results{RESET}")
        print(f"{'=' * 60}")
        print(f"  Members fetched: {GREEN}{len(successful)}{RESET} / {total}")
        if failed_count:
            print(f"  Failed:          {RED}{failed_count}{RESET}")
        print(f"  Combined GP:     {total_gp:,}")
        print(f"  Total time:      {overall_elapsed:.2f}s")

        if verbose and successful:
            # Recalculate per-member fetch times is not possible retroactively,
            # so show aggregate stats from wall clock
            avg_time = overall_elapsed / len(successful) if successful else 0
            print(f"\n  {CYAN}Timing{RESET}")
            print(f"  Avg per member (wall / count): {avg_time:.2f}s")
            print(f"  Effective throughput: {len(successful) / overall_elapsed:.1f} members/s")


asyncio.run(main())
