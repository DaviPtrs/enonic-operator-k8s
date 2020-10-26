import signal as sig
import os
import time
import requests as req
import json
from datetime import datetime

ENONIC_AUTH = os.getenv('ENONIC_AUTH', "su:password")

XP_HOST = os.getenv('XP_HOST', 'localhost')

ES_API_PORT = int(os.getenv('ES_API_PORT', 2609))
ES_API = f"http://{XP_HOST}:{ES_API_PORT}"

REPO_API_PORT = int(os.getenv('REPO_API_PORT', 4848))
REPO_API = f"http://{XP_HOST}:{REPO_API_PORT}"

def take_snapshot():
    if ENONIC_AUTH is None:
        print("There's no Enonic auth information")
        exit(1)

    auth = ENONIC_AUTH.split(':')
    auth = (auth[0], auth[1])
    r = req.get(REPO_API + "/repo/list", auth=auth)
    response = json.loads(r.text)
    print(f"repo list\n{response}")
    repoList = list()

    for repo in response['repositories']:
        repoList.append(repo['id'])

    for repo in repoList:
        payload = {"repositoryId": repo}

        r = req.post(REPO_API + '/repo/snapshot', auth=auth, json=payload)
        print(f"snapshot {repo}\n{r.text}")



def check_cluster_health():
    r = req.get(ES_API + '/cluster.elasticsearch')
    health = json.loads(r.text)['state']

    r = req.get(ES_API + '/index')
    unassignedIndx = json.loads(r.text)['summary']['unassigned']

    if health == "GREEN" and int(unassignedIndx) == 0:
        return True
    else:
        return False

def cluster_wait():
    while True:
        if check_cluster_health():
            break
        else:
            time.sleep(15)

def preStop():
    r = req.get(ES_API + '/cluster.elasticsearch')
    rJson = json.loads(r.text)
    print(f"cluster info\n{rJson}")
    isMaster = rJson['localNode']['isMaster']
    numNodes = rJson['localNode']['numberOfNodesSeen']

    if isMaster == False or numNodes > 1:
        print("cluster wait")
        cluster_wait()
    else:
        print("snapshot init")
        take_snapshot()

def get_exit_flag():
    path = '/exit/1'
    return os.path.exists(path)

def set_exit_flag(flag: bool):
    path = '/exit/1'
    if flag:
        os.system(f'touch {path}')
    else:
        if os.path.exists(path):
            os.remove(path)
    print(f"exitflag = {flag}")

def handle_sigterm(signalNumber, frame):
    print("preStop init")
    if not check_cluster_ready():
        set_exit_flag(True)
        exit(1)
    preStop()
    set_exit_flag(True)
    exit(0)

def restore():
    if ENONIC_AUTH is None:
        print("There's no Enonic auth information")
        exit(1)

    auth = ENONIC_AUTH.split(':')
    auth = (auth[0], auth[1])

    r = req.get(REPO_API + "/repo/snapshot/list", auth=auth)
    if r.status_code == 403:
        print("Auth error")
        exit(1)
        
    print(f"snapshot list\n{r.text}")
    snapshots = json.loads(r.text)['results']
    snapshotIds = list()

    for snapshot in snapshots:
        snapshotIds.append(snapshot['name'])
    
    for snapshot in snapshotIds:
        payload = {"snapshotName": snapshot}

        r = req.post(REPO_API + '/repo/snapshot/restore', auth=auth, json=payload)
        print(f"snapshot {snapshot}\n{r.text}")

        time.sleep(3)
    
    # Delete restored snapshots
    payload = {"snapshotNames": snapshotIds}

    r = req.post(REPO_API + '/repo/snapshot/delete', auth=auth, json=payload)
    print(f"snapshot delete\n{r.text}")

def check_cluster_ready():
    try:
        r = req.get(ES_API + '/cluster.elasticsearch')
        if r.status_code == 200:
            return True
    except req.ConnectionError:
        pass
    return False

def wait_ready_cluster():
    while True:
        ready = check_cluster_ready()
        print(f"cluster ready: {ready}")
        if ready:
            break
        time.sleep(10)

def postStart():
    print("postStart init")
    set_exit_flag(True)
    wait_ready_cluster()
    set_exit_flag(False)
    time.sleep(5)

    r = req.get(ES_API + '/cluster.elasticsearch')
    isMaster = json.loads(r.text)['localNode']['isMaster']
    print(f"Is master: {isMaster}")

    if isMaster:
        restore()


if __name__ == "__main__":
    sig.signal(sig.SIGTERM, handle_sigterm)

    # output current process id
    print('My PID is:', os.getpid())

    postStart()

    # wait in an endless loop for signals 
    while True:
        print("Waiting")
        time.sleep(3)