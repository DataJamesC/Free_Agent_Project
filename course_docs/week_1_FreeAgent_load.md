# Extract & Load Project: freeagent

### Week 2 | Tuesday | Instructor Led Walkthrough

## Introduction

## Learning Objectives

- Considerations for Loading Data
- Configuring AWS
- Loading with Python
- Snowflake Storage Integrations

## Recap of Existing Processes

**Airbyte Cloud** Extract and load to AWS S3 bucket\
**freeagent Export API** Python script to extract and store locally in a zip folder

## Considerations for Loading Data

### Data Loading Strategies

**Full Refresh vs. Incremental Loading**
Choose between full refresh and incremental loading based on data size, computational intensity, and loading frequency. Incremental loading is ideal for large datasets with frequent updates, as it only transfers new or modified data since the last load.

**Batch vs. Real-Time Loading**
Batch loading is suitable for organisations with low data volatility, while real-time or stream loading is ideal for high-velocity data streams requiring immediate insights.

**The Staging Layer**
The staging layer in practice is an Amazon S3 Bucket, Azure Blob Storage or another flexible data container. It serves as an intermediate storage area between source systems and the final destination. Its primary purpose is to temporarily hold and process data before it's loaded into the target system, typically a data warehouse or database.

It has the following opportunities:

- Data Consolidation: the staging layer allows the collection of data from multiple source systems regardless of data types and formats
- Data Quality Enhancement: data cleaning, standardisation, and quality enrichment can be applied at the staging layer
- Schema Alignment: the staging layer allows for necessary transformations to align data schemas from different sources

Which leads to the advantages of:

- Improved efficiency, auditability and monitoring
- Increased flexibility in handling diverse data sources
- Reduced strain on source and target systems

### Data Security

Throughout this process, we'll be applying some key data security concepts to prevent our data from falling into the wrong hands, i.e. a data breach.

| Security Principle     | Explanation                                                                                                                   | Example Risk Prevented                                        |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Least Privilege Access | "Least privilege" means giving people or services only the access they absolutely need to perform their job—no more, no less. | Attacker stealing one account can’t control all systems.      |
| Encryption at Rest     | Data is stored in an encrypted form, making it unreadable without the proper key.                                             | Theft of a server or database still won’t leak readable data. |
| Encryption in Transit  | Data is encrypted while being sent across a network.                                                                          | Prevents network-based spying or man-in-the-middle attacks.   |

### Optimization Techniques

- **Parallel Loading** For large datasets to distribute workload across multiple processors, threads, or servers, significantly accelerating data transfer.
- **Data Compression and Encryption** Implement compression to reduce data transfer volumes and encrypt sensitive data during loading to ensure security.
- **Caching and Partitioning** Techniques to optimize data access and improve loading performance

### Challenges with Loading Data

- **Schema Evolution** Managing schema evolution as data structures change over time
- **Unstructured Data** Handling data types like images, audio, or social media content
- **Data Quality** Ensuring data integrity throughout the loading process
- **Monitoring** Implementing effective error handling and logging mechanisms
- **Data Security and Privacy** Implementing proper access controls and data masking and encryption techniques to ensure compliance with data protection regulations
- **Performance and Scalability** Ability to handle large, infrequent data loads, that can scale to meet growing data demands promptly

## Setting Up AWS S3 for Secure Snowflake Integration

![](../course_docs/images/aws_load_diagram.png)

#### What is a Snowflake Storage Integration?

A Snowflake storage integration allows secure and seamless access to an Amazon S3 bucket by associating Snowflake with an IAM user configured for your account.

<a href="https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration">
    <img src="https://docs.snowflake.com/en/_images/storage-integration-s3.png" width ="90%">
  </a>

1. An external (i.e. S3) stage references a storage integration object in its definition.

2. Snowflake automatically associates the storage integration with an S3 IAM user created for your account. Snowflake creates a single IAM user that is referenced by all S3 storage integrations in your Snowflake account.

3. An AWS administrator in your organisation grants permissions to the IAM user to access the bucket referenced in the stage definition. Note that many external stage objects can reference different buckets and paths and use the same storage integration for authentication.

Source: https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration

## Step 0. Personalising This Document

This walkthrough contains a number of AWS CLI scripts that require your name and account number. To reduce the manual effort you can run a script to customise all the commands in the walkthrough and it's supporting docs.

- In the AWS folder, create an file `.aws_env` with your name and aws account number, e.g.

YOUR_NAME='wjsutton'\
AWS_ACCOUNT_ID=123456789012\
PROFILE_NAME='default'\
COHORT='DESxx'\
PROJECT='des_freeagent'

- Then run the python script [aws/personalise.py](../aws/personalise.py)

```
python aws/personalise.py
```

- Confirm in the folder 'aws' a new folder 'week_2' has been added
- Confirm in the folder 'course*docs' a 'confidential*' version of this walkthrough has been added



Assuming you have configured a profile correctly in your `./aws/configure` file, using that profile to login with the below command should work.

```
aws sso login --profile <profile-name>
```

#### Using the AWS CLI

For Bike Point, we used the GUI to set everything up for AWS. Today you'll be trying things out with the CLI. However, if you get stuck with the CLI, you can find instructions for doing it using the GUI below.

<details>
<summary>AWS GUI Instructions</summary>

### In the AWS Console

Important reminder: Make sure to include the tag `Usage:Training` on everything you create in AWS to help with deleting everything at the end of training.

**Login to AWS Console**

- Sign in the AWS using your TIL email.

#### Step 1: Create S3 Bucket for Data Import

- Navigate to S3 > Create bucket.
- Provide a Bucket name, `<your-name>-freeagent-storage`
- Under Object Ownership select, `ACLs disabled (recommended)`
- Under Bucket settings for Block Public Access select, `Block all public access`
- Under Bucket Versioning select, `Disable`
- Under Default Encryption select, `Server-side encryption with AWS Key Management Service keys (SSE-KMS)`
- Choose `Create a new KMS key`, leave KMS default settings, Step give the key an alias, `<your-name>-freeagent-kms-key`, Select `Skip to Review` and `Finish`.
- Return to Amazon S3 tab and Enter Aws KMS key ARN or Choose the key from your AWS KMS keys
- Bucket Key, `Enable`
- Click `Create bucket`

| Security Measure          | Key Benefit                                                                                                                                   | Example Threat Mitigated                                                           |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| ACLs Disabled             | All access control is managed centrally through IAM policies or bucket policies, simplifying security management.                             | Prevents accidental misconfiguration or exposure                                   |
| Block Public Access       | No one outside your AWS account can access the bucket                                                                                         | Prevents unauthorized data access, accidental exposure or leaks of sensitive data. |
| Bucket Versioning Enabled | Maintains multiple versions of each file in the bucket, allowing recovery of older versions if files are accidentally overwritten or deleted. | Prevents accidental or intentional data loss                                       |
| SSE-KMS Encryption        | Ensures data stored is unreadable without encryption key                                                                                      | Prevents usage of data if data was accessed                                        |
| Bucket Key Enabled        | Temporarily caches encryption keys within S3 to encrypt/decrypt many objects without repeated requests to AWS KMS                             | Lowers AWS KMS costs without compromising security.                                |

#### Setup S3 Bucket for Data Import

- In your new S3 Bucket, Create a folder in the bucket, named `python-import`, and `Specify an encryption key` with Use bucket settings for default encryption

<!-- #### Create S3 Bucket for Logging

- Create another bucket specifically for access logs, `freeagent-storage-logs` with default settings
- In the primary bucket, `freeagent-storage`, select Properties > Server access logging  and `Edit`
- Enable logging and choose the logging bucket `freeagent-storage-logs` as the destination. -->

### Create an IAM Policy

- Log in to the AWS Management Console.
- From the home dashboard, search for and select IAM.
- From the left-hand navigation pane, select Account settings.
- Under Security Token Service (STS) in the Endpoints list, find the Snowflake region where your account is located, in this case 'eu-west-1'. If the STS status is inactive, move the toggle to Active.
- From the left-hand navigation pane, select Policies.
- Select Create Policy.
- For the Policy editor, select JSON and enter the following

Replace:

- &lt;bucket&gt; with the bucket name, i.e. <your-name>-freeagent-storage
- &lt;prefix&gt; to the folder within the bucket, i.e. python-import
- &lt;kms-key&gt; the kms key for accessing your bucket

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
			"Effect": "Allow",
			"Action": [
				"s3:PutObject",
				"s3:GetObject",
				"kms:Decrypt",
				"kms:DescribeKey",
				"kms:GenerateDataKey",
				"kms:Encrypt",
				"s3:DeleteObject",
				"s3:PutObjectAcl",
				"s3:ListBucket",
				"s3:ListBucketMultipartUploads",
				"s3:AbortMultipartUpload",
				"s3:GetBucketLocation"
			],
            "Resource": [
                "arn:aws:s3:::<bucket>/<prefix>",
                "arn:aws:s3:::<bucket>/<prefix>/*",
                "arn:aws:kms:<kms-key>"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::<bucket>",
            "Condition": {
                "StringLike": {
                    "s3:prefix": [
                        "<prefix>/*",
                        "<prefix>"
                    ]
                }
            }
        }
    ]
}
```

Note that the privileges here only allow data to be read from the S3 bucket. You can give permission for Snowflake to write and delete objects from the bucket.

- Select Next.
- Enter a Policy name, e.g. <your-name>-sts-s3-integration-python
- Select Create policy.


**Check** Search for "sts-s3-integration" and verify you have a policy

### Create an IAM User

- Navigate to IAM
- Select Create new user
- Provider a user name, `<your-name>_freeagent_python_uploader`, and click Next
- Attach policies directly > Search for `<your-name>-sts-s3-integration-python` > Tick and Select Next
- Create User

Select each user and `Create access key`, record the `Access Key` and `Secret Key` in you .env file.

- In Python we will reference these values to upload to the S3 Bucket

### Create an IAM Role

- From the left-hand navigation pane in the Identity and Access Management (IAM) Dashboard, select Roles.
- Select `Create role`.
- Select the `AWS account` as the `Trusted entity type`.
- Select `This account (xxxxxxxxxxxxx)`
- Select the `Require external ID` option and enter a placeholder ID, `0000`.

An external ID is used to grant access to your AWS resources (such as S3 buckets) to a third party like Snowflake.In a later step, you will modify the trust relationship for your IAM role and specify the external ID for your storage integration.

- Select Next.
- Search for `<your-name>-sts-s3-integration` and select the python policy for access to the S3 Bucket
- Select Next.
- Enter a name, e.g. `<your-name>-snowflake-freeagent-python`, and description for the role, then select Create role
- You have now created an IAM policy for a bucket, created an IAM role, and attached the policy to the role.
- Click the role and record the Role ARN value

The trust policy should look like this.

```
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Principal": {
				"AWS": "arn:aws:iam::123456789012"
			},
			"Action": "sts:AssumeRole",
			"Condition": {
				"StringEquals": {
					"sts:ExternalId": "0000"
				}
			}
		}
	]
}
```

## </details>

\
Open terminal and login to AWS via the CLI single sign on. If you are having trouble please check the notes to configure the AWS CLI on [Notion](https://www.notion.so/theinformationlab/How-to-configure-the-AWS-CLI-for-access-to-TIL-AWS-resources-1e75772ad0a280d9aaebd8bb6fd937e6).

### Step 1: Create S3 Bucket and KMS Key

**Create KMS Key**

```
aws kms create-key --description "KMS key for freeagent S3 bucket encryption" --region eu-west-2 --profile <profile-name> --tags TagKey=creator,TagValue=<your-name> TagKey=cohort,TagValue=<cohort> TagKey=project,TagValue=<project> TagKey=Usage,TagValue=Training
```

After KEYMETADATA, record the ARN, noting the KeyId from the output, e.g. arn:aws:kms:eu-west-2:<account_id>:key/`KeyId` then create an alias for the key.

Update this command with:

- KMS Alias: **your-name-freeagent-kms-key**
- KeyId: **KeyId** from-previous-command

```
aws kms create-alias --alias-name alias/<your-name>-freeagent-kms-key --target-key-id <KeyId> --region eu-west-2 --profile <profile-name>
```

**Create S3 Bucket**

Update this command with:

- Bucket name: **your-name-freeagent-storage**

```
aws s3api create-bucket --bucket <your-name>-freeagent-storage --create-bucket-configuration LocationConstraint=eu-west-2 --profile <profile-name>
```
And apply the tagging after:
```
aws s3api put-bucket-tagging --bucket <your-name>-freeagent-storage --profile <profile-name> --tagging 'TagSet=[{Key=creator,Value=<your-name>},{Key=cohort,Value=<cohort>},{Key=project,Value=<project>},{Key=Usage,Value=Training}]'
```

**Secure Bucket**

Enable encryption

Update this command with:

- Bucket name: **your-name-freeagent-storage**
- KMS Alias: **your-name-freeagent-kms-key** in `aws/week_2/s3-bucket-encryption.json`

```
aws s3api put-bucket-encryption --bucket <your-name>-freeagent-storage --server-side-encryption-configuration file://aws/week_2/s3-bucket-encryption.json --profile <profile-name>
```

Block public access

Update this command with:

- Bucket name: **your-name-freeagent-storage**

```
aws s3api put-public-access-block --bucket <your-name>-freeagent-storage --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true --profile <profile-name>
```

Disable ACLs

Update this command with:

- Bucket name: **your-name-freeagent-storage**

```
aws s3api put-bucket-ownership-controls --bucket <your-name>-freeagent-storage --ownership-controls "Rules=[{ObjectOwnership=BucketOwnerEnforced}]" --profile <profile-name>
```

**Create Folder for Data Import**

Update these commands with:

- Bucket name: **your-name-freeagent-storage**

```
aws s3api put-object --bucket <your-name>-freeagent-storage --key python-import/ --profile <profile-name>
```

### Step 2: Create IAM Policies to Upload to AWS

**Get Your KMS Key ARN**

Either recall it from earlier, it has the form: arn:aws:kms:eu-west-2:account_id:key/`KeyId`
Or run this command with your KMS Alias: **your-name-freeagent-kms-key**

```
aws kms describe-key --key-id alias/<your-name>-freeagent-kms-key --region eu-west-2 --query 'KeyMetadata.Arn' --output text --profile <profile-name>
```

**Update IAM Policies with KMS Key ARN**

For these files, update the bucket name and update line 22 with your KMS Key ARN:

- [aws/week_2/iam-policy-python.json](../aws/week_2/iam-policy-python.json)

**Create the Policies and Record the ARNs**

```
aws iam create-policy --policy-name <your-name>-sts-s3-integration-python --policy-document file://aws/week_2/iam-policy-python.json --profile <profile-name> --tags 'Key=creator,Value=<your-name>' 'Key=cohort,Value=<cohort>' 'Key=project,Value=<project>' 'Key=Usage,Value=Training'
```

**Create IAM Users**

```
aws iam create-user --user-name <your-name>_freeagent_python_uploader --profile <profile-name> --tags 'Key=creator,Value=<your-name>' 'Key=cohort,Value=<cohort>' 'Key=project,Value=<project>' 'Key=Usage,Value=Training'
```

**Attach Policies to Users**

```
aws iam attach-user-policy --user-name <your-name>_freeagent_python_uploader --policy-arn arn:aws:iam::<account-id>:policy/<your-name>-sts-s3-integration-python --profile <profile-name>
```

**Create and Record Access Keys**

```
aws iam create-access-key --user-name <your-name>_freeagent_python_uploader --profile <profile-name>
```

Record the Access Key and the Secret Key

- In Python we will reference these values to upload to the S3 Bucket

---

## Loading with Python

### Loading Data to S3 in Python

Boto3 is an AWS Python package, maintained by AWS, and is the package for implementing the Python SDK.

```
import boto3

# Create an S3 Client using AWS Credentials
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

# Upload file (Key) to S3 Bucket
s3_client.upload_file(Filename, Bucket, Key)
```

Parameters:

- Filename (str) – The source, the file path to the file to upload.
- Bucket (str) – The name of the bucket to upload to.
- Key (str) – The destination, path to the file in the S3 bucket.

Source: [Boto3 S3 upload_file()](https://boto3.amazonaws.com/v1/documentation/api/1.35.9/reference/services/s3/client/upload_file.html)

Here we import the boto3 library, configure the boto3 for AWS S3 and implement the file upload function.

### Python Environment Setup

In your freeagent folder, edit the .env file to include the following variables, edited with the correct keys.

```
AWS_ACCESS_KEY = 'xxxxxxxxxxxxxxxxxx'
AWS_SECRET_KEY = 'xxxxxxxxxxxxxxxxxx'
AWS_REGION = 'xxxxxxxxxxxxxxxxxx'
AWS_BUCKET_NAME = 'bucket-name'
```

Activate the environment

```
# Windows
.venv/Scripts/activate

# Mac / Linux
source .venv/bin/activate
```

Install required packages

```
pip install boto3
```

Update your requirements.txt file

```
pip freeze > requirements.txt
```
### Python Script

**1. Verify you can upload a file to the S3 Bucket**

Take a file from the extracted folder from last week and rename it "test_upload.json"

Exclude this file in your .gitignore

```
*test_upload.json
```

Write a script to test that you can upload this file to S3. Below is an example script for if you get stuck. 

<details>
    <summary>freeagent_load_single_file.py</summary>

```
# Single JSON file upload to S3 with KMS key

# Load libraries
import boto3
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Read .env file
aws_access_key=os.getenv('AWS_ACCESS_KEY')
aws_secret_key=os.getenv('AWS_SECRET_KEY')
aws_bucket_name=os.getenv('AWS_BUCKET')

# Create S3 Client using AWS Credentials
s3_client = boto3.client(
    's3',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

# Set file start and end points
local_file_location = "test_upload.json"
aws_file_destination = "python-import/test_upload.json"

# Upload file to S3 Bucket
s3_client.upload_file(local_file_location, aws_bucket_name, aws_file_destination)

print("File uploaded")
```

</details>

/

## Snowflake

### In AWS: Create IAM Policy for Storage Integration to Snowflake

**Create Role**

In the file [aws/week_2/iam-policy-snowflake-trust.json](../aws/week_2/iam-policy-snowflake-trust.json) update with your account id.

```
aws iam create-role --role-name <your-name>-snowflake-freeagent-python --assume-role-policy-document file://aws/week_2/iam-policy-snowflake-trust.json --description "Role for Snowflake to access S3 python-import folder" --profile <profile-name> --tags 'Key=creator,Value=<your-name>' 'Key=cohort,Value=<cohort>' 'Key=project,Value=<project>' 'Key=Usage,Value=Training'
```

**Attach Policy**

```
aws iam attach-role-policy --role-name <your-name>-snowflake-freeagent-python --policy-arn arn:aws:iam::<account-id>:policy/<your-name>-sts-s3-integration-python --profile <profile-name>
```

### Configure Snowflake Storage Integration

Snowflake Stages are locations where data files are stored (staged) for loading and unloading data. They are used to move data from one place to another, and the locations for the stages could be internal or external to the Snowflake environment.

Businesses can use a Snowflake stage to move their data from external data sources such as S3 buckets to internal Snowflake tables or vice-versa.

### Log in to Snowflake

- Sign in to The Information Lab's Snowflake Account.
- Database: TIL_DATA_ENGINEERING
- Role: DATASCHOOL

### Create a Personal Schema

```
CREATE SCHEMA <your-name>_freeagent_STAGING;
```

### Configure Snowflake Storage Integration

Snowflake Stages are locations where data files are stored (staged) for loading and unloading data. They are used to move data from one place to another, and the locations for the stages could be internal or external to the Snowflake environment.

Businesses can use a Snowflake stage to move their data from external data sources such as S3 buckets to internal Snowflake tables or vice-versa.

### Log in to Snowflake

- Sign in to The Information Lab's Snowflake Account.
- Database: TIL_DATA_ENGINEERING
- Role: DATASCHOOL

### Create Storage Integration

1. Run the following SQL command in Snowflake to create a storage integration:

```
CREATE OR REPLACE STORAGE INTEGRATION <your-name>_freeagent_python_import
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::<account-id>:role/<your-name>-snowflake-freeagent-python'
  STORAGE_ALLOWED_LOCATIONS = ('s3://<your-name>-freeagent-storage/python-import/');
```

STORAGE_AWS_ROLE_ARN is the ARN of the Snowflake via Python role, this command will retrieve it.

```
aws iam get-role --role-name <your-name>-snowflake-freeagent-python --query 'Role.Arn' --output text
```

2. Verify the Integration

Run the following command to describe the integration and retrieve the required information:

```
DESC INTEGRATION <your-name>_freeagent_python_import;
```

3. Record Key Details:

Note the following values from the output:

- **STORAGE_AWS_IAM_USER_ARN** This is the IAM user ARN created by Snowflake.
- **STORAGE_AWS_EXTERNAL_ID** This is the external ID required for updating the IAM role trust relationship.

### Grant the IAM User Permissions to Access Bucket Objects

Granting the IAM user permissions ensures that Snowflake can securely assume the role required to access the specified S3 bucket. Without these permissions, Snowflake cannot read or write data, which disrupts the integration process. Using the STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID adds an additional layer of security by enforcing a trust relationship and limiting access to only the intended external system.

Update the Snowflake trust policy with the details from DESC INTEGRATION

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "<snowflake_user_arn>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<snowflake_external_id>"
        }
      }
    }
  ]
}
```

Then run the command

```
aws iam update-assume-role-policy --role-name <your-name>-snowflake-freeagent-python --policy-document file://aws/week_2/iam-policy-snowflake-trust.json
```

Note if you change or recreate the storage integration the `<snowflake_external_id>` will change and you will have to redo this step.

If you get stuck at any point you can refer to the below. 
<details>
<summary>AWS Console GUI Method</summary>
- Log in to the AWS Management Console.
- Select IAM.
- From the left-hand navigation pane, select Roles.
- Select the role you created earlier
- Select the Trust Relationships tab.
- Select Edit trust policy.
- Modify the policy document with the DESC STORAGE INTEGRATION output values you recorded from the Snowflake Account

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "<snowflake_user_arn>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<snowflake_external_id>"
        }
      }
    }
  ]
}
```

- Select Update policy to save your changes.
</details>

### Create New External Stages

External stages act as a bridge between Snowflake and the data stored in S3. By creating these stages, you establish a connection that allows Snowflake to efficiently query and manage data in its native format. This step is essential for simplifying data ingestion and enabling downstream transformations or analyses.

**1. Define the Stage**

Use the following SQL command to create an external stage for the S3 bucket:

```
CREATE OR REPLACE FILE FORMAT <your-name>_json_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = TRUE;

CREATE OR REPLACE STAGE <your-name>_freeagent_python_stage
  STORAGE_INTEGRATION = <your-name>_freeagent_python_import
  URL = 's3://<your-name>-freeagent-storage/python-import/'
  FILE_FORMAT = <your-name>_json_format;
```

**2. View Stage Contents**

Using the Snowflake operation `LIST` you can see all objects on the stage (in the S3 bucket).

```
LIST @<your-name>_freeagent_python_stage;
```

**3. Copy the files into a raw table**

```
CREATE OR REPLACE TABLE <your-name>_freeagent_STAGING.freeagent_events_raw_python (
  json_data VARIANT
);

COPY INTO <your-name>_STAGING.freeagent_events_raw_python
FROM @<your-name>_freeagent_python_stage
FILE_FORMAT = (FORMAT_NAME = <your-name>_json_format);

SELECT *
FROM <your-name>_STAGING.freeagent_events_raw_python
LIMIT 100;
```

---

## If you have time to update your Python scripts

### Create a function to Extract from the API

<details>
    <summary>Python Script</summary>

```
import requests
from datetime import datetime

def extract_freeagent_data(start_date, end_date, api_key, secret_key, output_file='data.zip'):
    """
    Extract data from freeagent's Export API for a given date range.

    Args:
        start_date (str): Start date in format 'YYYYMMDDTHH' (e.g., '20241101T00')
        end_date (str): End date in format 'YYYYMMDDTHH' (e.g., '20241101T23')
        api_key (str): freeagent API key
        secret_key (str): freeagent secret key
        output_file (str): Output filename for the downloaded data (default: 'data.zip')

    Returns:
        bool: True if successful, False otherwise
    """
    # API endpoint for EU residency server
    url = 'https://analytics.eu.freeagent.com/api/2/export'
    params = {
        'start': start_date,
        'end': end_date
    }

    try:
        # Make the GET request with basic authentication
        response = requests.get(url, params=params, auth=(api_key, secret_key))

        # Check the response status
        if response.status_code == 200:
            # The request was successful
            data = response.content
            print('Data retrieved successfully.')

            # Save data to file
            with open(output_file, 'wb') as file:
                file.write(data)
            print(f'Data saved to {output_file}')
            return True
        else:
            # The request failed
            print(f'Error {response.status_code}: {response.text}')
            return False

    except Exception as e:
        print(f'An error occurred: {str(e)}')
        return False
```

</details>

### Create a function to Check data in S3

<details>
    <summary>Python Script</summary>

```
import boto3

def list_s3_files(bucket_name, aws_access_key_id, aws_secret_access_key, s3_folder=""):
    """
    List all files in an S3 bucket folder.

    Args:
        bucket_name (str): S3 bucket name
        aws_access_key_id (str): AWS access key
        aws_secret_access_key (str): AWS secret key
        s3_folder (str): Folder path (e.g., "my-folder/")

    Returns:
        list: File names in the folder
    """
    s3 = boto3.client('s3',
                      aws_access_key_id=aws_access_key_id,
                      aws_secret_access_key=aws_secret_access_key)

    files = []
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_folder):
        if 'Contents' in page:
            files.extend([obj['Key'] for obj in page['Contents']])

    return files
```

</details>

### Build a Script to Call S3 for what files it needs and upload them from the API

<details>
    <summary>Python Script</summary>

```
import re
import os
from datetime import datetime, timedelta, date

def find_missing_freeagent_data(bucket_name, aws_access_key_id, aws_secret_access_key, s3_folder, start_date=None, end_date=None):
    """
    Check S3 bucket for missing freeagent data files.

    Args:
        bucket_name (str): S3 bucket name
        aws_access_key_id (str): AWS access key
        aws_secret_access_key (str): AWS secret key
        s3_folder (str): S3 folder prefix
        start_date (date, optional): Start date. Defaults to 1 week before yesterday
        end_date (date, optional): End date. Defaults to yesterday

    Returns:
        list: List of tuples (start_date, end_date) for missing data ranges
    """
    # Ensure end_date is a date object
    if end_date is None:
        end_date = date.today() - timedelta(days=1)
    elif isinstance(end_date, datetime): # If it's a datetime object, convert to date
        end_date = end_date.date()

    # Ensure start_date is a date object (if provided)
    if start_date is not None and isinstance(start_date, datetime):
        start_date = start_date.date()

    # Fix folder path
    if not s3_folder.endswith('/'):
        s3_folder += '/'

    # Get files from S3
    files = list_s3_files(bucket_name, aws_access_key_id, aws_secret_access_key, s3_folder)

    # Set start_date default based on files
    if start_date is None:
        file_dates = []
        for file in files:
            match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d+)', file)
            if match:
                date_str = match.groups()[0]
                file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                file_dates.append(file_date)

        if file_dates:
            start_date = min(file_dates)
        else:
            start_date = end_date - timedelta(days=7)

    # Extract existing dates and hours
    existing_hours = set()
    for file in files:
        match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d+)', file)
        if match:
            date_str, hour_str = match.groups()
            file_date = datetime.strptime(date_str, '%Y-%m-%d').date() # file_date is a datetime.date object
            hour = int(hour_str)

            # Only keep files in our date range
            # At this point, start_date, file_date, and end_date should all be datetime.date objects
            if start_date <= file_date <= end_date:
                dt = datetime.combine(file_date, datetime.min.time()) + timedelta(hours=hour)
                existing_hours.add(dt)

    # Generate all required hours
    # These conversions are correct for creating datetime objects for hour-level granularity
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.min.time()) + timedelta(hours=23)

    required_hours = []
    current = start_dt
    while current <= end_dt:
        required_hours.append(current)
        current += timedelta(hours=1)

    # Find missing hours
    missing_hours = [h for h in required_hours if h not in existing_hours]

    if not missing_hours:
        return []

    # Group into ranges (max 7 days each)
    ranges = []
    start = missing_hours[0]
    end = missing_hours[0]

    for hour in missing_hours[1:]:
        if hour == end + timedelta(hours=1) and (hour - start).days < 7:
            end = hour  # Extend range if consecutive and under 7 days
        else:
            ranges.append((start.strftime('%Y%m%dT%H'), end.strftime('%Y%m%dT%H')))
            start = end = hour

    # Add final range
    ranges.append((start.strftime('%Y%m%dT%H'), end.strftime('%Y%m%dT%H')))

    return ranges
```

</details>

### Build a Script upload the missing files to S3

<details>
    <summary>Python Script</summary>

```
def upload_to_s3(bucket_name, aws_access_key,aws_secret_key,local_folder,s3_folder):

    # Assign slashes if missing
    local_folder = local_folder if local_folder.endswith('/') else local_folder + '/'
    s3_folder = s3_folder if s3_folder.endswith('/') else s3_folder + '/'

    # Create S3 Client using AWS Credentials
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )

    files_to_upload = []
    for root, _, filenames in os.walk(local_folder):
        files_to_upload.extend(filenames)

    for file in files_to_upload:
        aws_file_destination = s3_folder + file
        local_path = local_folder + file
        s3_client.upload_file(local_path, bucket_name, aws_file_destination)
        print(f"✓ Uploaded: {file}")
```

</details>

### Build a Script to Call S3 for to check what local files have been uploaded, remove the local files if uploaded

<details>
    <summary>Python Script</summary>

```
from pathlib import Path

def cleanup_uploaded_files(local_folder, s3_files):
    """
    Delete local files that exist in S3, rename folder if files remain.

    Args:
        local_folder (str): Local folder path
        s3_files (list): List of S3 filenames (without path)
    """
    local_path = Path(local_folder)
    if not local_path.exists():
        return

    local_files = [f.name for f in local_path.iterdir() if f.is_file()]
    s3_set = set(s3_files)

    # Delete files that are in S3
    remaining_files = []
    for filename in local_files:
        if filename in s3_set:
            (local_path / filename).unlink()
        else:
            remaining_files.append(filename)

    # Rename folder if files remain, otherwise remove empty folder
    if remaining_files:
        local_path.rename(local_path.parent / "data_failed_to_upload")
    else:
        local_path.rmdir()
```

</details>

### Create a script to extract and load the new/missing data

[freeagent_extract_and_load.py](freeagent_extract_and_load)

<details>
    <summary>freeagent_extract_and_load.py</summary>

```
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Import local functions
from modules.extract import extract_freeagent_data, extract_json_files
from modules.load import list_s3_files, find_missing_freeagent_data, upload_to_s3, cleanup_uploaded_files

load_dotenv()

yesterday = datetime.now() - timedelta(days=1)

# Start_date is usable argument, it default to the earliest date in S3
missing = find_missing_freeagent_data(
    bucket_name = os.getenv('AWS_BUCKET'),
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key = os.getenv('AWS_SECRET_KEY'),
    s3_folder="python-import",
    end_date = yesterday
)

print("Missing data ranges:")
for start, end in missing:
    print(f"  {start} to {end}")

# Loop through and extract missing files from API
# Some API calls will fail if there was no data received for that hour
for start, end in missing:
    success = extract_freeagent_data(start, end,
                                    os.getenv('AMP_API_KEY'),
                                    os.getenv('AMP_SECRET_KEY'))
    print(f"{'✓' if success else '✗'} {start} to {end}")

# Extract the main zip file
zip_path = "data.zip"
output_folder = "data"
extract_json_files(zip_path,output_folder)

# Upload files to S3
upload_to_s3(
    bucket_name = os.getenv('AWS_BUCKET'),
    aws_access_key = os.getenv('AWS_ACCESS_KEY'),
    aws_secret_key = os.getenv('AWS_SECRET_KEY'),
    local_folder = output_folder,
    s3_folder = 'python-import'
)

# Get S3 files and extract just filenames
s3_files = list_s3_files(
    bucket_name=os.getenv('AWS_BUCKET'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
    s3_folder="python-import/"
)

# Strip folder prefix to get just filenames
s3_filenames = [f.replace("python-import/", "") for f in s3_files if f.replace("python-import/", "")]

# Clean up local folder and zip folder
cleanup_uploaded_files("./data", s3_filenames)
os.remove(zip_path)
```

</details>

## Appendix

### References

Data Load Patterns - https://tobikodata.com/data_load_patterns_101.html

What Are Snowflake Stages? - https://www.phdata.io/blog/what-are-snowflake-stages/

freeagent's Export API - https://freeagent.com/docs/apis/analytics/export

Boto3 Upload File - https://boto3.amazonaws.com/v1/documentation/api/1.35.9/reference/services/s3/client/upload_file.html

<details>
<summary> Archive </summary>

## Airbyte Cloud

### Create a New Destination: S3

Create new destination

- Set up a new destination
- Select S3
- Enter the S3 access key, secret access key configured earlier for "<your-name>\_freeagent_airbyte_uploader"
- S3 Bucket Name: "<your-name>-freeagent-storage"
- S3 Bucket Path: "airbyte-sync"
- S3 Bucket Region: same region as in AWS (most likely to be eu-west-2)
- Output format: JSON
- Click Set up destination
- Test destination

Select streams

- Select all tables
- Sync mode: Append for all, Incremental where possible,
  i.e. "Incremental | Append", otherwise "Full refresh | Append"

Configure connection

- Schedule Type: Scheduled
- Replication frequency: Every 24 hours
- Destination Namespace (determines folder name for data stored): Custom format "freeagent"
- Sync

After 15 minutes data should start appearing in the S3 Bucket.
</details>