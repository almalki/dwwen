from django.conf import settings

__author__ = 'abdulaziz'

class SetRemoteAddrFromRealIp(object):

    def process_request(self, request):
        '''
        We assume the reverse proxy will set HTTP_X_REAL_IP to a correct value, in case it was
        the only proxy, it will be the value of remote_addr. Note that this will have impact on
        users NATed behind the same proxy, since they will be considered one and throttled
        accordingly.
        '''
        try:
            real_ip = request.META['HTTP_X_REAL_IP']
        except KeyError:
            return None
        else:
            request.META['REMOTE_ADDR'] = real_ip