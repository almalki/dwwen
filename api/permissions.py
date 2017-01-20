from api.models import Blog

__author__ = 'abdulaziz'


from rest_framework import permissions


class IsResourceOwnerOrReadOnly(permissions.BasePermission):
    """
    Global permission check for blacklisted IPs.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `owner`.
        return obj.user == request.user


class IsAuthenticatedNonPost(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method == 'POST':
            if request.user.is_authenticated():
                return False
            else:
                return True

        elif request.method == 'GET':
            return True

        elif request.user.is_authenticated():
            return True
        else:
            return False


class IsAuthenticatedAndSameUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj == request.user and request.user.is_authenticated()
    

class IsDwwenBlogOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in ['PUT', 'DELETE', 'POST']:
            if view.action in ['update', 'publish', 'destroy']:
                return obj.blog.user == request.user and obj.blog.type == Blog.DWWEN
            #better to be explicit for allowing
            elif view.action in ['retrieve', 'like', 'favorite']:
                return True
        elif request.method == 'GET' and view.action in ['retrieve', 'mlt', 'visit']:
            return True
        return False