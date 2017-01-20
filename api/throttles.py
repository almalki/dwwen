from rest_framework.throttling import UserRateThrottle

__author__ = 'abdulaziz'

class EmailSendThrottle(UserRateThrottle):
    rate = '100/day'


class BlogClaimVerifyThrottle(UserRateThrottle):
    rate = '24/day'


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'
