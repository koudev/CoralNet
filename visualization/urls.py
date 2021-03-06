from django.conf.urls.defaults import *  # 404, 500, patterns, include, url

urlpatterns = patterns('',
    url(r'^(?P<source_id>\d+)/$', 'visualization.views.visualize_source', name="visualize_source"),
    url(r'^(?P<source_id>\d+)/statistics', 'visualization.views.generate_statistics', name="statistics"),
    url(r'^(?P<source_id>\d+)/csv_annotations/$', 'visualization.views.export_annotations', name="export_annotations"),
    url(r'^(?P<source_id>\d+)/csv_statistics/$', 'visualization.views.export_statistics', name="export_statistics"),
    url(r'^(?P<source_id>\d+)/export/$', 'visualization.views.export_menu', name="export_menu"),
)
