# Enonic Operator for k8s

## Overview

Enonic operator (unofficial) is a Kubernetes operator that allows Enonic XP apps to run properly on a scalable environment, without losing data shards or getting the cluster crashed when scale-up and scale-down events happen.

## How does it work

This operator injects a sidecar container that performs snapshots on tier down and restores those on tier up.

## Getting started

### Installing the operator

-   First install kopf operator peering (to prevent duplicated operators from doing the same thing at the same time)

    You maybe will need to run this command twice to make sure that all resources are created.

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/init/peering.yaml
    ```


-   Install the operator by the following command
    
    ```bash
    kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/manifests/manifest.yaml
    ```


### Making run with Enonic XP applications

-   Your Enonic XP app must be deployed as a StatefulSet (because Enonic uses Elastic Search to manage all the data, and ES clusters are Stateful). 
  
-   It's highly recommended reading this guide that shows how to deploy an Enonic XP app properly on Kubernetes. (Link coming soon)
   
-   Create a generic secret named with this pattern

    `<StatefulSetName>-auth`

    This secret will contain a "auth" key with user:password credentials (using exactly this pattern) to a user that owns permissions to restore and create snapshots. The default will be su:password.

    ```
    kubectl create secret generic -n <your-app-namespace> \
    <statefulset-name>-auth --from-literal=auth=<user>:<password>
    ```

    **YOU DO NOT NEED TO ATTACH THIS SECRET TO YOUR APP, JUST CREATE.**

    *Example:*

    My StatefulSet is named by "my-xp", the crendentials are user "giropops" and password "bolinha", so this is how I gonna create my secret:

    ```
    kubectl create secret generic -n <your-app-namespace> \
    my-xp-auth --from-literal=auth=giropops:bolinha
    ```

-   The StatefulSet need to have an annotation called "enonic-operator-managed" (with anything as a value, the annotation just be there), to flag that it can be managed by the operator. 
  
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

-   Last but not less (or something like that), the Enonic XP application container **MUST BE** the first container in StatefulSet manifest.

-   Now you can apply/update the StatefulSet and see the magic happening.