import os
import pickle
import csv

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    LEADERBOARD_INSTALLED = True
except:
    LEADERBOARD_INSTALLED = False


from assignment_checker import search_student_by_email, read_student_list

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def connect_to_spreadsheet(config):
    google_credentials_file = config['google_credentials_file']
    google_token_file = config['google_token_file']

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(google_token_file):
        with open(google_token_file, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                   google_credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(google_token_file, 'wb') as token:
            pickle.dump(creds, token)
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_leaderboard(config, service):
    spreadsheet_id = config['spreadsheet_id']
    sheet = service.spreadsheets()
    
    all_values = []
    for i_test in range(config['number_tests']):
        leaderboard_name = config['leaderboard_name']%(i_test + 1)
        leaderboard_range = f"{leaderboard_name}!A2:B"

        result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                    range=leaderboard_range).execute()
        values = result.get('values', [])
        all_values.append(values)

    return all_values


def prepare_data_for_leaderboard(config, data, with_private=False):
    student_list = read_student_list(config['student_list_file'])

    all_values = []
    for i_test in range(config['number_tests']):
        # select participats new values
        dd = [d for d in data if d['test_scores_competition'][i_test] is not None]
        # sort
        dd = sorted(dd, key=lambda d: d['test_scores_competition'], reverse=config['leaderboard_direction'].lower() == 'max')
        # prepare for writing
        values = []
        for d in dd:
            student_data = search_student_by_email(student_list, d['email'])
            student_name = f"{student_data['first_name']} {student_data['last_name']}"
            if student_data['role'].lower() == "student":
                item = [student_name, d['test_scores_competition'][i_test]]
                if with_private:
                    item.append(d['test_scores_competition_private'][i_test])
                values.append(item)

        # add baselines

        all_values.append(values)
    return all_values


def update_leaderboard(config, data):
    new_values = prepare_data_for_leaderboard(config, data)
    
    if config['use_private_split_after_competition']:
        new_values_with_private = prepare_data_for_leaderboard(config, data, with_private=True)
        update_local_leaderboard(config, new_values_with_private, with_private=True)
    else:
        update_local_leaderboard(config, new_values_with_private, with_private=False)

    update_spreadsheet_leaderboard(config, new_values)


def update_local_leaderboard(config, new_values, with_private=False):
    for i_test, values in enumerate(new_values):
        file_name = config['local_leader_board_file']%(i_test + 1)
        with open(file_name, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
            if not with_private:
                writer.writerow(['Student name', 'Public score'])
            else:
                writer.writerow(['Student name', 'Public score', 'Private score'])
            for cur_list in values:
                writer.writerow(cur_list)


def update_spreadsheet_leaderboard(config, new_values):
    try:
        service = connect_to_spreadsheet(config)
        old_values = get_leaderboard(config, service)

        for i_test in range(config['number_tests']):
            values = new_values[i_test]

            # get the range
            old_length = len(old_values[i_test])
            num_entries_to_write = max(old_length, len(values))
            if len(values) < num_entries_to_write:
                values = values + [ ["", ""] for _ in range(num_entries_to_write - len(values)) ]

            leaderboard_name = config['leaderboard_name']%(i_test + 1)
            leaderboard_range = f"{leaderboard_name}!A2:B{num_entries_to_write + 1}"

            # update
            body = {
                'values': values
            }
            result = service.spreadsheets().values().update(spreadsheetId=config['spreadsheet_id'],
                                                            range=leaderboard_range,
                                                            valueInputOption="USER_ENTERED", body=body).execute()
    except :
        exit_message = f"ERROR: could not update the leaderboard with config {config} and data {new_values}"
        print(exit_message)


def print_leaderboard(config):
    service = connect_to_spreadsheet(config)
    all_values = get_leaderboard(config, service)

    for i_test, values in enumerate(all_values):
        print(f"Competition {config['leaderboard_name']%(i_test + 1)}")
        if not values:
            print('No data found.')
        else:
            print('Student, Public Score')
            for row in values:
                print('%s, %s' % (row[0], row[1]))
