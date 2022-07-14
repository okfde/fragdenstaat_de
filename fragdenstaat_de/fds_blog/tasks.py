from datetime import timedelta

from django.utils import timezone

from froide.celery import app as celery_app


@celery_app.task(name="fragdenstaat_de.fds_blog.index_recently_published")
def index_recently_published():
    from .documents import index_article
    from .models import Article

    roughly_hour_ago = timezone.now() - timedelta(minutes=90)

    recently_published = Article.published.filter(
        start_publication__gte=roughly_hour_ago
    )
    for article in recently_published:
        index_article(article)
