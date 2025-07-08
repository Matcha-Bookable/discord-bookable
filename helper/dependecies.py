# Simple script to check for the latest dependencies

import os, json
import urllib.request

def get_latest_version(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    with urllib.request.urlopen(url) as response:
        if response.status == 200:
            data = json.loads(response.read().decode())
            return data['info']['version']
    return None

def check_dependencies(requirements_file):
    dependencies = []
    all_up_to_date = True
    with open(requirements_file, 'r') as file:
        for line in file:
            if '==' in line:
                package_name, current_version = line.strip().split('==')
                latest_version = get_latest_version(package_name)
                dependencies.append((package_name, current_version, latest_version))
                if latest_version and latest_version != current_version:
                    print(f"{package_name}: Current version: {current_version}, Latest version: {latest_version}")
                    all_up_to_date = False
                else:
                    print(f"{package_name}: Up-to-date")
    return dependencies, all_up_to_date

def update_dependencies(requirements_file, dependencies):
    updated_lines = []
    with open(requirements_file, 'r') as file:
        for line in file:
            if '==' in line:
                package_name, current_version = line.strip().split('==')
                for dep in dependencies:
                    if dep[0] == package_name and dep[2] and dep[2] != current_version:
                        updated_lines.append(f"{package_name}=={dep[2]}\n")
                        break
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

    with open(requirements_file, 'w') as file:
        file.writelines(updated_lines)

if __name__ == "__main__":
    requirements_path = os.path.join(os.path.dirname(__file__), '../requirements.txt')
    dependencies, all_up_to_date = check_dependencies(requirements_path)
    if all_up_to_date:
        print("--\nAll dependencies are up-to-date, program will now terminate.")
    else:
        update = input("Do you want to update the dependencies? (Y/n): ").strip().lower()
        if update in ['y', 'yes', '']:
            update_dependencies(requirements_path, dependencies)
            print("--\nAll dependencies have been updated, program will now terminate.")