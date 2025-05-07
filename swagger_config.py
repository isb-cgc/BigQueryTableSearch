swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "[ISB-CGC] BigQuery Table Search",
        "description": "API Documentation for [ISB-CGC] BigQuery Table Search",
        # "version": "1.0",
    },
    "schemes": [
        "https"
    ],
}

swagger_config = {
    "headers": [
        ('Access-Control-Allow-Origin', 'self'),
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
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}
