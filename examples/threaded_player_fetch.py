# coding=utf-8
"""
Script to collect SWGOH players from Comlink using parallel threads

This script is intended to be used as a demonstration of how to use background threads and queues to collect player
data from the SWGOH game servers.
"""

import logging
import queue
import signal
import threading
import time

from swgoh_comlink import SwgohComlink

logger = logging.getLogger(__name__)
logging.basicConfig(
        filename=f"player_fetch.log",
        filemode='w',
        encoding='utf-8',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
        )

# How many worker threads should be spawned
NUMBER_OF_WORKERS = 10

shared_status_event_object = threading.Event()
shared_status_event_object.set()

# Queue for storing playerIds to collect
player_q = queue.Queue()

# Queue for storing player data objects
result_q = queue.Queue()

# Queue for storing individual player result response times
response_times_q = queue.Queue()

# List of all threads for keeping track of workers
threads: list[threading.Thread] = []

# List of playerIds to request from Comlink. Can be populated manually below or dynamically from your own
# added code. Example: members = ['PXON5sB4Skmqt4_jCKlszQ', 'OE7WmxEySLaTWBTA0gFpZQ', 'UL3U-hPbRGebQXyTZNYtHA']
members: list[str] = []

# Change the URL below to the appropriate value for your self-hosted Comlink instance
comlink_url = "http://localhost:3000"
comlink = SwgohComlink(comlink_url)

# Let's record how long it takes for the script to run as well as the average time needed for each player data request
start_time = time.time()


# Define a signal handler to handle SIGTERM and SIGINT
def handle_terminate_signal(signum, frame):
    logger.info(f"Received termination signal ({signal.strsignal(signum)}). Stopping threads...")
    shared_status_event_object.clear()


# Register the signal handler for SIGTERM and SIGINT
signal.signal(signal.SIGTERM, handle_terminate_signal)
signal.signal(signal.SIGINT, handle_terminate_signal)


def get_player_worker(
        cl: SwgohComlink,
        player_id_q: queue.Queue,
        player_results_q: queue.Queue,
        response_times_q: queue.Queue, ):
    """
    Retrieves playerId data from a queue, processes it using the SwgohComlink object, and
    places the results into another queue. The function runs in a thread and uses a shared
    event object to determine when to stop processing.

    Args:
        cl (SwgohComlink): The SWGoH API communication object used to retrieve player data.
        player_id_q (queue.Queue): The queue containing player IDs to be processed.
        player_results_q (queue.Queue): The queue where the results, including retrieval time
            and player data, are placed.
        response_times_q (queue.Queue): The queue where the individual player data call response times are placed.
    """
    # Collect the thread name for logging
    t_name = threading.current_thread().name
    logger.info(f"{t_name} started")

    # Run until the shared threading event status is cleared, indicating shutdown
    while shared_status_event_object.is_set():
        logger.info(f"{t_name} thread Event status is set. Waiting for item in queue ...")
        try:
            # Use a blocking queue item retrieval with short timeout to prevent race conditions between threads
            player_id = player_id_q.get(timeout=1.0)
            logger.info(f"{t_name} Received '{player_id}' from queue")
            s_time = time.time()

            # Get the player data from Comlink
            # This should probably be placed in a try/except block, but is not for simplicity of this example
            player = cl.get_player(player_id=player_id)

            t_time = time.time() - s_time
            logger.info(f"{t_name} Player '{player_id}' has been collected in {t_time} seconds.")

            if isinstance(player, dict) and 'rosterUnit' in player:
                logger.info(f"{t_name}   {len(player['rosterUnit'])} units in player roster.")
            else:
                # It would probably be a good idea to place the item back on the player queue
                #
                # player_id_q.put(player_id)
                #
                # We'd still mark the task as complete because we placed the item back in the queue,
                # thereby creating a new item for a thread to process. If we did not mark the task
                # as done, the player_q.join() operation below would block until forcibly closed.
                #
                # player_id_q.task_done()
                #
                # This functionality is not provided in this example because it introduces the need
                # for considerably more complex processing for tracking items that have been
                # re-queued and implementing retry limits to prevent infinite loops
                logger.error(f"{t_name}   Player '{player_id}' has no roster.")

            # Mark the processing of the queue item as complete
            player_id_q.task_done()

            # Place the time taken for the request as well as the player data on the results queue
            response_times_q.put(t_time)
            player_results_q.put(player)
        except queue.Empty:
            # Queue is empty or timeout from get() expired
            logger.info(f"{t_name} Player ID queue is empty.")
            continue
    # Shared thread event status has been cleared. Log a message and return
    logger.info(f"{t_name} Event status has been cleared. Exiting ...")


def player_results_worker(player_results_q: queue.Queue):
    """
    Processes player results from a queue in a threaded environment.

    This function continuously retrieves and processes player results from the
    provided queue while the shared threading event status remains set. It handles
    player result retrieval with a timeout to avoid race conditions, logs relevant
    information about the processing, and gracefully exits when the event status
    is cleared. Processing includes logging player information when the required
    data (e.g., 'name') is present in the player object.

    Args:
        player_results_q (Queue): A thread-safe queue containing player results.
    """
    # Collect the thread name for logging
    t_name = threading.current_thread().name
    logger.info(f"{t_name} started")

    # Run until the shared threading event status is cleared, indicating shutdown
    while shared_status_event_object.is_set():
        logger.info(f"{t_name} thread Event status is set. Waiting for item in queue ...")
        try:
            # Use a blocking queue item retrieval with short timeout to prevent race conditions between threads
            player_obj = player_results_q.get(timeout=1.0)
            if isinstance(player_obj, dict) and 'name' in player_obj:
                # We just output a log message, but this is where any processing of the player response from
                # Comlink would take place.
                logger.info(f"{t_name}   Player '{player_obj['name']}' has been collected.")
            player_results_q.task_done()
        except queue.Empty:
            # Queue is empty or timeout from get() expired
            logger.info(f"{t_name} Player results queue is empty.")
            continue
    # Shared thread event status has been cleared. Log a message and return
    logger.info(f"{t_name} Event status has been cleared. Exiting ...")


def response_time_worker(response_time_q: queue.Queue):
    """
    Continuously processes response times from a queue to calculate and log the average response
    time and total number of processed responses. The worker exits when the shared threading
    event status is cleared.

    Args:
        response_time_q (queue.Queue): A thread-safe queue from which response times are
        retrieved for processing.
    """
    # Collect the thread name for logging
    t_name = threading.current_thread().name
    logger.info(f"{t_name} started")
    fetch_times = 0.0
    count = 0

    # Run until the shared threading event status is cleared, indicating shutdown
    while shared_status_event_object.is_set():
        logger.info(f"{t_name} thread Event status is set. Waiting for item in queue ...")
        try:
            response_time = response_time_q.get(timeout=1.0)
            fetch_times += response_time
            count += 1
            response_time_q.task_done()
        except queue.Empty:
            # Queue is empty or timeout from get() expired
            logger.info(f"{t_name} Player results queue is empty.")
            continue

    # Shared thread event status has been cleared. Log a message and return
    logger.info(f"Average fetch times: {fetch_times / count:.2f} seconds. Total players fetched: {count}")
    logger.info(f"{t_name} Event status has been cleared. Exiting ...")


# Spawn the worker threads
for n in range(NUMBER_OF_WORKERS):
    n += 1
    pt = threading.Thread(
            target=get_player_worker,
            args=(comlink, player_q, result_q, response_times_q,),
            daemon=True,
            name=f"Player ID worker thread-{n}"
            )
    pt.start()
    threads.append(pt)

    rt = threading.Thread(
            target=player_results_worker,
            args=(result_q,),
            daemon=True,
            name=f"Player results worker thread-{n}"
            )
    rt.start()
    threads.append(rt)

rtt = threading.Thread(
        target=response_time_worker,
        args=(response_times_q,),
        daemon=True,
        name=f"Response time worker thread"
        )
rtt.start()
threads.append(rtt)

# Place the list of player Ids on the queue
for member in members:
    logger.info(f"Placing '{member}' in queue ...")
    player_q.put(member)

# Wait for all queue items to be processed
logger.info("Waiting for all items to be processed ...")
player_q.join()
result_q.join()

# Let the worker threads know that the script is shutting down
logger.info("Clearing thread event status ... ")
shared_status_event_object.clear()

# Wait for the response time worker thread to finish processing all queue items
response_times_q.join()

# Wait for all threads to exit
logger.info(f"Stopping threads ...")
for t in threads:
    t.join()

end_time = time.time()
logger.info(f"Total time taken to collect players is {end_time - start_time:.2f} seconds.")
logger.info("All treads have been completed. Exiting ...")
