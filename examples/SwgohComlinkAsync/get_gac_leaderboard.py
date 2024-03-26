"""
get_gac_leaderboard.py
Sample script to get either the GAC bracket or league/division leaderboards using Comlink
"""
import asyncio

# Place module imports below this line
from swgoh_comlink import SwgohComlinkAsync


def format_output(lb_list: list) -> tuple[int, int, list]:
    """Calculate the necessary column widths for formatted output based on data provided in tb_list"""
    if not isinstance(lb_list, list):
        raise RuntimeError(
            f"Invalid input. Expected type(list), received type({type(lb_list)}"
        )
    # First create a list of (name, guild, skill) tuples
    output_list = []
    max_name_len = 0
    max_guild_len = 0
    for player in lb_list:
        if len(player["name"]) > max_name_len:
            max_name_len = len(player["name"])
        if player["guild"] is not None:
            if len(player["guild"]["name"]) > max_guild_len:
                max_guild_len = len(player["guild"]["name"])
            output_list.append(
                (
                    player["name"],
                    player["guild"]["name"],
                    player["playerRating"]["playerSkillRating"]["skillRating"],
                )
            )
        else:
            output_list.append(
                (
                    player["name"],
                    "None",
                    player["playerRating"]["playerSkillRating"]["skillRating"],
                )
            )

    return max_name_len + 2, max_guild_len + 2, output_list


async def main():
    # Create instance of SwgohComlink
    comlink = SwgohComlinkAsync()

    """
    The get_gac_leaderboard() method takes several required arguments. The combination of arguments required varies depending
    on the GAC leaderboard desired. The parameters are:

            leaderboard_type: Type 4 is for scanning gac brackets, and only returns results while an event is active.
                                When type 4 is indicated, the "event_instance_id" and "group_id" must also be provided.
                              Type 6 is for the global leaderboards for the league + divisions.
                                When type 6 is indicated, the "league" and "division" arguments must also be provided.
            league: Integer values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium,
                           and kyber respectively. Also accepts string values for each league.
            division: Integer values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                             Also accepts string or int values for each division.
            event_instance_id: When leaderboard_type 4 is indicated, a combination of the event Id and the instance
                                    ID separated by ':'
                                    Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
                                    This information can be obtained from the get_events() method.
            group_id: When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                             by the league and bracketId, separated by :. The number at the end is the bracketId, and
                             goes from 0 to N, where N is the last group of 8 players.
                                Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
            enums: Whether to translate enum values to text [Default: False]


    """

    # Get the Kyber 2 leaderboard
    gac_kyber_2_lb = await comlink.get_leaderboard(
        leaderboard_type=6, league=100, division=20
    )
    await comlink.client.aclose()

    # Output the GAC leaderboard information
    if 'player' in gac_kyber_2_lb:
        name_col_width, guild_col_width, lb_entries = format_output(
            gac_kyber_2_lb["player"]
        )
        for player in lb_entries:
            print(
                f"Player nane: {player[0]:{name_col_width}} "
                + f"Guild: {player[1]:{guild_col_width}} "
                + f"Skill Rating: {player[2]}"
            )
    else:
        print("No GAC is currently running.")


if __name__ == "__main__":
    asyncio.run(main())
