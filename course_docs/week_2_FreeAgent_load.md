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

#### What is a Snowflake Storage Integration?

A Snowflake storage integration allows secure and seamless access to an Amazon S3 bucket by associating Snowflake with an IAM user configured for your account.

1. An external (i.e. S3) stage references a storage integration object in its definition.

2. Snowflake automatically associates the storage integration with an S3 IAM user created for your account. Snowflake creates a single IAM user that is referenced by all S3 storage integrations in your Snowflake account.

3. An AWS administrator in your organisation grants permissions to the IAM user to access the bucket referenced in the stage definition. Note that many external stage objects can reference different buckets and paths and use the same storage integration for authentication.

Source: https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration

## Setting up AWS

We're going to use the GUI to set everything up for AWS.

### AWS GUI Instructions

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
``
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

## Appendix

### References

Data Load Patterns - https://tobikodata.com/data_load_patterns_101.html

What Are Snowflake Stages? - https://www.phdata.io/blog/what-are-snowflake-stages/

freeagent's Export API - https://freeagent.com/docs/apis/analytics/export

Boto3 Upload File - https://boto3.amazonaws.com/v1/documentation/api/1.35.9/reference/services/s3/client/upload_file.html