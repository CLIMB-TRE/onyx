class CurrentUserSiteDefault:
    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context["request"].user.site

    def __repr__(self):
        return "%s()" % self.__class__.__name__


class CurrentProjectDefault:
    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context["project"]

    def __repr__(self):
        return "%s()" % self.__class__.__name__
