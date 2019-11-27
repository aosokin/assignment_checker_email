import csv
import configparser
import os, sys
import zipfile
import subprocess
from copy import deepcopy
import math
import time
import pickle

try:
    import rarfile
    RAR_INSTALLED = True
except:
    RAR_INSTALLED = False

import gmail_communication
import robot_emails
import timezone

import leaderboard


def read_student_list(file_name):
    students = []
    with open(file_name, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in reader:
            cur_student = {}
            cur_student['last_name'] = row[0]
            cur_student['first_name'] = row[1]
            cur_student['role'] = row[2]
            cur_student['e-mails'] = row[3:]
            students.append(cur_student)
    return students


def read_config_file(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    config_data = {}
    config_data['course_e_mail'] = config.get('General','course_e_mail')
    config_data['course_e_mail_password'] = config.get('General','course_e_mail_password')
    config_data['student_list_file'] = config.get('General','student_list_file')
    config_data['teacher_email'] = config.get('General','teacher_email')
    config_data['student_score_file'] = config.get('General','student_score_file')
    config_data['email_check_pause_minutes'] = config.getfloat('General','email_check_pause_minutes')
    config_data['gmail_label'] = config.get('Assignment','gmail_label')
    config_data['solutions_path'] = config.get('Assignment','solutions_path')
    config_data['task_name'] = config.get('Assignment','task_name')
    config_data['number_tests'] = config.getint('Assignment','number_tests')
    config_data['test_pattern'] = config.get('Assignment','test_pattern')
    config_data['checker_cmd'] = config.get('Assignment','checker_cmd')
    config_data['test_data_pattern'] = config.get('Assignment','test_data_pattern')
    config_data['test_groundtruth_pattern'] = config.get('Assignment','test_groundtruth_pattern')
    config_data['deadline'] = config.get('Assignment','deadline')
    config_data['deadline_hard'] = config.get('Assignment','deadline_hard')
    config_data['timezone'] = config.get('Assignment','timezone')
    config_data['delay_day_penalty'] = config.getfloat('Assignment','delay_day_penalty')
    config_data['delay_cap'] = config.getfloat('Assignment','delay_cap')
    config_data['max_score'] = config.getfloat('Assignment','max_score')
    config_data['min_score'] = config.getfloat('Assignment','min_score')
    config_data['acceptance_threshold'] = config.getfloat('Assignment','acceptance_threshold')
    config_data['score_non_accepted'] = config.getfloat('Assignment','score_non_accepted')
    config_data['failed_emails_path'] = config.get('Assignment','failed_emails_path')

    config_data['use_leaderboard'] = config.getboolean('Leaderboard','use_leaderboard')
    config_data['google_credentials_file'] = config.get('Leaderboard','google_credentials_file')
    config_data['google_token_file'] = config.get('Leaderboard','google_token_file')
    config_data['spreadsheet_id'] = config.get('Leaderboard','spreadsheet_id')
    config_data['leaderboard_link'] = config.get('Leaderboard','leaderboard_link')
    config_data['leaderboard_direction'] = config.get('Leaderboard','leaderboard_direction')
    config_data['leaderboard_entry_threshold'] = config.get('Leaderboard','leaderboard_entry_threshold')
    config_data['leaderboard_entry_threshold'] = [float(x) for x in config_data['leaderboard_entry_threshold'].split(' ')]
    config_data['leaderboard_name'] = config.get('Leaderboard','leaderboard_name')
    config_data['local_leader_board_file'] = config.get('Leaderboard','local_leader_board_file')

    config_data['use_private_split_after_competition'] = config.getboolean('Leaderboard','use_private_split_after_competition')
    config_data['checker_cmd_private_data'] = config.get('Leaderboard','checker_cmd_private_data')
    return config_data


def standartize_email(address):
    # remove '.' symbol and put to lower case
    return address.translate(address.maketrans("", "", ".")).lower()


def search_student_by_email(student_list, address):
    for student in student_list:
        for student_address in student['e-mails']:
            if standartize_email(student_address) == standartize_email(address):
                return student
    return None


def create_path(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


def parse_archive(archive, target_path, desired_files):
    read_files = []
    content = archive.namelist()
    for desired_file in desired_files:
        for file_name in content:
            # base_name = os.path.basename(file_name) does not work if the archive was created on Windows
            slash_index = file_name.rfind('/')
            backslash_index = file_name.rfind('\\')
            start_index = max( -1, slash_index, backslash_index ) + 1
            if start_index < len(file_name):
                base_name = file_name[ start_index: ]
            else:
                base_name = ''

            if base_name == desired_file and len(file_name) > 0 and not file_name[0] in ['.', '~']: # adding some security checks for archive containing files outside of them
                try:
                    test_file = archive.read(file_name)
                except:
                    test_file = None
                if test_file:
                    with open(os.path.join(target_path, os.path.basename(desired_file)), 'wb') as f:
                        f.write(test_file)
                        read_files.append(desired_file)
                    break
    return read_files


def extract_files_zip_archive(file_path, target_path, desired_files):
    try:
        read_files = []
        with  zipfile.ZipFile(file_path) as z:
            exit_code = z.testzip()

            if exit_code is not None:
                return None

            read_files = parse_archive(z, target_path, desired_files)

        return read_files
    except:
        return None


def extract_files_rar_archive(file_path, target_path, desired_files):
    try:
        if not RAR_INSTALLED:
            print('rarfile module is not installed: cannot unpack', file_path)
            return None

        read_files = []
        with  rarfile.RarFile(file_path) as rf:
            exit_code = rf.testrar()

            if exit_code is not None:
                return None

            read_files = parse_archive(rf, target_path, desired_files)

        return read_files
    except:
        return None


def extract_cc_info(cur_mail):
    emails_cc = []
    cc_message = ''
    if 'CCed' in cur_mail and cur_mail['CCed']:
        emails_cc = cur_mail['CCed']
        cc_message = robot_emails.cc_message%( ', '.join(emails_cc) )
    return emails_cc, cc_message


def react_email_unknown_sender(timestamp, cur_mail, config):
    print(timestamp, ':', 'Mail from unknown sender:', cur_mail['From'])

    emails_cc, cc_message = extract_cc_info(cur_mail)

    # reply the sender
    exit_message = gmail_communication.replyall_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         robot_emails.sender_unknown%(cur_mail['From'], cc_message, config['task_name']),
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path'] )
    if exit_message != 'OK':
        # error while sending the e-mail
        print(timestamp, ':', exit_message)
    # send message to the teacher
    exit_message = gmail_communication.forward_email_gmail(config['course_e_mail'], config['course_e_mail_password'], config['teacher_email'],
                                                         cur_mail,
                                                         forward_text=robot_emails.sender_unknown_teacher%(cur_mail['From'],config['task_name']),
                                                         failed_emails_path = config['failed_emails_path'] )
    if exit_message != 'OK':
        # error while sending the e-mail
        print(timestamp, ':', exit_message)


def save_attachements(timestamp, cur_mail, submit_path, test_files):
    submit_message = ''
    found_some_test_files = False
    for attachment in cur_mail['Attachments']:
        submit_message += 'Received file: '+attachment['file_name']+'\n'
        fp = open( os.path.join(submit_path, attachment['file_name']), 'wb')
        fp.write(attachment['file_content'])
        fp.close()

        is_archive = False

        for test_file in test_files:
            if attachment['file_name'] == test_file:
                found_some_test_files = True

        if len(attachment['file_name']) >= 4 and attachment['file_name'][-4:].lower() == '.zip':
            # found a ZIP archive, need to unpack
            print(timestamp, ':', 'Unpacking archive', attachment['file_name'])
            extracted_files = extract_files_zip_archive(os.path.join(submit_path,attachment['file_name']), submit_path, test_files)
            is_archive = True

        if RAR_INSTALLED and len(attachment['file_name']) >= 4 and attachment['file_name'][-4:].lower() == '.rar':
            # found a RAR archive, need to unpack
            print(timestamp, ':', 'Unpacking archive', attachment['file_name'])
            extracted_files = extract_files_rar_archive(os.path.join(submit_path,attachment['file_name']), submit_path, test_files)
            is_archive = True

        if is_archive:
            if extracted_files is None:
                submit_message += 'Could not unpack '+attachment['file_name']+'. Archive is corrupt!'+'\n'
            elif len(extracted_files) == 0:
                submit_message += 'Did not find any test files in '+attachment['file_name']+'\n'
            else:
                submit_message += 'Extracted '+', '.join(extracted_files)+' from '+attachment['file_name']+'\n'
                found_some_test_files = True

    return submit_message, found_some_test_files


def read_student_score_file(file_name, number_tests, use_leaderboard=False, add_private_leaderboard=False):
    student_score_data = []
    if not os.path.exists( file_name ):
        return student_score_data

    with open(file_name, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in reader:
            cur_student_score = {}
            cur_student_score['email'] = row[0]
            cur_student_score['time_stamp'] = row[1]
            cur_student_score['total_score'] = float(row[2])
            cur_student_score['late-penalty'] = float(row[3])

            position_offset = 4
            test_scores = []
            for i_task in range(number_tests):
                if row[i_task + position_offset] == 'None':
                    test_scores.append(None)
                else:
                    test_scores.append(float(row[i_task + position_offset]))
            cur_student_score['test_scores'] = test_scores
            student_score_data.append(cur_student_score)

            if use_leaderboard:
                test_scores_competition = []
                position_offset = 4 + number_tests
                for i_task in range(number_tests):
                    if row[i_task + position_offset] == 'None':
                        test_scores_competition.append(None)
                    else:
                        test_scores_competition.append(float(row[i_task + position_offset]))
                cur_student_score['test_scores_competition'] = test_scores_competition

            if add_private_leaderboard:
                test_scores_competition_private = []
                position_offset = 4 + 2 *number_tests
                for i_task in range(number_tests):
                    if row[i_task + position_offset] == 'None':
                        test_scores_competition_private.append(None)
                    else:
                        test_scores_competition_private.append(float(row[i_task + position_offset]))
                cur_student_score['test_scores_competition_private'] = test_scores_competition_private

    return student_score_data


def write_student_score_file(file_name, number_tests, student_score_data, use_leaderboard=False, add_private_leaderboard=False):
    with open(file_name, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for i_student in range(len(student_score_data)):
            cur_student_score = student_score_data[i_student]
            cur_list = [cur_student_score['email'], cur_student_score['time_stamp'], str(cur_student_score['total_score']), str(cur_student_score['late-penalty'])]
            for i_test in range(number_tests):
                cur_list.append(str(cur_student_score['test_scores'][i_test]))

            if use_leaderboard:
                for i_test in range(number_tests):
                    cur_list.append(str(cur_student_score['test_scores_competition'][i_test]))
            
            if add_private_leaderboard:
                for i_test in range(number_tests):
                    cur_list.append(str(cur_student_score['test_scores_competition_private'][i_test]))

            writer.writerow(cur_list)


def find_student_email(student_score_data, student):
    student_id = None
    for i_email in range(len(student_score_data)):
        email = student_score_data[i_email]['email']
        for i in range(len(student['e-mails'])):
            if standartize_email(student['e-mails'][i]) == standartize_email(email):
                student_id = i_email
    return student_id


def update_student_scores(config, student, new_score_data):
    student_score_data = read_student_score_file(config['student_score_file'], config['number_tests'],
                                                 use_leaderboard=config['use_leaderboard'],
                                                 add_private_leaderboard=config['use_private_split_after_competition'])
    student_id = find_student_email(student_score_data, student)
    if student_id is not None:
        student_score_data[student_id] = new_score_data
    else:
        student_score_data.append(new_score_data)
    write_student_score_file(config['student_score_file'], config['number_tests'], student_score_data,
                             use_leaderboard=config['use_leaderboard'],
                             add_private_leaderboard=config['use_private_split_after_competition'])

    if config['use_leaderboard']:
        leaderboard.update_leaderboard(config, student_score_data)


def get_previous_scores(config, student):
    student_score_data = read_student_score_file(config['student_score_file'], config['number_tests'])
    student_id = find_student_email(student_score_data, student)
    if student_id is not None:
        return student_score_data[student_id]['test_scores'], student_score_data[student_id]['total_score']
    else:
        return [None]*config['number_tests'], None


def get_delay_days(submission_time, deadline, deadline_hard=None):
    time_sub = timezone.convert_to_global_time(submission_time)
    time_deadline = timezone.convert_to_global_time(deadline)
    if deadline_hard:
        time_deadline_hard = timezone.convert_to_global_time(deadline_hard)
        hit_hard_deadline = time_sub <= time_deadline_hard
    else:
        hit_hard_deadline = True

    delay_seconds = (time_sub - time_deadline).total_seconds()
    if delay_seconds <= 0:
        return 0, hit_hard_deadline
    else:
        delay_days = int(math.ceil( delay_seconds / (3600 * 24.0) ))
        return delay_days, hit_hard_deadline


def get_delay_penalty(delay_days, config):
    late_penalty = delay_days * config['delay_day_penalty']
    late_penalty = min(late_penalty, config['delay_cap'])
    return late_penalty


def run_checker(command_line_checker):
    print(command_line_checker)
    p = subprocess.Popen(command_line_checker,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
    output, errors = p.communicate()
    # we assume that the score for this test file is given in the first line
    output = output.decode("utf-8")
    first_line_ends = output.find('\n')
    first_line_elements = output[0:first_line_ends].split(' ')
    score = float(first_line_elements[0])

    submit_message = output[first_line_ends+1:]

    return score, first_line_elements, submit_message


def check_solutions(config, submit_path, student, submission_time):
    submit_message = ''
    solution_score = 0
    old_test_scores, old_full_score = get_previous_scores(config, student)
    test_scores = [None]*config['number_tests']
    test_scores_competition = [None]*config['number_tests']
    test_scores_competition_private = [None]*config['number_tests']

    # get time stamps
    delay_days, hit_hard_deadline = get_delay_days(submission_time, config['deadline'], config['deadline_hard'])
    flag_competition_submission = config['use_leaderboard'] and delay_days <= 0

    # start testing
    for test_case in range(config['number_tests']):
        test_file = config['test_pattern']%(test_case+1)
        test_data_file = config['test_data_pattern']%(test_case+1)
        test_groundtruth_file = config['test_groundtruth_pattern']%(test_case+1)

        if len(submit_message) > 0:
            submit_message += '\n'
        submit_message += f"Checking {test_file:s}:\n"
        if os.path.exists(os.path.join(submit_path,test_file)):
            command_line_checker = config['checker_cmd']%(test_data_file, test_groundtruth_file, os.path.join(submit_path,test_file))
            score, first_line_elements, submit_message_checker = run_checker(command_line_checker)

            submit_message += submit_message_checker

            if old_test_scores[test_case] is not None:
                # there was some solution in the past
                if score > old_test_scores[test_case]:
                    submit_message += f"Your new score is {score:.2f} (instead of {old_test_scores[test_case]:.2f}).\n"
                elif score == old_test_scores[test_case]:
                    submit_message += f"Your score {score:.2f} is the same as your old score.\n"
                else:
                    submit_message += f"Your new score is {score:.2f}, but I am keeping your old score {old_test_scores[test_case]:.2f}.\n"
                    score = old_test_scores[test_case]
            else:
                submit_message += f"Your score is {score:.2f}.\n"

            if config['use_leaderboard']:
                assert len(first_line_elements) >= 2, "Need the checker to provide competition scores if using the leaderboard"
                score_competition = float(first_line_elements[1])
                if flag_competition_submission:
                    submit_message += f"Your score for the competition is {score_competition:.2f}. "
                    competition_threshold = config['leaderboard_entry_threshold'][test_case]
                    if score_competition >= competition_threshold and config['leaderboard_direction'].lower() == 'max' or \
                       score_competition <= competition_threshold and config['leaderboard_direction'].lower() == 'min':
                        submit_message += f"It reaches the entry threshold of {competition_threshold:.2f} and participates in the competition.\n"
                    else:
                        submit_message += f"It is too bad for the competition. Please, reach {competition_threshold} to participate.\n"

                    test_scores_competition[test_case] = score_competition

                    if config['use_private_split_after_competition']:
                        try:
                            command_line_checker_private = config['checker_cmd_private_data']%(test_data_file, test_groundtruth_file, os.path.join(submit_path,test_file))
                            score_private, first_line_elements_private, submit_message_checker_private = run_checker(command_line_checker_private)
                            score_competition_private = float(first_line_elements_private[1])
                        except Exception as e:
                            print(f"ERROR: checker chrashed when processing student file {os.path.join(submit_path,test_file)} on private data")
                            print(e)
                            score_competition_private = None
                            score_private = 0.0

                        if not score_competition_private:
                            print(f"ERROR: Some error when processing student file {os.path.join(submit_path,test_file)} on private data")
                        test_scores_competition_private[test_case] = score_competition_private

            test_scores[test_case] = score
            solution_score += score
        else:
            submit_message += f"File {test_file:s} not found in the submission.\n"
            
            if old_test_scores[test_case] is not None:
                # there was some solution in the past
                score = old_test_scores[test_case]
                submit_message += f"Your score {score:.2f} comes from before.\n"
                test_scores[test_case] = score
                solution_score += score
            else:
                submit_message += f"You've never submitted this test, so the score is zero.\n"

    if flag_competition_submission:
        if config['use_leaderboard']:
            submit_message += f"The current leaderboard is here: {config['leaderboard_link']}\n"

    # grade the solution
    submit_message += '\n'
    if delay_days >= 1:
        late_penalty = get_delay_penalty(delay_days, config)
        submit_message += f"You submitted this solution {delay_days:d} days after the deadline.\n"
    else:
        late_penalty = 0.0

    if hit_hard_deadline:
        if late_penalty > 0.0:
            submit_message += f"You are getting {late_penalty:.2f} penalty for that.\n"

        if not old_full_score is None and solution_score-late_penalty < old_full_score:
            # score is worse than the previous attempt
            submit_message += f"Your score {solution_score - late_penalty:.2f} is worse than you previous score. I am keeping your old score {old_full_score:.2f}.\n"
            full_score = old_full_score
        elif solution_score < config['acceptance_threshold']:
            submit_message += f"Your score {solution_score:.2f} is too low (below threshold {config['acceptance_threshold']:.2f})."
            submit_message += f" I can not accept your solution and assign you {config['score_non_accepted']:.2f} points for it.\n"
            full_score = config['score_non_accepted']
        else:
            full_score = solution_score - late_penalty
            full_score = max(full_score, config['min_score'])
            submit_message += f"I accept your solution and give you {full_score:.2f} points for it.\n"

        # tell students how much they can still get
        current_time = timezone.get_current_time_str()
        current_delay_days, _ = get_delay_days(current_time, config['deadline'])
        current_delay_penalty = get_delay_penalty(current_delay_days, config)
        max_possible_score = config['max_score']- current_delay_penalty
        if max_possible_score > full_score:
            submit_message += f"You can resubmit an improved solution to get {max_possible_score:.2f} points.\n"
    else:
        submit_message += f"You've missed the hard deadline {config['deadline_hard']}.\n"
        if not old_full_score is None:
            submit_message += f"I am keeping your old score {old_full_score:.2f}.\n"
            full_score = old_full_score
        else:
            submit_message += f"You have not submitted before, so, unfortunately, you get {config['score_non_accepted']:.2f}.\n"
            full_score = 0.0

    cur_student_score = {}
    cur_student_score['email'] = student['e-mails'][0]
    cur_student_score['time_stamp'] = submission_time
    cur_student_score['total_score'] = full_score
    cur_student_score['late-penalty'] = late_penalty
    cur_student_score['test_scores'] = test_scores
    cur_student_score['test_scores_competition'] = test_scores_competition
    cur_student_score['test_scores_competition_private'] = test_scores_competition_private

    return submit_message, cur_student_score


def react_email(timestamp, cur_mail, config, student):
    print(timestamp, ':', 'E-mail from', student['first_name'], student['last_name'])

    student_path = os.path.join(config['solutions_path'], student['last_name']+'_'+student['first_name'] );
    create_path(student_path)

    submit_index = 0
    submit_path = None
    while not submit_path or os.path.isdir( submit_path ):
        submit_index+=1
        submit_path = os.path.join(student_path, 'submit_%04d'%(submit_index))
    create_path(submit_path)

    emails_cc, cc_message = extract_cc_info(cur_mail)

    # preparations
    test_files = [config['test_pattern']%(i+1) for i in range(config['number_tests'])] # names of all test files
    no_file_str = ', '.join(test_files)
    no_file_str = f"the files {no_file_str} are" if len(test_files) > 1 else f"the file {no_file_str} is"
    no_test_files_message = f"Please, ensure that {no_file_str:s} attached in a ZIP archive (.zip file).\n"
    no_test_files_email = robot_emails.no_attachments%(student['first_name'], no_test_files_message, cc_message, config['task_name'])

    # save attachements
    if len(cur_mail['Attachments'])==0:
        exit_message = gmail_communication.reply_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         no_test_files_email,
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path'] )
        if exit_message != 'OK':
            # error while sending the e-mail
            print(timestamp, ':', exit_message)
    else:
        submit_message = ""
        extraction_message, found_some_test_files = save_attachements(timestamp, cur_mail, submit_path, test_files)
        submit_message += extraction_message + '\n'

        if found_some_test_files:
            solution_message, cur_student_score = check_solutions(config, submit_path, student, cur_mail['Time'])
            submit_message += solution_message
            update_student_scores(config, student, cur_student_score)
        else:
            submit_message += "Could not find any solution files in your e-mail.\n"
            submit_message += no_test_files_message

        # submit_message += cc_message

        exit_message = gmail_communication.reply_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         robot_emails.solution_graded%(student['first_name'],submit_message,config['task_name']),
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path']
                                                             )

        if exit_message != 'OK':
            # error while sending the e-mail
            print(timestamp, ':', exit_message)


def server_email_check(config_file):
    timestamp = timezone.get_current_time_str()

    config = read_config_file(config_file)
    student_list = read_student_list(config['student_list_file'])

    exit_message, emails = gmail_communication.receive_emails_gmail( config['course_e_mail'], config['course_e_mail_password'], config['gmail_label'] )
    if exit_message != 'OK':
        # error while checking the g-mail folder
        print(timestamp, ':', exit_message)
        return config['email_check_pause_minutes']

    if len(emails) == 0:
        # no e-mails received
        return config['email_check_pause_minutes']

    print(timestamp, ':', 'Received', len(emails), 'e-mails. Parsing...')
    for cur_mail in emails:
        print(timestamp, ':', 'Parsing e-mail from', cur_mail['From'], 'received at', cur_mail['Time'])
        # get sender name
        student = search_student_by_email(student_list, cur_mail['From'])
        if not student:
            react_email_unknown_sender(timestamp, cur_mail, config)
        else:
            react_email(timestamp, cur_mail, config, student)

    return config['email_check_pause_minutes']


def main():
    if len(sys.argv) == 2:
        config_file = sys.argv[1].strip()

        config = read_config_file(config_file)
        timezone.set_timezone(config["timezone"])

        print(f">>> Launched the checker at timezone {timezone.TIMEZONE}, Time: {timezone.get_current_time_str()}")
        print(f">>> Deadline is set to {timezone.convert_to_global_time(config['deadline'])}")
        if config['deadline_hard']:
            print(f">>> Hard deadline is set to {timezone.convert_to_global_time(config['deadline_hard'])}")

        if config['use_leaderboard']:
            assert leaderboard.LEADERBOARD_INSTALLED, "Requested the leaderboard, but API was not found"
            print(f">>> Creating the leaderboard in Google Spreadsheet")
            leaderboard.print_leaderboard(config)

        email_check_pause_minutes = server_email_check(config_file)
        while True:
            time.sleep(email_check_pause_minutes*60.0)
            email_check_pause_minutes = server_email_check(config_file)
    else:
        print('Expecting 1 command line argument: config file name')


if __name__ == '__main__':
    main()
