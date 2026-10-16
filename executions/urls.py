from django.urls import path
from executions.views import execution_history_page

urlpatterns = [
    path("", execution_history_page, name="execution-history-page"),
]
