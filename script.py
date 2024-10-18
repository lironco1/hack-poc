import logging
import sys
import subprocess
import os
from github import Github

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

def main(repo_name, pr_number, token):
    g = Github(token)
    repo = g.get_repo(repo_name)

    pr = repo.get_pull(pr_number)
    print(f"PR #{pr.number}: {pr.title} by {pr.user.login}")
    files = get_files_from_pr(repo, pr.number)
    for file in files:
        filename = file.filename
        print(f"  - {filename}")
        print(file.raw_data['patch'])
        print("--------------------------------")
        print("--------------------------------")
        print("--------------------------------")

    # Fetch all files from src folder and store in a dictionary
    all_files = get_all_files_from_src(repo)

    # save all files values into a txt file
    with open("all_files.txt", "w") as f:
        for file_path, content in all_files.items():
            minified_content = minify_content(content)
            f.write("-------------\n")
            f.write(f"File: {file_path}\n")
            f.write("-------------\n")
            f.write(minified_content)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 4:
        print("Usage: script.py <repo_name> <pr_number> <token>")
        sys.exit(1)
    print(sys.argv[0])
    print(sys.argv[1])
    print(sys.argv[2])
    print(sys.argv[3])
    repo_name = sys.argv[1]
    pr_number = int(sys.argv[2])
    token = sys.argv[3]
    main(repo_name, pr_number, token)
