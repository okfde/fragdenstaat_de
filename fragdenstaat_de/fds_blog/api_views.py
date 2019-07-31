from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import ArticleTag


class ArticleTagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ArticleTag
        fields = (
            'id', 'name', 'slug',
        )


class ArticleTagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleTagSerializer
    queryset = ArticleTag.objects.all()

    @action(detail=False, methods=['get'], url_path='autocomplete',
            url_name='autocomplete')
    def autocomplete(self, request):
        query = request.GET.get('query', '')
        tags = []
        if query:
            tags = ArticleTag.objects.filter(name__istartswith=query)
            tags = [t for t in tags.values_list('name', flat=True)]
        return Response(tags)
