"""
Personalise AWS course template files with name and AWS account ID.

To do:
1. Edit aws/.aws_env with their name and AWS account ID
2. Run: python aws/personalise.py
3. Find personalised files in the aws/ directory
"""

import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_env_file(env_path):
    """
    Load environment variables from .aws_env file.

    Args:
        env_path (str): Path to .aws_env file

    Returns:
        dict: Dictionary with YOUR_NAME and AWS_ACCOUNT_ID

    Raises:
        FileNotFoundError: If .aws_env file doesn't exist
        ValueError: If required variables are missing or invalid format
    """
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip("'\"")

    # Check required variables
    if not env_vars.get('YOUR_NAME'):
        raise ValueError("YOUR_NAME is not set in .aws_env file")
    if not env_vars.get('AWS_ACCOUNT_ID'):
        raise ValueError("AWS_ACCOUNT_ID is not set in .aws_env file")
    if not env_vars.get('PROFILE_NAME'):
        raise ValueError("PROFILE_NAME is not set in .aws_env file")
    if not env_vars.get('COHORT'):
        raise ValueError("COHORT is not set in .aws_env file")
    if not env_vars.get('PROJECT'):
        raise ValueError("PROJECT is not set in .aws_env file")

    # Validate YOUR_NAME format (single lowercase word, no spaces or dashes)
    your_name = env_vars['YOUR_NAME']
    if not re.match(r'^[a-z]+$', your_name):
        raise ValueError(
            f"YOUR_NAME must be a single lowercase word with no spaces or dashes.\n"
            f"      Got: '{your_name}'\n"
            f"      Examples: 'john', 'sarah', 'alex'"
        )

    profile_name = env_vars['PROFILE_NAME']
    if not re.match(r'^[a-z_]+$', profile_name):
        raise ValueError(
            f"PROFILE_NAME must be a lowercase word with no spaces or dashes (underscores allowed).\n"
            f"      Got: '{profile_name}'\n"
            f"      Examples: 'default', 'amplitude_test', 'til_ds'"
        )

    return env_vars


def format_name_for_aws(name):
    """
    Return name as-is (validation ensures it's already in correct format).

    Args:
        name (str): Name (already validated as lowercase single word)

    Returns:
        str: Name for AWS resources
    """
    return name


def personalise_content(content, your_name, aws_account_id, profile_name, cohort, project):
    """
    Replace placeholders in template content with user information.

    Replaces:
        <your-name> -> name (AWS format)
        <account-id> -> AWS account ID
        <profile-name> -> AWS profile name

    Args:
        content (str): Template file content
        your_name (str): Name in AWS format
        aws_account_id (str): AWS account ID
        profile_name (str): AWS profile name
        cohort (str): Cohort identifier
        project (str): Project name

    Returns:
        str: Personalised content
    """
    # Replace placeholder tags
    content = content.replace('<your-name>', your_name)
    content = content.replace('<account-id>', aws_account_id)
    content = content.replace('<account_id>', aws_account_id)
    content = content.replace('<profile-name>', profile_name)
    content = content.replace('<cohort>', cohort)
    content = content.replace('<project>', project)

    return content


def process_templates(templates_dir, aws_output_dir, course_docs_dir, markdown_template_path, your_name, aws_account_id, profile_name, cohort, project):
    """
    Process all template files and output personalised versions.

    Args:
        templates_dir (Path): Directory containing JSON template files
        aws_output_dir (Path): Directory to output JSON files
        course_docs_dir (Path): Directory to output markdown files
        markdown_template_path (Path): Path to markdown template file
        your_name (str): Name in AWS format
        aws_account_id (str): AWS account ID

    Returns:
        dict: Dictionary of processed files by type
    """
    processed_files = {'json': [], 'markdown': []}

    # Ensure output directories exist
    aws_output_dir.mkdir(parents=True, exist_ok=True)
    course_docs_dir.mkdir(parents=True, exist_ok=True)

    # Process JSON files in templates directory
    for template_file in templates_dir.iterdir():
        if template_file.is_file() and template_file.suffix == '.json':
            print(f"Processing: {template_file.name}")

            # Read template content
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Personalise content
            personalised_content = personalise_content(content, your_name, aws_account_id, profile_name, cohort, project)

            # JSON files go to aws/week_2/ directory
            output_file = aws_output_dir / template_file.name
            output_location = f"aws/week_2/{template_file.name}"
            processed_files['json'].append(template_file.name)

            # Write to output location
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(personalised_content)

            print(f"  → Created: {output_location}")

    # Process markdown template from course_docs
    if markdown_template_path.exists():
        print(f"Processing: {markdown_template_path.name}")

        # Read template content
        with open(markdown_template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Personalise content
        personalised_content = personalise_content(content, your_name, aws_account_id, profile_name, cohort, project)

        # Markdown file goes to course_docs/ with confidential_ prefix
        new_filename = f"confidential_{markdown_template_path.name}"
        output_file = course_docs_dir / new_filename
        output_location = f"course_docs/{new_filename}"
        processed_files['markdown'].append(new_filename)

        # Write to output location
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(personalised_content)

        print(f"  → Created: {output_location}")
    else:
        print(f"⚠ Warning: Markdown template not found at {markdown_template_path}")

    return processed_files


def main():
    """Main execution function."""
    # Get script directory (aws/)
    script_dir = Path(__file__).parent
    # Get project root directory
    project_root = script_dir.parent

    # Define paths
    env_file = script_dir / '.aws_env'
    templates_dir = script_dir / 'templates'
    aws_output_dir = script_dir / 'week_2'  # JSON files go to aws/week_2/
    course_docs_dir = project_root / 'course_docs'  # MD files go to course_docs/
    markdown_template = course_docs_dir / 'week_2_amplitude_load.md'  # MD template in course_docs/

    print("=" * 60)
    print("AWS Course Template Personalization Script")
    print("=" * 60)
    print()

    try:
        # Load environment variables
        print(f"Loading credentials from: {env_file.name}")
        env_vars = load_env_file(env_file)

        your_name = format_name_for_aws(env_vars['YOUR_NAME'])
        aws_account_id = env_vars['AWS_ACCOUNT_ID']
        profile_name = env_vars['PROFILE_NAME']
        cohort = env_vars['COHORT']
        project = env_vars['PROJECT']

        print(f"  Your Name: {your_name}")
        print(f"  AWS Account ID: {aws_account_id}")
        print(f"  AWS Profile Name: {profile_name}")
        print(f"  Cohort: {cohort}")
        print(f"  Project: {project}")
        print()

        # Process templates
        print(f"Processing templates from: {templates_dir.name}/ and {markdown_template.parent.name}/")
        print()
        processed_files = process_templates(templates_dir, aws_output_dir, course_docs_dir,
                                           markdown_template, your_name, aws_account_id, profile_name, cohort, project)

        print()
        print("=" * 60)
        print("Success! Personalised files created:")
        print("=" * 60)

        if processed_files['json']:
            print("\nJSON files (in aws/week_2/):")
            for filename in processed_files['json']:
                print(f"  - {filename}")

        if processed_files['markdown']:
            print("\nMarkdown files (in course_docs/):")
            for filename in processed_files['markdown']:
                print(f"  - {filename}")

        print()
        print("Note: You'll still need to manually replace <KeyId> placeholders")
        print("      after creating your KMS key in AWS.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure you run this script from the project root:")
        print("  python aws/personalise.py")
        return 1

    except ValueError as e:
        print(f"Error: {e}")
        print("\nPlease edit aws/.aws_env and set:")
        print("  YOUR_NAME='yourname'  (single lowercase word, no spaces/dashes)")
        print("  AWS_ACCOUNT_ID=123456789012")
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())