import kopf
import os


@kopf.on.event('', 'v1', 'pods', annotations={'enonic-operator-managed': kopf.PRESENT})
def create_fn(event, status, **kwargs):
    ignored_conditions = [
        event is None, 
        status is None,
        event is '',
        status is '',
        event.get('type') == None,
        status.get('phase') != "Running",
        event['object']['metadata'].get('deletionGracePeriodSeconds') != None 
    ]
    if any(ignored_conditions):
        return
    
    podIp = status['podIP']
