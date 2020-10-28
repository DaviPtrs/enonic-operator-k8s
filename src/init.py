import time

import kopf
import pykube as pk


@kopf.on.create("apps", "v1", "statefulsets", annotations={"enonic-operator-managed": kopf.PRESENT})
def init_fn(name, namespace, logger, **kwargs):
    api = pk.HTTPClient(pk.KubeConfig.from_env())
    while True:
        logger.debug("Trying to fetch statefulset object json")
        try:
            statefulset = pk.StatefulSet.objects(api, namespace=namespace).get_by_name(name)
            break
        except pk.exceptions.ObjectDoesNotExist:
            pass

    logger.info("Preparing objects for injection")
    spec = statefulset.obj["spec"]["template"]["spec"]

    exit_volume = {"name": "exit-folder", "emptyDir": {}}
    logger.debug(f"Preparing volume object: {exit_volume}")
    spec["volumes"].append(exit_volume)

    sidecar_container = {
        "name": "enonic-sidecar",
        "image": "daviptrs/enonic-operator-k8s-sidecar:alpha",
        "imagePullPolicy": "Always",
        "env": [
            {"name": "DEBUG", "value": "False"},
            {
                "name": "ENONIC_AUTH",
                "valueFrom": {"secretKeyRef": {"name": f"{name}-auth", "key": "auth"}},
            },
        ],
        "volumeMounts": [{"name": "exit-folder", "mountPath": "/exit"}],
    }
    logger.debug(f"Preparing sidecar container object: {sidecar_container}")
    spec["containers"].append(sidecar_container)

    xp_container = spec["containers"][0]

    xp_pre_stop = {
        "exec": {
            "command": [
                "/bin/bash",
                "-c",
                'while [ -z "$(ls /exit)" ];do sleep 1; done',
            ]
        }
    }
    logger.debug(f"Preparing preStop probe for xp container: {xp_pre_stop}")

    if xp_container.get("lifecycle") is None:
        xp_container["lifecycle"] = {}
    xp_container["lifecycle"]["preStop"] = xp_pre_stop

    if xp_container.get("livenessProbe") is None:
        xp_liveness = {
            "httpGet": {"path": "/cluster.elasticsearch", "port": 2609},
            "failureThreshold": 2,
            "initialDelaySeconds": 30,
            "periodSeconds": 10,
        }
        logger.debug(f"Preparing liveness probe for xp container: {xp_liveness}")
        xp_container["livenessProbe"] = xp_liveness

    xp_exit_volume = {"name": "exit-folder", "mountPath": "/exit"}
    logger.debug(f"Preparing volume mounting for xp container: {xp_exit_volume}")
    xp_container["volumeMounts"].append(xp_exit_volume)

    logger.info("Injecting sidecar container")
    statefulset.update()
    logger.info("Injection has been successful")
    api.session.close()
