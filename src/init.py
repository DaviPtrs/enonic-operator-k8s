import kopf
import time
import pykube as pk


@kopf.on.create('apps', 'v1', 'statefulsets', annotations={'enonic-operator-managed': kopf.PRESENT})
def init_fn(**kwargs):
    for key in kwargs:
        print(key)
        print(kwargs[key])



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