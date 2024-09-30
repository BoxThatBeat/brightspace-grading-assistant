import json
import os
import requests
import zipfile
import subprocess

# Note: don't forget the last / of URLs

# Good API ref: https://github.com/an-algonquin-facilitator/assistant/tree/main/src/api

# To get the auth token, you need to login to Brightspace and run the following in the console:
#console.log(JSON.parse(localStorage["D2L.Fetch.Tokens"])["*:*:*"].access_token);

# Replace auth token each run (lasts 1 hour)
#AUTH_TOKEN = 'eyJhbGciOiJSUzI1NiIsImtpZCI6ImU3NjNlMGJhLTgzMDAtNDk4YS04MzI1LWQ4Mjk4NGFlMTViOSIsInR5cCI6IkpXVCJ9.eyJuYmYiOjE3Mjc3MDUyMDcsImV4cCI6MTcyNzcwODgwNywiaXNzIjoiaHR0cHM6Ly9hcGkuYnJpZ2h0c3BhY2UuY29tL2F1dGgiLCJhdWQiOiJodHRwczovL2FwaS5icmlnaHRzcGFjZS5jb20vYXV0aC90b2tlbiIsInN1YiI6IjE4NjczNyIsInRlbmFudGlkIjoiZDUyYTVkMWUtYWI5NC00MTU5LWJiZWYtYWNlMDA5MzYxNmRjIiwiYXpwIjoibG1zIiwic2NvcGUiOiIqOio6KiIsImp0aSI6ImFlMThmZWY0LWM1Y2MtNDJlZC1hMGEyLWMyNTQ4OWJiOGJiNSJ9.IQa8GDqdwq7zzu30hkWgs4hWi845Pw32SBlWSLndjGsMxEKb9Jb7IFTabRptO2pCJwln6c0M3zYTjm0I33Ocp1EJsYnsJWjlnqUqGnk4pgmcXEkxrPUaBtKqfbMvQjbzz01WlOuFO7fSB84q_OrZk54jePCZHp0kWBmfVOKWg_bwE6d_65Z7noyBAuLSIa23dWdHzs3h3gso6u5cAZhmnEPj9fEpC9rkY-CQC-u9k-l56eNs-mgtyoQ2f3ZUf-oo1oqyGlA2TzSpa0p2VVY68Hrra2K4NbJUUh6BZDknWOhCFF2t3i94PfgpGFAWUMl25Cyl2agSAp_baBBoZow83g'
headers = {}

HOST = "https://d52a5d1e-ab94-4159-bbef-ace0093616dc.organizations.api.brightspace.com" #HOST = "https://brightspace.algonquincollege.com"
LP_VERSION = "1.9"
LE_VERSION = "1.74"
LP_BASE_URL = f"{HOST}/d2l/api/lp/{LP_VERSION}"
LE_BASE_URL = f"{HOST}/d2l/api/le/{LE_VERSION}"

COURSE_ID = '691169' #Course Name: 24F_CST8288_451 OOP with Design Patterns, Course ID: 691169
SUBMISSION_FOLDER_ID  = '645558' #TODO: get this dynamically
SUBMISSION_FOLDER_NAME = 'Assignment 1'
CONTAINER_FOLDER = 'Assignments'

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
        for course in courses:
            course_info = course.get('OrgUnit', {})
            print(f"Course Name: {course_info.get('Name')}, Course ID: {course_info.get('Id')}")
    else:
        print(f"Failed to retrieve courses: {response.status_code}")

def get_course():
    url = f'{LP_BASE_URL}/courses/{COURSE_ID}'
    response = requests.get(url, headers=headers)
    print(response.json())

def get_folders():
    url = f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/'
    
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        folders = response.json()
        
        for folder in folders:
            print (f'{folder['Name']} - {folder['Id']}')

def get_submissions(assignment_name):
    submissionsResponse = requests.get(f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/{SUBMISSION_FOLDER_ID}/submissions/', headers=headers)
    submissions = submissionsResponse.json()

    if submissionsResponse.status_code == 200:
      # create a dict of user names to id
      users = {}
      for submission in submissions:
          user_name = submission['Entity']['DisplayName']
          user_id = submission['Entity']['EntityId']
          users[user_id] = user_name
      
      print(f'Found {len(users)} submissions')

      download_submissions(users, assignment_name)
    else:
      print(f'Failed to retrieve submissions: {submissionsResponse.status_code}')

def download_submissions(user_map, assignment_name):
    
    for user_id, user_name in user_map.items():
        print(f'Downloading submission for {user_name}')

        userSubmittedFilesUrl = f'{LE_BASE_URL}/{COURSE_ID}/dropbox/folders/{SUBMISSION_FOLDER_ID}/submissions/{user_id}/download'
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
                if file.endswith('.zip'):

                    # Unzip to folder named 'submission'
                    with zipfile.ZipFile(os.path.join(root, file), 'r') as zip_ref:
                        zip_ref.extractall(os.path.join(root, 'submission'))

                    # Delete zip file
                    os.remove(os.path.join(root, file))


if __name__ == '__main__':
    print('Please run console.log(JSON.parse(localStorage["D2L.Fetch.Tokens"])["*:*:*"].access_token); in the browser console to get the auth token and paste it here: ')
    auth_token = input()

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }

    #get_courses()
    print('Do you wish to fetch recent submissions? (y/n)')
    if input() == 'y':
        get_submissions(SUBMISSION_FOLDER_NAME)

    while(True):
        print('Insert Username of submission to grade:')
        username = input()

        # Search in the user's submission folder for any zip files and unzip them
        user_folder = os.path.join(os.getcwd(), CONTAINER_FOLDER, SUBMISSION_FOLDER_NAME, username)

        print(f'Opening files for user {username}')
        if os.path.exists(user_folder):
            
            openedInVsCode = False
            print('Searching for bin or src folder and opening the parent folder in vscode')
            for root, dirs, files in os.walk(user_folder):
                for dir in dirs:
                    if dir == 'bin' or dir == 'src':
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
                    if file.endswith('.pdf') or file.endswith('.docx'):
                        print(file)
                        subprocess.run(['explorer.exe', file], cwd=root, shell=True)
        else:
            print('User not found, please try again')
            continue