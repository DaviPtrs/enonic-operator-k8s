import kopf
import os


@kopf.on.event('', 'v1', 'pods', annotations={'enonic-operator-managed': kopf.PRESENT})
def create_fn(event, status, **kwargs):
    if event is None or status is None:
        return
    if event is '' or status is '':
        return
    if event.get('type') == None or status.get('phase') != "Running":
        return
    if event['object']['metadata'].get('deletionGracePeriodSeconds') != None:
        return
    
    podIp = status['podIP']
