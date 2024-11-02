import logging
import sys
import subprocess
import os
from github import Github
import psycopg2
import json
import uuid
from datetime import datetime


def get_pull_requests(repo):
    pulls = repo.get_pulls(state='open', sort='created')
    return pulls


def get_files_from_pr(repo, pr_number):
    pr = repo.get_pull(pr_number)
    files = pr.get_files()
    return files


def get_all_files_from_src(repo):
    src_files = repo.get_contents("src")
    all_files = {}

    def fetch_files(files):
        for file in files:
            if file.type == "dir":
                fetch_files(repo.get_contents(file.path))
            else:
                try:
                    # get the contents only files ending with .ts
                    if file.path.endswith(".ts") and not file.path.endswith(".d.ts") and not file.path.endswith(
                            "test.ts"):
                        all_files[file.path] = repo.get_contents(file.path).decoded_content.decode()
                except Exception as e:
                    print(f"Error reading {e}")

    fetch_files(src_files)
    return all_files


def minify_content(file_path, content):
    # Write the content to a temporary file
    with open("temp_input.txt", "w") as temp_input_file:
        temp_input_file.write("-------------\n")
        temp_input_file.write(f"File: {file_path}\n")
        temp_input_file.write("-------------\n")
        temp_input_file.write(content)

    # Call the minify.sh script
    subprocess.run(["./minify.sh", "temp_input.txt"])

    # Read the minified content from the output file
    with open("temp_input-min.txt", "r") as temp_output_file:
        minified_content = temp_output_file.read()

    # Clean up temporary files
    os.remove("temp_input.txt")
    os.remove("temp_input-min.txt")

    return minified_content


def save_to_database(pr_number, description, pr_title, diff_code_list, code, user_name, repo_owner, provider, db_config):
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO PullRequests (pr_number, title, diff_code, code, user_name, repo_owner, provider, created_at, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        diff_code_json = json.dumps(diff_code_list)
        created_at = int(datetime.now().timestamp() * 1000)

        cursor.execute(insert_query,
                       (pr_number, pr_title, diff_code_json, code, user_name, repo_owner, provider, created_at, description))

        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error saving to database: {e}")


def main(repo_name, pr_number, token, db_config):
    g = Github(token)
    repo = g.get_repo(repo_name)

    pr = repo.get_pull(pr_number)
    description = pr.body
    user_name = pr.user.login
    repo_owner = f"{repo.owner.login}/{repo.name}"
    provider = "Github"

    files = get_files_from_pr(repo, pr.number)
    diff_code_list = []
    diff_code = ""

    for file in files:
        diff_code_obj = {}
        filename = file.filename
        diff_code += file.raw_data['patch'] + "\n"
        diff_code_obj['file'] = filename
        diff_code_obj['code'] = file.raw_data['patch']
        diff_code_list.append(diff_code_obj)

    # Fetch all files from src folder and store in a dictionary
    all_files = get_all_files_from_src(repo)

    # save all files values into a txt file
    code = ""
    for file_path, content in all_files.items():
        minified_content = minify_content(file_path, content)
        code += minified_content + "\n"

    # Print values before saving to database
    print("Saving to database with the following values:")
    print(f"pr_number: {pr.number}")
    print(f"pr_title: {pr.title}")
    print(f"pr_diff_code: {diff_code_list}")
    print(f"user_name: {user_name}")
    print(f"repo_owner: {repo_owner}")
    print(f"provider: {provider}")
    print(f"code: {code}")

    # Save data to database
    save_to_database(pr.number, description, pr.title, diff_code_list, code, user_name, repo_owner, provider, db_config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 8:
        print("Usage: script.py <repo_name> <pr_number> <token> <db_host> <db_name> <db_user> <db_password>")
        sys.exit(1)
    repo_name = sys.argv[1]
    pr_number = int(sys.argv[2])
    token = sys.argv[3]
    db_config = {
        'host': sys.argv[4],
        'dbname': sys.argv[5],
        'user': sys.argv[6],
        'password': sys.argv[7]
    }
    main(repo_name, pr_number, token, db_config)
