# BigQueryTableSearch
Standalone BigQuery Table Search System


# Local Development

1) **Create a Service Account:** 
Create a Service Account using [these instructions](https://cloud.google.com/iam/docs/creating-managing-service-accounts). 
The account will need the following roles against the GCP project or BQ datasets holding the data you wish to make searchable:
   - BigQuery Job User
   - Viewer


**NOTE:** For these next steps you will want to `gcloud auth login` and `gcloud config set project <PROJECT ID>` via the Google Cloud SDK to the GCP project used for development.


2) Give your personal account the IAM role `roles/iam.serviceAccountTokenCreator` role on the Service Account you made: 
`gcloud iam service-accounts add-iam-policy-binding <SERVICE ACCOUNT EMAIL> --member=user:<YOUR ACCOUNT EMAIL> --role=roles/iam.serviceAccountTokenCreator `.


3) On the GCloud SDK CLI, run the command `gcloud auth application-default login --impersonate-service-account <SERVICE ACCOUNT EMAIL>` to create the default credentials account under your identity.


4) Save a copy of `sample.env` into your secure files directory, renaming it to `dev.env`.  Add the missing values from the development
tier's `.env`, and set the `SECURE_PATH` value to the absolute path on your file system to your secure files directory 
(eg. `C:\Users\<USERNAME>\secure\dev\`).


5) In Pycharm, create a Flask configuration by clicking on `Edit Configurations...` and choosing + from the upper left 
corner of dialog that opens. Choose your local Python interpreter, set the script to main.py, and set the `Paths to ".env" files` 
to the full path to your `dev.env`.


6) Click the 'Play' button in Pycharm, or use `<PYTHON CMD> -m flask run` from the project directory.
