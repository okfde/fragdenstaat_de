from rest_framework import serializers, viewsets
from rest_framework.decorators import action

from .models import ArticleTag


class ArticleTagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArticleTag
        fields = (
            "id",
            "name",
            "slug",
        )


class ArticleTagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleTagSerializer
    queryset = ArticleTag.objects.all()

    @action(
        detail=False, methods=["get"], url_path="autocomplete", url_name="autocomplete"
    )
    def autocomplete(self, request):
        query = request.GET.get("q", "")
        tags = ArticleTag.objects.none()
        if query:
            tags = ArticleTag.objects.filter(name__istartswith=query).values_list(
                "name", flat=True
            )

        page = self.paginate_queryset(tags)
        return self.get_paginated_response([{"value": t, "label": t} for t in page])
