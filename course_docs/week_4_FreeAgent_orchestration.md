# Orchestration Project: FreeAgent
### Week 4 | Thursday | Instructor Led Walkthrough

## Introduction

So far we've run our FreeAgent extract scripts by hand from our laptops. In this session we'll hand that job to an **orchestrator**, so the pipeline runs on a schedule without anyone needing to press go.

[Kestra](https://kestra.io/docs) is an open-source orchestration platform. You describe a pipeline as a **flow** in YAML, a list of tasks such as "clone the repo" then "run the extract script", and Kestra runs them in order, on a schedule or trigger, and keeps the logs, outputs and history of every run. Each task's `type:` is a **plugin**, and there are plugins for git, Python, Snowflake, dbt and hundreds of other tools.

We'll run Kestra locally in **Docker**. Docker runs software in an isolated, throwaway Linux environment called a **container**, built from a downloadable **image**. When we start Kestra:

- The `kestra/kestra` image runs as a container, with `server local` starting all of Kestra's components (web UI, scheduler, executor, worker and a built-in database) in one process. The UI is then available at localhost:8080.
- Kestra is given access to Docker itself (`-v /var/run/docker.sock:...`), because it doesn't run our Python inside its own container. For each script task it starts a **fresh Python container**, passes in our cloned repo and credentials, runs the script and then deletes the container.

This has a few consequences you'll see throughout the session:
- `pip install` runs on every execution, because every run starts from a clean container.
- Credentials have to be passed in through the flow's `env` block, as there's no `.env` file in the container.
- Nothing saved to disk survives between runs, which is why our extract scripts keep their watermarks in S3.

## Learning Objectives
- Running tasks with Kestra
- Running code anywhere
- Debugging

## Set Up Kestra and GitHub Access

### 1. Start Kestra

You'll need Docker Desktop installed and running. In a terminal, run the command below to download the latest Kestra image and start it.

Windows 
```
docker run --pull=always --rm -it -p 8080:8080 --user=root -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp kestra/kestra:latest server local
```

MAC
```
docker run --pull=always --rm -it -p 8080:8080 --user=root -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -e JAVA_OPTS="-XX:UseSVE=0" kestra/kestra:latest server local
```
Source: [https://kestra.io/docs/getting-started/quickstart#start-kestra](https://kestra.io/docs/getting-started/quickstart#start-kestra)

When ready go to localhost:8080 and login. Leave this terminal open, closing it (or pressing Ctrl+C) stops Kestra.

If you have java related error messages, stop Kestra and try removing the image and pulling it again:

```
# Remove the kestra image

docker rmi kestra/kestra:latest


# Clean up any dangling images

docker image prune -f
```

Then run the `docker run` command above again, which will pull a fresh image.

**Note:** `server local` keeps Kestra's data inside the container, and `--rm` deletes the container when it stops. Your flows and KV Store values will be lost each time you stop Kestra, so keep a copy of your flow YAML in your repo.


### 2. Get GitHub token

How to Get Your GitHub Token to Access a Private Repo
To access a private GitHub repository, you need to generate a Personal Access Token (PAT) and use it in place of your password when authenticating via HTTPS. Here’s a concise, step-by-step guide:

1. Log in to GitHub and Go to Settings

Click your profile picture in the upper-right corner.
Select Settings from the dropdown menu.

2. Navigate to Developer Settings

In the left sidebar, click Developer settings.
Under Personal access tokens, choose either Tokens (classic) or Fine-grained tokens.

3. Generate a New Token

Click Generate new token (classic).
Give your token a name. "kestra_access"
Set an expiration date if desired.
Select the repo scope (all).
Click Generate token.

4. Copy and Store the Token Securely

The token will be displayed once. Copy it and store it securely in your .env file.

### 3. Using Kestra's KV Store

1. Start Kestra

If Kestra isn't already running, start it with the `docker run` command from step 1 and go to localhost:8080.

2. Set up a Hello World Flow

A flow is defined in YAML format and contains:
- **id**: A unique identifier for your flow
- **namespace**: Organizes your flows into logical groups (think of it like a folder structure)
- **tasks**: The actual work to be done

Update the namespace to 'til.des' as below.

```
id: hello_world
namespace: til.des

tasks:
  - id: example_task
    type: io.kestra.plugin.core.log.Log
    message: "Hello, World!"
```
Click Save and Execute your flow, you should see a message printed in the logs on the next screen. 

3. Add Values to the KV Store

The KV (Key-Value Pair) Store is perfect for:
- Configuration values you'll reuse across multiple flows
- Non-sensitive data like URLs, usernames, or settings
- Values that might change between environments

**Add your values to the KV Store:**

1. Navigate to the **KV Store** section in Kestra UI
2. Make sure you're in the `til.des` namespace 
3. Click **Create** to add a new key-value pair
4. Add the following key-value pairs:
   - **Key**: `GITHUB_USERNAME`, **Value**: Your GitHub username
   - **Key**: `GITHUB_TOKEN`, **Value**: The token you created in step 2
5. Click **Save**

**Why use the KV Store?**
- ✅ Easy to update values without changing flow code, or restarting Kestra
- ✅ Values are scoped by namespace, keeping environments separate

**Note:** The KV Store is typically used for non-sensitive data only. For our purposes it is acceptable to add our API Keys. Kestra has a **Secrets Manager** which can be used instead, which encrypts data at rest, the setup is much more involved - I have left the steps later if you are interested.

4. Reference KV Store Values in Your Flow

A flow reads values from the KV Store using the `{{ kv('KEY_NAME') }}` selector.

```
id: hello_kv
namespace: til.des

tasks:
  - id: print_github_user
    type: io.kestra.plugin.core.log.Log
    message: "GitHub username from KV Store: {{ kv('GITHUB_USERNAME') }}"
```

Execute the flow and check the logs. You should see your GitHub username printed.

- `{{ kv('GITHUB_USERNAME') }}` - Retrieves the value for key `GITHUB_USERNAME` from the KV Store in the current namespace (`til.des`)
- `{{ kv('KEY_NAME', 'other.namespace') }}` - You can also reference values from other namespaces
- The double curly braces `{{ }}` indicate a Pebble expression, which is Kestra's templating language


<details>
<summary>Kestra Secrets - No Action needed just FYI</summary>

For Kestra to read the credentials in the Secrets they are required to be encoded as base64 and stored with the prefix "SECRET_"

To convert a value to base64 use the following commands.

Windows via Powershell

```
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_secret_value"))
```

MAC/Linux

```
echo -n "your_secret_value" | base64
```

Add the base64 encoded value of your GitHub token and GitHub username to a new .env file `.env_encoded`

```
SECRET_GITHUB_USERNAME='your_username_as_base64'
SECRET_GITHUB_TOKEN='your_token_as_base64'
```

Update your gitignore to hide this file.
```
.env_encoded
```

To load the file into Kestra, add `--env-file .env_encoded` to the `docker run` command from step 1, run from the folder containing `.env_encoded`, e.g. on Windows:
```
docker run --pull=always --rm -it -p 8080:8080 --user=root --env-file .env_encoded -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp kestra/kestra:latest server local
```

### Update .env_encoded

Migrate the remaining API keys to base64 and add them to your .env_encoded file.
```
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your_secret_value"))
```
Your .env_encoded file should now look like this:

```
SECRET_GITHUB_USERNAME='your_username_as_base64'
SECRET_GITHUB_TOKEN='your_token_as_base64'

SECRET_FREEAGENT_CLIENT_ID = 'more_base64'
SECRET_FREEAGENT_CLIENT_SECRET = 'more_base64'
SECRET_FREEAGENT_REFRESH_TOKEN = 'more_base64'
SECRET_AWS_ACCESS_KEY_ID = 'more_base64'
SECRET_AWS_SECRET_ACCESS_KEY = 'more_base64'
SECRET_AWS_REGION = 'more_base64'
SECRET_AWS_BUCKET_NAME = 'more_base64'

```

Restart Kestra with the `--env-file` option for it to load these credentials. Flows then read them with `{{ secret('FREEAGENT_CLIENT_ID') }}` instead of `{{ kv('FREEAGENT_CLIENT_ID') }}`.

</details>

## Migrate our Project to Kestra

To start with we'll see if we can clone our GitHub repo to Kestra, so later we can run our scripts. 

### 1. Find Git Plugin and build as a Flow

In Kestra, navigate to Plugins, search for "GIT" and find a git clone for a private repo.

Now let's create a Flow that clones our repo. Replace the `repo_url` with the URL of your own FreeAgent project repo.

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: clone
    type: io.kestra.plugin.git.Clone
    url: "{{ vars.repo_url }}"
    branch: main
    username: "{{ kv('GITHUB_USERNAME') }}"
    password: "{{ kv('GITHUB_TOKEN') }}"
```

Execute with no additional settings. 

### 2. Add Python as another task. 

In Kestra, navigate to Plugins, search for "Python" and find ` io.kestra.plugin.scripts.python.Script`

Next, we'll want to run a Python script to test Python can work. Add another task to test that we can run Python. 

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: clone
    type: io.kestra.plugin.git.Clone
    url: "{{ vars.repo_url }}"
    branch: main
    username: "{{ kv('GITHUB_USERNAME') }}"
    password: "{{ kv('GITHUB_TOKEN') }}"

  - id: python
    type: io.kestra.plugin.scripts.python.Script
    beforeCommands:
      - pip install requests
      - pip install kestra
    script: |
      from kestra import Kestra
      import requests
      response = requests.get('https://kestra.io')
      print(response.status_code)
      Kestra.outputs({'status': response.status_code, 'text': response.text})

```

## Configure Kestra for our Python Script

### 1. Pip Install Requirements.txt

Try changing

```
      - pip install requests
```
To 
```
      - pip install -r requirements.txt
```

You'll receive, "No such file or directory: 'requirements.txt'" in the logs.

We need a working directory to clone the repository and access the files. This, in practice, is another task that wraps all the other tasks within it. 

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: wdir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone
        type: io.kestra.plugin.git.Clone
        url: "{{ vars.repo_url }}"
        branch: main
        username: "{{ kv('GITHUB_USERNAME') }}"
        password: "{{ kv('GITHUB_TOKEN') }}"

      - id: python
        type: io.kestra.plugin.scripts.python.Script
        beforeCommands:
          - pip install -r requirements.txt
          - pip install kestra
        script: |
          from kestra import Kestra
          import requests
          response = requests.get('https://kestra.io')
          print(response.status_code)
          Kestra.outputs({'status': response.status_code, 'text': response.text})
```

### 2. Update Python Script 

Now update your flow to use `io.kestra.plugin.scripts.python.Commands` to run the python script `Extract/extract_contacts.py`

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: wdir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone
        type: io.kestra.plugin.git.Clone
        url: "{{ vars.repo_url }}"
        branch: main
        username: "{{ kv('GITHUB_USERNAME') }}"
        password: "{{ kv('GITHUB_TOKEN') }}"

      - id: python
        type: io.kestra.plugin.scripts.python.Commands
        beforeCommands:
          - pip install -r requirements.txt
        commands:
          - python Extract/extract_contacts.py
```

This should fail, but why? 
Our Python script doesn't know the environment variables. Locally they come from our `.env` file, which (correctly) isn't in GitHub. Add each one to the KV Store, using the same names as your `.env` file:

- `FREEAGENT_CLIENT_ID`
- `FREEAGENT_CLIENT_SECRET`
- `FREEAGENT_REFRESH_TOKEN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_BUCKET_NAME`

We can then pass these to the script by calling them in the Kestra way as before with "{{ kv('GITHUB_USERNAME') }}" in an env block:

```
env:
  FREEAGENT_CLIENT_ID: "{{ kv('FREEAGENT_CLIENT_ID') }}"
  FREEAGENT_CLIENT_SECRET: "{{ kv('FREEAGENT_CLIENT_SECRET') }}"
  FREEAGENT_REFRESH_TOKEN: "{{ kv('FREEAGENT_REFRESH_TOKEN') }}"
  AWS_ACCESS_KEY_ID: "{{ kv('AWS_ACCESS_KEY_ID') }}"
  AWS_SECRET_ACCESS_KEY: "{{ kv('AWS_SECRET_ACCESS_KEY') }}"
  AWS_REGION: "{{ kv('AWS_REGION') }}"
  AWS_BUCKET_NAME: "{{ kv('AWS_BUCKET_NAME') }}"
```

`load_dotenv()` in our scripts doesn't complain when there's no `.env` file, and `os.getenv()` reads the values from this env block instead.

Now try running this flow.
```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: wdir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone
        type: io.kestra.plugin.git.Clone
        url: "{{ vars.repo_url }}"
        branch: main
        username: "{{ kv('GITHUB_USERNAME') }}"
        password: "{{ kv('GITHUB_TOKEN') }}"

      - id: python
        type: io.kestra.plugin.scripts.python.Commands
        beforeCommands:
          - pip install -r requirements.txt
        env:
          FREEAGENT_CLIENT_ID: "{{ kv('FREEAGENT_CLIENT_ID') }}"
          FREEAGENT_CLIENT_SECRET: "{{ kv('FREEAGENT_CLIENT_SECRET') }}"
          FREEAGENT_REFRESH_TOKEN: "{{ kv('FREEAGENT_REFRESH_TOKEN') }}"
          AWS_ACCESS_KEY_ID: "{{ kv('AWS_ACCESS_KEY_ID') }}"
          AWS_SECRET_ACCESS_KEY: "{{ kv('AWS_SECRET_ACCESS_KEY') }}"
          AWS_REGION: "{{ kv('AWS_REGION') }}"
          AWS_BUCKET_NAME: "{{ kv('AWS_BUCKET_NAME') }}"
        commands:
          - python Extract/extract_contacts.py
```

Check your S3 bucket for a new file in `python-import/contacts/`.

### 3. Extract All Endpoints to S3 

Our extract scripts upload straight to S3, so there's no separate load step. Now extend the flow to extract all five endpoints, either by listing each script in `commands` or by running `Extract/extract_all_incremental.py`, which does all five in one go.

Each Kestra execution starts from a fresh working directory, so nothing is remembered between runs on Kestra's side. This is why our scripts keep their watermarks in S3 (`python-import/_state/`) rather than on disk: every run picks up from where the last one, local or Kestra, left off.

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: wdir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone
        type: io.kestra.plugin.git.Clone
        url: "{{ vars.repo_url }}"
        branch: main
        username: "{{ kv('GITHUB_USERNAME') }}"
        password: "{{ kv('GITHUB_TOKEN') }}"

      - id: python
        type: io.kestra.plugin.scripts.python.Commands
        beforeCommands:
          - pip install -r requirements.txt
        env:
          FREEAGENT_CLIENT_ID: "{{ kv('FREEAGENT_CLIENT_ID') }}"
          FREEAGENT_CLIENT_SECRET: "{{ kv('FREEAGENT_CLIENT_SECRET') }}"
          FREEAGENT_REFRESH_TOKEN: "{{ kv('FREEAGENT_REFRESH_TOKEN') }}"
          AWS_ACCESS_KEY_ID: "{{ kv('AWS_ACCESS_KEY_ID') }}"
          AWS_SECRET_ACCESS_KEY: "{{ kv('AWS_SECRET_ACCESS_KEY') }}"
          AWS_REGION: "{{ kv('AWS_REGION') }}"
          AWS_BUCKET_NAME: "{{ kv('AWS_BUCKET_NAME') }}"
        commands:
          - python Extract/extract_all_incremental.py
```
### 4. Add a trigger

We can add a trigger for this to run every hour

```
id: freeagent_pipeline
namespace: til.des

variables:
  repo_url: "https://github.com/<your-github-username>/<your-freeagent-repo>.git"

tasks:
  - id: wdir
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:
      - id: clone
        type: io.kestra.plugin.git.Clone
        url: "{{ vars.repo_url }}"
        branch: main
        username: "{{ kv('GITHUB_USERNAME') }}"
        password: "{{ kv('GITHUB_TOKEN') }}"

      - id: python
        type: io.kestra.plugin.scripts.python.Commands
        beforeCommands:
          - pip install -r requirements.txt
        env:
          FREEAGENT_CLIENT_ID: "{{ kv('FREEAGENT_CLIENT_ID') }}"
          FREEAGENT_CLIENT_SECRET: "{{ kv('FREEAGENT_CLIENT_SECRET') }}"
          FREEAGENT_REFRESH_TOKEN: "{{ kv('FREEAGENT_REFRESH_TOKEN') }}"
          AWS_ACCESS_KEY_ID: "{{ kv('AWS_ACCESS_KEY_ID') }}"
          AWS_SECRET_ACCESS_KEY: "{{ kv('AWS_SECRET_ACCESS_KEY') }}"
          AWS_REGION: "{{ kv('AWS_REGION') }}"
          AWS_BUCKET_NAME: "{{ kv('AWS_BUCKET_NAME') }}"
        commands:
          - python Extract/extract_all_incremental.py

triggers:
  - id: hourly-extraction
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 * * * *"  # Every hour at minute 0
```


## Some other Kestra features to be aware of.  

Re-running a script:
```
retry:
  type: constant
  interval: PT30S  # 30 seconds
  maxAttempt: 3
  warningOnRetry: true
```

Echo in the commands section to print messages to the logs
```
commands:
  - echo "📦 Starting FreeAgent extract and S3 upload"
  - python Extract/extract_all_incremental.py
  - echo "✅ Data successfully loaded to S3"
```

[Flowable tasks: (Sequential, Parallel, Conditional)](https://kestra.io/docs/workflow-components/tasks/flowable-tasks)

Connect Kestra to:

- [DBT Cloud](https://kestra.io/plugins/plugin-dbt/dbt-cloud)
- [Snowflake](https://kestra.io/plugins/plugin-jdbc-snowflake)
