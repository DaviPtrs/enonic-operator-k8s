import asyncio
import kopf
import time
import pykube as pk

tasks = {}

@kopf.on.create('apps', 'v1', 'statefulsets', annotations={'enonic-operator-managed': kopf.PRESENT})
def init_fn(name, namespace, **kwargs):
    api = pk.HTTPClient(pk.KubeConfig.from_env())
    while True:
        try:
            statefulset = pk.StatefulSet.objects(api, namespace=namespace).get_by_name(name)
            break
        except pk.exceptions.ObjectDoesNotExist:
            pass
    
    exit_volume = {'name': 'exit-folder', 'emptyDir': {}}
    (statefulset.obj["spec"]["template"]["spec"]["volumes"]).append(exit_volume)

    sidecar_container = {'name': 'enonic-sidecar', 'image': 'daviptrs/enonic-operator-k8s-sidecar:alpha','env': [{'name': 'ENONIC_AUTH', 'valueFrom': {'secretKeyRef': {'name': f'{name}-auth', 'key': 'auth'}}}], 'volumeMounts': [{'name': 'exit-folder','mountPath': '/exit'}]}
    (statefulset.obj['spec']['template']['spec']['containers']).append(sidecar_container)

    xp_pre_stop = {'exec': {'command': ['/bin/bash', '-c', 'while [ -z "$(ls /exit)" ];do sleep 1; done']}}
    if statefulset.obj['spec']['template']['spec']['containers'][0].get('lifecycle') is None:
        statefulset.obj['spec']['template']['spec']['containers'][0]['lifecycle'] = {}
    statefulset.obj['spec']['template']['spec']['containers'][0]['lifecycle']['preStop'] = xp_pre_stop

    xp_exit_volume = {'name': 'exit-folder', 'mountPath': '/exit'}
    (statefulset.obj['spec']['template']['spec']['containers'][0]['volumeMounts']).append(xp_exit_volume)


    statefulset.update()
    api.session.close()


# @kopf.on.event('', 'v1', 'pods', annotations={'enonic-operator-managed': kopf.PRESENT})
# def init_fn(event, status, **kwargs):
#     ignored_conditions = [
#         event is None, 
#         status is None,
#         event is '',
#         status is '',
#         event.get('type') == None,
#         status.get('phase') != "Running",
#         event['object']['metadata'].get('deletionGracePeriodSeconds') != None 
#     ]
#     if any(ignored_conditions):
#         return
    
#     api = pk.HTTPClient(pk.KubeConfig.from_env())

#     api.session.close()
    


# @kopf.on.delete('', 'v1', 'pods', annotations={'enonic-operator-managed': kopf.PRESENT})
# def delete_fn(status, **kwargs):
#     print("\n\n\n\n\n================\n\n\n\n")

#     time.sleep(60)
#     print(status['podIP'])