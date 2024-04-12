from __future__ import annotations

import asyncio
import sys

import swgoh_comlink.utils as utils
from swgoh_comlink import SwgohComlinkAsync

acl = SwgohComlinkAsync()
cl_logger = utils.get_logger(default_logger=True)


async def main():
    cl_logger.info(" ***** Starting test script ...")
    try:
        cl_logger.info(" ***** Calling get_async_player() as expected ...")
        p = await utils.get_async_player(comlink=acl, player_id="cRdX7yGvS-eKfyDxAAgaYw", allycode=str(314927874))
        sys.stderr.write("\n\nPlayer name is : {}\n\n".format(p['name']))
        if 'name' in p:
            cl_logger.info(" ***** call completed successfully ...")
        else:
            cl_logger.error(" ***** An error occurred while calling get_async_player() ...")
    except ValueError:
        cl_logger.warning(" ***** ValueError raised while calling get_async_player() ...")
    except NameError as exc:
        cl_logger.warning(" ***** Name error raised while calling get_async_player() ...")
        cl_logger.exception(exc)

    try:
        cl_logger.info(" ***** Calling get_async_player() with no player_id nor allycode arguments ...")
        p = await utils.get_async_player(comlink=acl)
        if 'name' in p:
            cl_logger.info(" ***** call completed successfully ...")
        else:
            cl_logger.error(" ***** An error occurred while calling get_async_player() ...")
    except ValueError:
        cl_logger.warning(" ***** ValueError raised while calling get_async_player() ...")
    except NameError as exc:
        cl_logger.warning(" ***** Name error raised while calling get_async_player() ...")
        cl_logger.exception(exc)


if __name__ == "__main__":
    asyncio.run(main())
