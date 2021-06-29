import kopf
import pykube as pk
import logging
import os
import yaml

def get_template(template_name):
    path = os.path.join(os.path.dirname(__file__), f'templates/{template_name}')
    tmpl = open(path, 'rt').read()
    return tmpl

@kopf.on.field('batch', 'v1', 'jobs', "status", annotations={"enonic-operator-managed": kopf.PRESENT})
def installed_xp_app_handler(name, namespace, logger, new, **kwargs):
    logger.debug(f"New status: {new}")
    result = new.get('succeeded')
    if result is not None and result == 1:
        logger.debug(f"Deleting succeeded {namespace}/{name} job.")
        api = pk.HTTPClient(pk.KubeConfig.from_env())
        job = pk.Job.objects(api, namespace=namespace).get_by_name(name)
        job.delete(propagation_policy="Foreground")
    else:
        result = new.get('failed')
        if result is not None and result == 1:
            logger.error(f"{namespace}/{name} job is failing. Check the logs!")


@kopf.on.create('kopf.enonic', 'v1', 'enonicxpapps')
@kopf.on.update('kopf.enonic', 'v1', 'enonicxpapps')
def xp_app_handler(spec, name, namespace, logger, **kwargs):
    tmpl = get_template("app-installer-job.yaml")
    text = tmpl.format(
        name = name, 
        namespace = namespace,
        url = spec.get('bucket').get('url'),
        url_sufix = spec.get('bucket').get('url_sufix'),
        object_name = spec.get('object').get('name'),
        object_prefix = spec.get('object').get('prefix'),
        secret_name = spec.get('secret_name'),
        pvc_name = spec.get('pvc_name')
    )
    data = yaml.safe_load(text)
    kopf.adopt(data)
    logger.debug(f"Generated job: {data}.")
    api = pk.HTTPClient(pk.KubeConfig.from_env())
    try:
        job = pk.Job.objects(api, namespace=namespace).get_by_name(name)
        job.delete(propagation_policy="Foreground")
        while True:
            if not job.exists():
                break
    except pk.exceptions.ObjectDoesNotExist:
        pass
    pk.Job(api, data).create()



@kopf.on.create("apps", "v1", "statefulsets", annotations={"enonic-operator-managed": kopf.PRESENT, "enonic-operator-already-injected": kopf.ABSENT})
def init_fn(name, namespace, logger, **kwargs):
    api = pk.HTTPClient(pk.KubeConfig.from_env())
    while True:
        logger.debug("Trying to fetch statefulset object json")
        try:
            # Fetch statefulset object from Kubernetes api
            statefulset = pk.StatefulSet.objects(api, namespace=namespace).get_by_name(name)
            break
        except pk.exceptions.ObjectDoesNotExist:
            pass

    logger.debug("Adding \"enonic-operator-already-injected\" annotation")
    # Adds annotation to flag that it was injected
    statefulset.obj["metadata"]["annotations"]["enonic-operator-already-injected"] = ""

    logger.info("Preparing objects for injection")
    spec = statefulset.obj["spec"]["template"]["spec"]

    # Adds an emptyDir volume to store the exit flag for both containers
    exit_volume = {"name": "exit-folder", "emptyDir": {}}
    logger.debug(f"Preparing volume object: {exit_volume}")
    spec["volumes"].append(exit_volume)

    # Sidecar container specs
    debug = str(logger.getEffectiveLevel() == logging.DEBUG)
    tmpl = get_template("sidecar-container.yaml")
    text = tmpl.format(name=name, debug=debug)
    sidecar_container = yaml.safe_load(text)
    logger.debug(f"Preparing sidecar container object: {sidecar_container}")
    # Adds the sidecar container to statefulset object
    spec["containers"].append(sidecar_container)

    xp_container = spec["containers"][0]

    # Pre-stop definition to make Enonic XP container wait for the exit flag
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

    # If XP container doesn't already have a liveness probe using the ElasticSearch
    # cluster status/health check, it will be added
    if xp_container.get("livenessProbe") is None:
        xp_liveness = {
            "httpGet": {"path": "/cluster.elasticsearch", "port": 2609},
            "failureThreshold": 2,
            "initialDelaySeconds": 30,
            "periodSeconds": 10,
        }
        logger.debug(f"Preparing liveness probe for xp container: {xp_liveness}")
        xp_container["livenessProbe"] = xp_liveness

    # Mount the exit volume on XP container
    xp_exit_volume = {"name": "exit-folder", "mountPath": "/exit"}
    logger.debug(f"Preparing volume mounting for xp container: {xp_exit_volume}")
    xp_container["volumeMounts"].append(xp_exit_volume)

    logger.info("Injecting sidecar container")
    statefulset.update()
    logger.info("Injection has been successful")
    api.session.close()
