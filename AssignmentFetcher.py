import json
import os
import requests
import zipfile
import subprocess

# Good API ref: https://github.com/an-algonquin-facilitator/assistant/tree/main/src/api

headers = {}

HOST = "https://d52a5d1e-ab94-4159-bbef-ace0093616dc.organizations.api.brightspace.com" #HOST = "https://brightspace.algonquincollege.com"
LP_VERSION = "1.9"
LE_VERSION = "1.74"
LP_BASE_URL = f"{HOST}/d2l/api/lp/{LP_VERSION}"
LE_BASE_URL = f"{HOST}/d2l/api/le/{LE_VERSION}"

CONTAINER_FOLDER = 'Assignments'

# Submission folder data class
class SubmissionFolder:
    def __init__(self, id, name, num_submissions):
        self.id = id
        self.name = name
        self.num_submissions = num_submissions


def test():
    endpoint = f'{LE_BASE_URL}/dropbox/folders'
    response = requests.get(endpoint, headers=headers)
    print(response.text)
    #print(response.json())


def get_courses():
    endpoint = f'{LP_BASE_URL}/enrollments/myenrollments/'
    
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()  # raises exception when not a 2xx response    
    if response.status_code == 200:
        courses = response.json().get('Items', [])

        course_map = {}
        for course in courses:
            course_info = course['OrgUnit']
            if (course_info['Type']['Name'] == 'Course Offering'):
                course_map[course_info['Name']] = course_info['Id']
        return course_map
    else:
        print(f"Failed to retrieve courses: {response.status_code}")

def get_course():
    url = f'{LP_BASE_URL}/courses/{COURSE_ID}'
    response = requests.get(url, headers=headers)
    print(response.json())

def get_folders():
    url = f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/'
    
    response = requests.get(url, headers=headers)

    folders = []
    if response.status_code == 200:
        assignments = response.json()

        for assignment in assignments:
            # add folder to submissionFolder list
            folders.append(SubmissionFolder(assignment['Id'], assignment['Name'], assignment['TotalUsersWithSubmissions']))
    return folders
        

def get_submissions(assignment_name, assignment_folder_id):
    submissionsResponse = requests.get(f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/{assignment_folder_id}/submissions/', headers=headers)
    submissions = submissionsResponse.json()

    if submissionsResponse.status_code == 200:
      # create a dict of user names to id
      users = {}
      for submission in submissions:
          user_name = submission['Entity']['DisplayName']
          user_id = submission['Entity']['EntityId']
          users[user_id] = user_name
      
      print(f'Found {len(users)} submissions')

      download_submissions(users, assignment_name, assignment_folder_id)
    else:
      print(f'Failed to retrieve submissions: {submissionsResponse.status_code}')

def download_submissions(user_map, assignment_name, assignment_folder_id):
    
    for user_id, user_name in user_map.items():
        print(f'Downloading submission for {user_name}')

        userSubmittedFilesUrl = f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/{assignment_folder_id}/submissions/{user_id}/download'
        response = requests.get(userSubmittedFilesUrl, headers=headers)

        if response.status_code == 200:
            user_folder = os.path.join(os.getcwd(), CONTAINER_FOLDER, assignment_name, user_name)
            os.makedirs(user_folder, exist_ok=True)
            with open(os.path.join(user_folder, 'submission.zip'), 'wb') as file:
                file.write(response.content)
        else:
            print(f'Failed to download submission for {user_name} error code {response.status_code}')
        
        # Unizp the file
        with zipfile.ZipFile(os.path.join(user_folder, 'submission.zip'), 'r') as zip_ref:
            zip_ref.extractall(user_folder)
        
        # Delete zip file
        os.remove(os.path.join(user_folder, 'submission.zip'))
        
        for root, dirs, files in os.walk(user_folder):
            for file in files:
                if file.endswith('.zip') or file.endswith('.WAR') or file.endswith('.war'):

                    # Unzip to folder named 'submission'
                    with zipfile.ZipFile(os.path.join(root, file), 'r') as zip_ref:
                        zip_ref.extractall(os.path.join(root, 'submission'))

                    # Delete zip file
                    os.remove(os.path.join(root, file))


if __name__ == '__main__':
    print('Running Assignment Fetcher...')
    print('Run console.log(JSON.parse(localStorage["D2L.Fetch.Tokens"])["*:*:*"].access_token); in the browser console to get the auth token and paste it here: ')
    auth_token = input()

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    myCourses = get_courses()
    print('Please select which course you are grading by typing the corresponding number:')
    for i, course_name in enumerate(myCourses.keys()):
        print(f'{i+1}. {course_name}')

    course_index = int(input()) - 1
    COURSE_ID = myCourses[list(myCourses.keys())[course_index]]
    print(f'Selected course ID: {COURSE_ID}')

    print('Please select which assignment you are grading by typing the corresponding number:')

    folders = get_folders()
    for i, folder in enumerate(folders):
        print(f'{i+1}. ({folder.num_submissions} Submissions) : {folder.name}')

    folder_index = int(input()) - 1
    SUBMISSION_FOLDER_ID = folders[folder_index].id
    SUBMISSION_FOLDER_NAME = f'Assignment {folder_index + 1}'#folders[folder_index].name
    print(f'Selected folder ID: {SUBMISSION_FOLDER_ID}')

    print('Do you wish to fetch recent submissions? (y/n)')
    if input() == 'y':
        get_submissions(SUBMISSION_FOLDER_NAME, SUBMISSION_FOLDER_ID)

    while(True):
        print('Insert Username of submission to grade: (q to quit)')
        username = input()

        # trip whitespace on both ends of string
        username = username.strip()

        if (username == ''):
            print('Please enter a valid username')
            continue

        if username == 'q':
            break

        # Search in the user's submission folder for any zip files and unzip them
        user_folder = os.path.join(os.getcwd(), CONTAINER_FOLDER, SUBMISSION_FOLDER_NAME, username)

        print(f'Opening files for user {username}')
        if os.path.exists(user_folder):
            
            openedInVsCode = False
            print('Searching for bin or src folder and opening the parent folder in vscode')
            for root, dirs, files in os.walk(user_folder):
                for dir in dirs:
                    if dir == 'bin' or dir == 'src' or dir == 'WEB-INF':
                        # Cd into the folder and then run subprocess to open in vscode
                        print(os.path.join(root, dir))
                        subprocess.run(['code', '.'], cwd=os.path.join(root, dir, '..'), shell=True)
                        openedInVsCode = True
                        break;
                if openedInVsCode:
                    break;
            if not openedInVsCode:
                print('Searching for .java files and opening parent folder in vscode')
                for root, dirs, files in os.walk(user_folder):
                    for file in files:
                        print(file)
                        if file.endswith('.java'):
                            # Cd into the folder and then run subprocess to open in vscode
                            print(os.path.join(root, dir))
                            subprocess.run(['code', '.'], cwd=os.path.join(root, dir, '..'), shell=True)
                            openedInVsCode = True
                            break;
                    if openedInVsCode:
                        break;
            print('Searching for .docx or .pdf reports and opening it')
            for root, dirs, files in os.walk(user_folder):
                for file in files:
                    if file.endswith('.pdf') or file.endswith('.docx') or file.endswith('.rtf'):
                        print(file)
                        subprocess.run(['explorer.exe', file], cwd=root, shell=True)

            print('Opening any .wav or .mp4 or .MOV video files')
            for root, dirs, files in os.walk(user_folder):
                for file in files:
                    if file.endswith('.wav') or file.endswith('.mp4') or file.endswith('.MOV'):
                        print(file)
                        subprocess.run(['explorer.exe', file], cwd=root, shell=True)
        else:
            print('User not found, please try again')
            continue