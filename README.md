# Enonic XP Operator for k8s

Enonic operator (unofficial) is a Kubernetes operator that allows Enonic XP apps to run properly on a scalable environment, without losing data shards or getting the cluster crashed when scale-up and scale-down events happen.

- [Enonic XP Operator for k8s](#enonic-xp-operator-for-k8s)
- [How does it work](#how-does-it-work)
- [Getting started](#getting-started)
  - [How to install](#how-to-install)
    - [Helm chart (recommended)](#helm-chart-recommended)
    - [kubectl](#kubectl)
  - [Making it run with Enonic XP applications](#making-it-run-with-enonic-xp-applications)
    - [Initial Considerations](#initial-considerations)
    - [Steps](#steps)
  - [Installing Jar files from an S3 bucket](#installing-jar-files-from-an-s3-bucket)
    - [Bucket credentials](#bucket-credentials)
    - [Building the manifest](#building-the-manifest)
- [Debugging](#debugging)
- [Contribute](#contribute)
- [Submit Feedback](#submit-feedback)

# How does it work

This operator injects a sidecar container that performs snapshots on tier down and restores those on tier up.

# Getting started

## How to install

First of all, install the KOPF operator peering resources (to prevent duplicated operators from doing the same thing at the same time)

You maybe will need to run this command twice to make sure that all resources are existent.

```bash
kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/init/peering.yaml
```

### Helm chart (recommended)

If you want to customize your operator deploy specs, see the example [values.yaml](chart/values.yaml)

- Add my chart repo
  ```bash
  helm repo add daviptrs-charts https://daviptrs.github.io/helm-charts/
  ```
- Install a new release
  ```bash
  helm install enonic-operator --wait daviptrs-charts/enonic-operator
  ```


### kubectl

- Install the operator by the following command
    
  ```bash
  kubectl apply -f https://raw.githubusercontent.com/DaviPtrs/enonic-operator-k8s/main/manifests/manifest.yaml
  ```


## Making it run with Enonic XP applications

### Initial Considerations

-   Your Enonic XP app must be deployed as a StatefulSet (because Enonic uses Elastic Search to manage all the data, and ES clusters are Stateful). 
  
-   It's highly recommended reading [this guide](https://github.com/DaviPtrs/enonic-xp-kubernetes) that shows how to deploy an Enonic XP app properly on Kubernetes.

-   **Don't apply the StatefulSet with more than 1 replica**, because it may cause an unwanted multi ES cluster being formed. If you want to initialize your application with multi replicas, you need to deploy with just 1 replica and then after the injection, you can scale up your application using `kubectl scale`

-   The injection will add a sidecar container, so if your original pod contains 1 container, the injected pod will have 2 containers. Wait for the injection happens before doing anything in your app.

### Steps
   
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

## Installing Jar files from an S3 bucket

This operator comes with a Custom Resource that allows you to install any application, by downloading its .jar from any bucket that supports the S3 protocol, which includes AWS S3 (of course) and also supports Minio buckets (actually we use the Minio CLI docker image to perform this task).

To use this feature, you must have a shared PVC attached to the Enonic deploy folder (usually /enonic-xp/home/deploy), the CRD works downloading your desired Jar file and placing it inside the deploy PVC.

### Bucket credentials

Create a namespaced secret (where you want to deploy your app) with the S3 bucket credentials like the following example:

**Remember to use simple quotes to prevent issues with bash reserved chars**

```bash
kubectl create secret generic -n my-namespace bucket-secret --from-literal=access_key='bolinha' --from-literal=secret_key='giropops'
```

### Building the manifest

You need to create a manifest that is namespaced with the same namespace as your application, like the following one:

```yaml
apiVersion: kopf.enonic/v1
kind: EnonicXpApp
metadata:
  name: my-app
  namespace: my-namespace
spec:
  secret_name: bucket-secret # name of the secret containing the bucket credentials
  pvc_name: deploy-pvc # pvc that will receive the installed Jar
  bucket:
    url: s3.example.com # Bucket endpoint (without https://)
    url_sufix: sample-project/master # Bucket folder where the jar is located. Can be empty (empty string == "").
  object:
    prefix: "sample-project-" # Artifact name without extensions and versions
    name: sample-project-1.1.0.jar # The actual full artifact name
```

# Debugging

When you try to edit the StatefulSet (after the injection), you will see something like this:

```yaml
  - name: enonic-sidecar
    image: daviptrs/enonic-operator-k8s-sidecar:latest
    imagePullPolicy: Always
    env: 
      - name: "DEBUG"
        value: "False"
```

To enable debugging mode on sidecar container, change the DEBUG value from `"False"` to `"True"` (including quotes)

# Contribute

Contributions are always welcome!
If you need some light, read some of the following guides: 
- [The beginner's guide to contributing to a GitHub project](https://akrabat.com/the-beginners-guide-to-contributing-to-a-github-project/)
- [First Contributions](https://github.com/firstcontributions/first-contributions)
- [How to contribute to open source](https://github.com/freeCodeCamp/how-to-contribute-to-open-source)
- [How to contribute to a project on Github](https://gist.github.com/MarcDiethelm/7303312)

# Submit Feedback

Be free to [open an issue](https://github.com/DaviPtrs/enonic-operator-k8s/issues/new/choose) telling your experience, suggesting new features or asking questions (there's no stupid questions, but make sure that yours cannot be answered by just reading the docs)

You can also find me on LinkedIn [/in/davipetris](https://www.linkedin.com/in/davipetris/)