import json
import logging as log
import os
import signal as sig
import sys
import time

import requests as req

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

ENONIC_AUTH = os.getenv("ENONIC_AUTH", "su:password")

XP_HOST = os.getenv("XP_HOST", "localhost")

ES_API_PORT = int(os.getenv("ES_API_PORT", 2609))
ES_API = f"http://{XP_HOST}:{ES_API_PORT}"

REPO_API_PORT = int(os.getenv("REPO_API_PORT", 4848))
REPO_API = f"http://{XP_HOST}:{REPO_API_PORT}"


def take_snapshot():
    log.info("Initializing steps to create cluster snapshots")
    if ENONIC_AUTH is None:
        log.error("There's no Enonic auth information")
        exit(1)

    auth = ENONIC_AUTH.split(":")
    auth = (auth[0], auth[1])
    r = req.get(REPO_API + "/repo/list", auth=auth)
    log.debug(f"Repository listing: {r.text}")
    response = json.loads(r.text)
    repoList = list()

    for repo in response["repositories"]:
        repoList.append(repo["id"])

    for repo in repoList:
        payload = {"repositoryId": repo}

        log.info(f"Snapshoting {repo}")
        r = req.post(REPO_API + "/repo/snapshot", auth=auth, json=payload)
        if r.status_code == 200:
            log.info(f"Repository {repo} snapshoted")
        else:
            log.error(f"Error to snapshot repository {repo}")
        log.debug(f"Snapshot response: {r.text}")


def check_cluster_health():
    r = req.get(ES_API + "/cluster.elasticsearch")
    log.debug(f"Cluster info: {r.text}")
    health = json.loads(r.text)["state"]

    r = req.get(ES_API + "/index")
    log.debug(f"Index info: {r.text}")
    unassignedIndx = json.loads(r.text)["summary"]["unassigned"]

    if health == "GREEN" and int(unassignedIndx) == 0:
        log.debug("Cluster is healthy")
        return True
    else:
        log.debug("Cluster is unhealthy")
        return False


def cluster_wait():
    log.info("Waiting cluster to be healthy")
    while True:
        if check_cluster_health():
            break
        else:
            time.sleep(15)


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


def get_exit_flag():
    path = "/exit/1"
    return os.path.exists(path)


def set_exit_flag(flag: bool):
    path = "/exit/1"
    if flag:
        os.system(f"touch {path}")
    else:
        if os.path.exists(path):
            os.remove(path)
    log.debug(f"Setting exitFlag to {flag}")


def handle_sigterm(signalNumber, frame):
    log.info("Exit signal received. Performing pre-stop operations.")
    if not check_cluster_ready():
        log.warning("Cluster is not ready. Exiting without pre-tasks...")
        set_exit_flag(True)
        exit(1)
    preStop()
    set_exit_flag(True)
    exit(0)


def restore():
    log.info("Starting to restore snapshots...")
    if ENONIC_AUTH is None:
        log.error("There's no Enonic auth information")
        exit(1)

    auth = ENONIC_AUTH.split(":")
    auth = (auth[0], auth[1])

    r = req.get(REPO_API + "/repo/snapshot/list", auth=auth)
    if r.status_code == 403:
        log.error("Auth error")
        exit(1)

    log.debug(f"Snapshot list: {r.text}")
    snapshots = json.loads(r.text)["results"]
    snapshotIds = list()

    for snapshot in snapshots:
        snapshotIds.append(snapshot["name"])

    for snapshot in snapshotIds:
        payload = {"snapshotName": snapshot}

        log.info(f"Restoring snapshot. Snapshot name: {snapshot}")
        r = req.post(REPO_API + "/repo/snapshot/restore", auth=auth, json=payload)
        log.debug(f"Restore request result: {r.text}")
        if r.status_code == 200:
            log.info(f"Snapshot {snapshot} restored!")
        else:
            log.error(f"Failed to restore {snapshot}: {r.text}")
        time.sleep(3)

    # Delete restored snapshots
    payload = {"snapshotNames": snapshotIds}

    log.info("Deleting remaining snapshots.")
    r = req.post(REPO_API + "/repo/snapshot/delete", auth=auth, json=payload)
    if r.status_code == 200:
        log.info("Snapshots deleted")
    else:
        log.error(f"Failed to delete snapshots: {r.text}")

    log.debug(f"Snapshots deletion: {r.text}")


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


def wait_ready_cluster():
    log.info("Waiting for cluster to be ready")
    while True:
        if check_cluster_ready():
            break
        time.sleep(10)


def postStart():
    log.debug("postStart function starting")
    set_exit_flag(True)
    wait_ready_cluster()
    set_exit_flag(False)
    time.sleep(5)

    log.info("Getting initial node information")
    r = req.get(ES_API + "/cluster.elasticsearch")
    log.debug(f"Cluster info: {r.text}")
    isMaster = json.loads(r.text)["localNode"]["isMaster"]
    log.info(f"Node is master? {isMaster}")

    if isMaster:
        restore()
    else:
        log.info("No need to restore snapshots.")


if __name__ == "__main__":
    sig.signal(sig.SIGTERM, handle_sigterm)

    postStart()

    while True:
        log.debug("Waiting for SIGTERM")
        time.sleep(3)
