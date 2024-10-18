import logging
import sys
import subprocess
import os
from github import Github
import psycopg2
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

def minify_content(content):
    # Write the content to a temporary file
    with open("temp_input.txt", "w") as temp_input_file:
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

def save_to_database(pr_number, pr_title, pr_diff_code, code, user_name, repo_owner, provider, db_config):
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO pr_data (pr_number, pr_title, pr_diff_code, code, user_name, repo_owner, provider, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (pr_number, pr_title, pr_diff_code, code, user_name, repo_owner, provider, datetime.now()))

        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error saving to database: {e}")


def main(repo_name, pr_number, token, db_config):
    g = Github(token)
    repo = g.get_repo(repo_name)

    pr = repo.get_pull(pr_number)
    user_name = pr.user.login
    repo_owner = f"{repo.owner.login}/{repo.name}"
    provider = "Github"

    print(f"PR #{pr.number}: {pr.title} by {user_name}")
    print("--------------------------------")
    print("--------------------------------")
    files = get_files_from_pr(repo, pr.number)
    pr_diff_code = ""
    for file in files:
        filename = file.filename
        print(f"  - {filename}")
        pr_diff_code += file.raw_data['patch'] + "\n"
        print(file.raw_data['patch'])
        print("--------------------------------")
        print("--------------------------------")

    # Fetch all files from src folder and store in a dictionary
    all_files = get_all_files_from_src(repo)

    # save all files values into a txt file
    code = ""
    with open("all_files.txt", "w") as f:
        for file_path, content in all_files.items():
            minified_content = minify_content(content)
            code += minified_content + "\n"
            print(minified_content)
            print("--------------------------------")
            print("--------------------------------")
            f.write("-------------\n")
            f.write(f"File: {file_path}\n")
            f.write("-------------\n")
            f.write(minified_content)

    # Save data to database
    save_to_database(pr.number, pr.title, pr_diff_code, code, user_name, repo_owner, provider, db_config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 8:
        print("Usage: script.py <repo_name> <pr_number> <token> <db_host> <db_name> <db_user> <db_password>")
        sys.exit(1)
    print(sys.argv[0])
    print(sys.argv[1])
    print(sys.argv[2])
    print(sys.argv[3])
    print(sys.argv[4])
    print(sys.argv[5])
    print(sys.argv[6])
    print(sys.argv[7])
    print("--------------------------------")
    print("--------------------------------")
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
