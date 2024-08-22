from data.urls import generate_project_urls
from .serializers import TestModelSerializer


urlpatterns = [
    # Any view overrides go here
    generate_project_urls("testproject", TestModelSerializer),
]
