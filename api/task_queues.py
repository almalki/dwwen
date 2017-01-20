from django_rq.decorators import job
from api.models import UserPostView

__author__ = 'abdulaziz'


@job
def record_post_view(post_id, user_id, type):
    UserPostView.objects.create(post_id=post_id, user_id=user_id, type=type)