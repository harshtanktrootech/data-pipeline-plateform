from django.contrib import admin
from django.urls import include, path
# from pipelines.views import pipeline_list_page, pipeline_detail_page

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.urls')),
    path('api/pipelines/', include('pipelines.urls')),

    # path("pipelines/", pipeline_list_page, name="pipeline-list-page"),
    # path("pipelines/<int:pk>/", pipeline_detail_page, name="pipeline-detail-page"),

    # path('api/executions/', include('executions.urls')),
    # path('api/audit/', include('audit.urls')),
    # path('api/dashboard/', include('dashboard.urls')),
]
