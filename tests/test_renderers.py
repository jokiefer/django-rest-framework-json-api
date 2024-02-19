
import time
import pytest

from rest_framework import status
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter

from rest_framework_json_api.parsers import JSONParser
from rest_framework_json_api.relations import ResourceRelatedField
from rest_framework_json_api.renderers import JSONRenderer
from rest_framework_json_api.views import ModelViewSet
from tests.models import ForeignKeySource, ForeignKeyTarget
from rest_framework_json_api import serializers

from django.urls import reverse
from django.core.signals import request_finished, request_started
import json

@pytest.fixture
def service(db):
    # configure self.attribute
    service = ForeignKeyTarget.objects.create(name="service")
    layers = [ForeignKeySource(name="l", target=service) for x in range(10000)]
    ForeignKeySource.objects.bulk_create(objs=layers)
    return service


class TestIncludePerformance:

    @pytest.mark.urls(__name__)
    def test_benchmark(self, client, service):

        url = reverse("benchmark-detail", kwargs={"pk": service.pk})
        response = client.get(f"{url}?include=sources")
        result = json.loads(response.content)
        print(len(result["included"]))
        assert response.status_code == status.HTTP_200_OK
        assert len(result["included"]) == 10000


class ForeignKeyTargetSerializer(serializers.ModelSerializer):
    a = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    b = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    c = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    d = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    e = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    f = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    g = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    h = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    i = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    j = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    k = serializers.CharField(default=serializers.CreateOnlyDefault("default"))
    l = serializers.CharField(default=serializers.CreateOnlyDefault("default"))

    sources = ResourceRelatedField(
        model=ForeignKeySource, 
        many=True,
        read_only=True,
    )

    class Meta:
        model = ForeignKeyTarget
        fields = "__all__"


class IncludeableForeignKeyTargetSerializer(ForeignKeyTargetSerializer):
    included_serializers = {
        "sources": ForeignKeyTargetSerializer
    }


class BenchmarkAPIView(ModelViewSet):
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]
    resource_name = "service"

    serializer_class = IncludeableForeignKeyTargetSerializer
    queryset = ForeignKeyTarget.objects.all()

    def retrieve(self, request, *args, **kwargs):
        global db_time
        global serializer_time
        global started
        started = time.time()

        db_start = time.time()
        instance = self.get_object()
        db_time = time.time() - db_start

        serializer_start = time.time()
        serializer = self.get_serializer(instance)
        data = serializer.data
        serializer_time = time.time() - serializer_start

        return Response(status=status.HTTP_200_OK, data=data)

    def dispatch(self, request, *args, **kwargs):
        global dispatch_time
        global render_time

        dispatch_start = time.time()
        ret = super().dispatch(request, *args, **kwargs)

        render_start = time.time()
        ret.render()
        render_time = time.time() - render_start

        dispatch_time = time.time() - dispatch_start

        return ret


def started(sender, **kwargs):
    global started
    started = time.time()


def finished(sender, **kwargs):
    total = time.time() - started
    api_view_time = dispatch_time - (render_time + serializer_time + db_time)
    request_response_time = dispatch_time - total
    print()
    print("Database lookup               | %.4fs" % db_time)
    print("Serialization                 | %.4fs" % serializer_time)
    print("Django request/response       | %.4fs" % request_response_time)
    print("API view                      | %.4fs" % api_view_time)
    print("Response rendering            | %.4fs" % render_time)


request_started.connect(started)
request_finished.connect(finished)


router = SimpleRouter()
router.register(r"benchmark", BenchmarkAPIView, basename="benchmark")
urlpatterns = router.urls
