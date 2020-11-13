# Enonic Operator for k8s

## Overview

Enonic-operator is an kubernetes operator (unofficial) that allows Enonic XP apps to run properly on a scalable environment, without losing data shards or getting the cluster crashed when scale-up and scale-down events happen.

## How does it work

This operator injects a sidecar container that perform snapshots on tier down and restore those on tier up.

## Getting started

### Installing the operator

-   First install kopf operator peering (to prevent duplicated operators doing the same thing at the same time)

    You maybe will need to run this command twice to make sure that all resources are created.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/init/peering.yaml
    ```


-   Install the operator by the following command
    
    ```bash
    kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/manifests/manifest.yaml
    ```
    ``


### Making run with Enonic XP applications

-   Your Enonic XP app must be deployed as a StatefulSet (because Enonic uses Elastic search to manage all the data, and ES clusters are Stateful).
   
-   Create a generic secret named with this pattern

    `<StatefulSetName>-auth`

    This secret will contain a "auth" key with user:password credentials (using exactly this pattern) to a user that own permissions to restore and create snapshots. Default will be su:password.

    **YOU DO NOT NEED TO ATTACH THIS SECRET TO YOUR APP, JUST CREATE.**

    *Example:*

    My StatefulSet is named by "my-xp", the user credentials are giropops:bolinha, so this is how I gonna create my secret:

    ```
    kubectl create secret generic -n <your-app-namespace> \
    my-xp-auth --from-literal=auth=giropops:bolinha
    ```

-   The StatefulSet must have an annotation called "enonic-operator-managed" (with anything as a value, the annotation just be there), to flag that it can be managed by the operator. 
  
    Example:

    ```yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
        name: my-xp
        namespace: my-xp
        annotations:
            enonic-operator-managed: ""
    spec:
        ...
    ```

    Another valid example

    ```yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
        name: my-xp
        namespace: my-xp
        annotations:
            enonic-operator-managed: "annotaception"
    spec:
        ...
    ```

-   Last but not less (or something like that), the Enonic xp application container **MUST BE** the first container of your containers definition.

-   Now you can apply/update your StatefulSet and see the magic happening.