gsutil cp "gs://${DEPLOYMENT_BUCKET}/${WEBAPP_RUNTIME_SA_KEY}" ./privatekey.json
gsutil cp "gs://${DEPLOYMENT_BUCKET}/${CONFIG_FILE}" ./app.yaml