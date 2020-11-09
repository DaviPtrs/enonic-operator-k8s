import json
import logging as log
import os
import signal as sig
import sys
import time

import requests as req

# Handles with DEBUG environment variable to change the logging level
DEBUG = bool(os.getenv("DEBUG", "False"))
if DEBUG:
    log_level = log.DEBUG
else:
    log_level = log.INFO
log.basicConfig(
    stream=sys.stdout,
    level=log_level,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
)
log.info("Initializing global parameters")

# Convert Enonic auth user:pass format to a tuple
# with (user, pass) format
# Needed to handle with repository related operations
# (listing repos, restoring snapshots, etc...)
ENONIC_AUTH = os.getenv("ENONIC_AUTH", "su:password")
ENONIC_AUTH.split(":")
ENONIC_AUTH = (ENONIC_AUTH[0], ENONIC_AUTH[1])

# Enonic XP host ip
# Will be localhost if you're using it as a sidecar container 
# (which is the only way to use it at least for now)
XP_HOST = os.getenv("XP_HOST", "localhost")

# Set the endpoint for Statistics API
# This will be used to monitoring the ElasticSearch Cluster
# See docs:
# https://developer.enonic.com/docs/xp/stable/runtime/statistics#monitoring
ES_API_PORT = int(os.getenv("ES_API_PORT", 2609))
ES_API = f"http://{XP_HOST}:{ES_API_PORT}"

# Set the endpoint for Management API
# This will be used to handle with repositories information fetching and
# repository snapshots
# See docs: 
# https://developer.enonic.com/docs/xp/stable/runtime/management#snapshots
REPO_API_PORT = int(os.getenv("REPO_API_PORT", 4848))
REPO_API = f"http://{XP_HOST}:{REPO_API_PORT}"


# This will fetch all repositories and create a snapshot
# for each of them, using the Enonic Management API
def take_snapshot():
    log.info("Initializing steps to create cluster snapshots")

    r = req.get(REPO_API + "/repo/list", auth=ENONIC_AUTH)
    log.debug(f"Repository listing: {r.text}")
    response = json.loads(r.text)
    repoList = list()

    # Getting the repo ids
    for repo in response["repositories"]:
        repoList.append(repo["id"])

    # For each repository, snapshoot it!
    for repo in repoList:
        payload = {"repositoryId": repo}

        log.info(f"Snapshoting {repo}")
        r = req.post(REPO_API + "/repo/snapshot", auth=ENONIC_AUTH, json=payload)
        if r.status_code == 200:
            log.info(f"Snapshot created to repository {repo}")
        else:
            log.error(f"Error to snapshot repository {repo}")
        log.debug(f"Snapshot response: {r.text}")

# Returns a boolean that refers to the ES Cluster health
# The cluster will be healthy if the Monitoring API indicates:
# - that the health is GREEN
# - that the unassigned indexes are 0
def check_cluster_health():
    r = req.get(ES_API + "/cluster.elasticsearch")
    log.debug(f"Cluster info: {r.text}")
    health = json.loads(r.text)["state"]

    r = req.get(ES_API + "/index")
    log.debug(f"Index info: {r.text}")
    unassignedIndex = json.loads(r.text)["summary"]["unassigned"]

    if health == "GREEN" and int(unassignedIndex) == 0:
        log.debug("Cluster is healthy")
        return True
    else:
        log.debug("Cluster is unhealthy")
        return False

# Self explanatory (or explained by the logging message)
def cluster_wait():
    log.info("Waiting cluster to be healthy")
    while True:
        if check_cluster_health():
            break
        else:
            time.sleep(15)

# Perform all required tasks before the application being terminated
# If the ES node (Enonic replica) is master and it's the only one
# in the cluster, then take snapshots. 
# Otherwise, it waits the cluster to be healthy before leaving it
def preStop():
    log.debug("preStop function starting")
    r = req.get(ES_API + "/cluster.elasticsearch")
    log.debug(f"Cluster info: {r.text}")
    rJson = json.loads(r.text)
    isMaster = rJson["localNode"]["isMaster"]
    numNodes = rJson["localNode"]["numberOfNodesSeen"]

    if not isMaster or numNodes > 1:
        log.info("There's no need to take snapshots")
        cluster_wait()
    else:
        take_snapshot()

# Return a boolean that indicates
# if the exit flag exists or not
def get_exit_flag():
    path = "/exit/1"
    return os.path.exists(path)

# If flag is true:
# - create a empty file (using 'touch' unix command) on exit folder
# Otherwise:
# - Remove the created file if exists
def set_exit_flag(flag: bool):
    path = "/exit/1"
    if flag:
        os.system(f"touch {path}")
    else:
        if os.path.exists(path):
            os.remove(path)
    log.debug(f"Setting exitFlag to {flag}")


# Function to handle with SIGTERM signal
# It calls preStop function before telling the application
# that it can be terminated
def handle_sigterm(signalNumber, frame):
    log.info("Exit signal received. Performing pre-stop operations.")

    # Allows the application to be killed because the cluster is unready
    if not check_cluster_ready():
        log.warning("Cluster is not ready. Exiting without pre-tasks...")
        set_exit_flag(True)
        exit(1)

    preStop()
    set_exit_flag(True)
    exit(0)


# Fetch all snapshots and restore all of them
def restore():
    log.info("Starting to restore snapshots...")

    r = req.get(REPO_API + "/repo/snapshot/list", auth=ENONIC_AUTH)
    if r.status_code == 403:
        log.error("Auth error")
        exit(1)

    log.debug(f"Snapshot list: {r.text}")
    snapshots = json.loads(r.text)["results"]
    snapshotIds = list()

    # Getting only the snapshots ids
    for snapshot in snapshots:
        snapshotIds.append(snapshot["name"])

    # For each snapshot, restore it
    for snapshot in snapshotIds:
        payload = {"snapshotName": snapshot}

        log.info(f"Restoring snapshot. Snapshot name: {snapshot}")
        r = req.post(REPO_API + "/repo/snapshot/restore", auth=ENONIC_AUTH, json=payload)
        log.debug(f"Restore request result: {r.text}")
        if r.status_code == 200:
            log.info(f"Snapshot {snapshot} restored!")
        else:
            log.error(f"Failed to restore {snapshot}: {r.text}")
        time.sleep(3)

    # Delete restored snapshots
    # TODO: create a separate function to delete snapshots
    payload = {"snapshotNames": snapshotIds}

    log.info("Deleting remaining snapshots.")
    r = req.post(REPO_API + "/repo/snapshot/delete", auth=ENONIC_AUTH, json=payload)
    if r.status_code == 200:
        log.info("Snapshots deleted")
    else:
        log.error(f"Failed to delete snapshots: {r.text}")

    log.debug(f"Snapshots deletion: {r.text}")


# Check if the cluster is ready to receive requests
# Return a boolean based on Monitoring API status code
def check_cluster_ready():
    try:
        r = req.get(ES_API + "/cluster.elasticsearch")
        if r.status_code == 200:
            log.debug("Cluster is ready")
            return True
    except req.ConnectionError:
        pass
    log.debug("Cluster is not ready")
    return False

# Self explanatory (or explained by the logging message)
def wait_ready_cluster():
    log.info("Waiting for cluster to be ready")
    while True:
        if check_cluster_ready():
            break
        time.sleep(10)

# Define all tasks to be performed just on the application startup
def postStart():
    log.debug("postStart function starting")

    # Set the exit flag to allow the application to be killed
    # if the cluster doesn't get ready 
    set_exit_flag(True)
    wait_ready_cluster()
    # Disallow the application to be killed until all tasks being completed
    set_exit_flag(False)
    time.sleep(5)

    # Get the info if the actual ES node is master or not
    log.info("Getting initial node information")
    r = req.get(ES_API + "/cluster.elasticsearch")
    log.debug(f"Cluster info: {r.text}")
    isMaster = json.loads(r.text)["localNode"]["isMaster"]
    log.info(f"Node is master? {isMaster}")

    # If is master then restore the snapshots
    if isMaster:
        restore()
    else:
        log.info("No need to restore snapshots.")


if __name__ == "__main__":
    # Register SIGTERM with the function  "handle_sigterm" to be executed
    sig.signal(sig.SIGTERM, handle_sigterm)

    postStart()

    while True:
        log.debug("Waiting for SIGTERM")
        time.sleep(3)
