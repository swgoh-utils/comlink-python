# coding=utf-8
"""
search_for_guilds.py
Sample script to search for guilds by various criteria using Comlink

There are two ways in which guilds can be searched via Comlink. Hence, there are two methods available in the
SwgohComlink library to call upon. One provides searching for guilds by name. The other provides searching for
guilds by criteria.

"""

import argparse

# Place module imports below this line
from swgoh_comlink import SwgohComlink


def search_for_guilds_by_name(comlink: SwgohComlink, name: str) -> dict:
    """Search for guilds by name

    Searching for guilds by name requires at least one argument, a string to search on. The search is very lazy,
    so the more characters provided, the better the match will be. Searching for the string 'a' will return all guilds
    (up to the maximum value of the 'count' parameter) with the letter 'a' anywhere in the name. The default maximum
    response record count is 10.

    Args:
        comlink (SwgohComlink): instance of the SwgohComlink class
        name (str): name of the guild to search for

    Returns:
        dict: dictionary containing the search results

    """
    return comlink.get_guilds_by_name(name)


def output_guilds(guilds: list):
    """Display all guilds in the list"""
    for guild in guilds:
        print(f'{guild["name"]=}')


def search_for_guilds_by_criteria(
        comlink: SwgohComlink,
        min_members: int = 1,
        max_members: int = 50,
        include_invite_only: bool = False,
        min_gp: int = 1,
        max_gp: int = 600000000,
        recent_tbs: list = None,
) -> dict:
    """Search for guilds by a number of criteria

    Searching for guilds by criteria offers the ability to find guilds based by characteristics other than name.

    Args:
        comlink (SwgohComlink): instance of the SwgohComlink class
        min_members (int): Minimum number of members in the guild
        max_members (int): Maximum number of members in the guild
        include_invite_only (bool): Flag indicating whether to include invite only guilds in teh search
        min_gp (int): minimum guild galactic power
        max_gp (int): maximum guild galactic power
        recent_tbs (list): list of the territory battle names the guilds have participated in

    Returns:
        dict: dictionary containing the search results

    Examples:

    """
    criteria = {
        "minMemberCount": min_members,
        "maxMemberCount": max_members,
        "includeInviteOnly": include_invite_only,
        "minGuildGalacticPower": min_gp,
        "maxGuildGalacticPower": max_gp,
        "recentTbParticipatedIn": recent_tbs if recent_tbs else [],
    }
    return comlink.get_guilds_by_criteria(search_criteria=criteria, count=1000)


def get_args():
    """Collect command line arguments and return them"""
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog=Path(__file__).stem,
        description="A sample script to search for guilds by name or criteria.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=55),
    )
    comlink_grp = parser.add_argument_group(
        title="comlink details",
        description="Necessary information for connecting to the comlink service.",
    )
    comlink_grp.add_argument(
        "--url",
        "-u",
        required=True,
        help="The Url for connecting to comlink.",
        nargs="?",
        default="http://localhost:3000",
    )

    search_type = parser.add_subparsers(
        title="search type keywords",
        description="Positional keywords indicating the type of search to perform.",
        required=True,
    )
    name_parser = search_type.add_parser(
        "name",
        help="Search for guilds by name [name --help] for additional details.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=55),
    )
    name_parser.add_argument(
        "name", metavar="NAME", help="The name of the guild to search for."
    )

    criteria_parser = search_type.add_parser(
        "criteria",
        help="Search for guilds based on specified guild characteristics"
             "[criteria --help] for additional details.",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=75),
    )
    criteria_parser.add_argument(
        "--min_member_count",
        "--min",
        help="The minimum number of members in the guild.",
        type=int,
        default=10,
        required=False,
    )
    criteria_parser.add_argument(
        "--max_member_count",
        "--max",
        help="The maximum number of members in the guild.",
        type=int,
        default=50,
        required=False,
    )
    criteria_parser.add_argument(
        "--min_galactic_power",
        "--min_gp",
        help="The minimum galactic power of the guild.",
        type=int,
        default=10000000,
        required=False,
    )
    criteria_parser.add_argument(
        "--max_galactic_power",
        "--max_gp",
        help="The maximum galactic power of the guild.",
        type=int,
        default=600000000,
        required=False,
    )
    criteria_parser.add_argument(
        "--include_invite",
        action="store_true",
        help="Include invitation only guilds.",
        default=False,
        required=False,
    )
    criteria_parser.add_argument(
        "--tbs",
        required=False,
        help="Comma separated list of territory battle names the guilds have recently "
             "participated in.",
    )
    return parser.parse_args()


def main():
    """Main program entry point"""
    args = get_args()

    comlink_url = args.url or None
    comlink = SwgohComlink(url=comlink_url)

    if "name" in args:
        guilds = search_for_guilds_by_name(comlink=comlink, name=args.name)
    else:
        if "tbs" in args and args.tbs is not None:
            tb_list = list(args.tbs.split(","))
        else:
            tb_list = []
        guilds = search_for_guilds_by_criteria(
            comlink=comlink,
            min_members=args.min_member_count,
            max_members=args.max_member_count,
            include_invite_only=args.include_invite,
            min_gp=args.min_galactic_power,
            max_gp=args.max_galactic_power,
            recent_tbs=tb_list,
        )

    output_guilds(guilds=guilds["guild"])
    # print(args)


if __name__ == "__main__":
    main()
