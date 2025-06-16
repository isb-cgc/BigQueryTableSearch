swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "[ISB-CGC] BigQuery Table Search",
        "description": "API Documentation for [ISB-CGC] BigQuery Table Search",
    },
    "schemes": [
        "https"
        # ,
        # "http"
    ],
}

swagger_config = {
    "title": "BigQuery Table Search API - Swagger UI",
    "headers": [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', "GET, POST"),
    ],
    "specs": [
        {
            "endpoint": 'search_api',
            "route": '/bq_search.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "jquery_js": '/static/js/libs/jquery.min.js',
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}
