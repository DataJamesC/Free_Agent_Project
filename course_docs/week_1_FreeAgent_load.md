# Extract & Load Project: Amplitude

### Week 2 | Tuesday | Instructor Led Walkthrough

## Introduction

## Learning Objectives

- Considerations for Loading Data
- Configuring AWS
- Loading with Python
- Snowflake Storage Integrations

## Recap of Existing Processes

**Airbyte Cloud** Extract and load to AWS S3 bucket\
**Amplitude Export API** Python script to extract and store locally in a zip folder

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