import csv
import ConfigParser
import datetime
import os, sys
import zipfile
import subprocess
from copy import deepcopy
import datetime
import math
import time

try:
    import rarfile
    RAR_INSTALLED = True
except:
    RAR_INSTALLED = False

import gmail_communication
import robot_emails

def read_student_list(file_name):
    students = []
    with open(file_name, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in reader:
            cur_student = {}
            cur_student['last_name'] = row[0]
            cur_student['first_name'] = row[1]
            cur_student['e-mails'] = row[2:]
            students.append(cur_student)
    return students


def read_config_file(config_file):
    config = ConfigParser.ConfigParser()
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
    config_data['delay_day_penalty'] = config.getfloat('Assignment','delay_day_penalty')
    config_data['delay_cap'] = config.getfloat('Assignment','delay_cap')
    config_data['max_score'] = config.getfloat('Assignment','max_score')
    config_data['acceptance_threshold'] = config.getfloat('Assignment','acceptance_threshold')
    config_data['score_non_accepted'] = config.getfloat('Assignment','score_non_accepted')
    config_data['failed_emails_path'] = config.get('Assignment','failed_emails_path')
    return config_data


def standartize_email(address):
    # remove '.' symbol and put to lower case
    return address.translate(None, '.').lower()


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
            print 'rarfile module is not installed: cannot unpack', file_path
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
    print timestamp, ':', 'Mail from unknown sender:', cur_mail['From']

    emails_cc, cc_message = extract_cc_info(cur_mail)

    # reply the sender
    exit_message = gmail_communication.replyall_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         robot_emails.sender_unknown%(cur_mail['From'], cc_message, config['task_name']),
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path'] )
    if exit_message != 'OK':
        # error while sending the e-mail
        print timestamp, ':', exit_message
    # send message to the teacher
    exit_message = gmail_communication.forward_email_gmail(config['course_e_mail'], config['course_e_mail_password'], config['teacher_email'],
                                                         cur_mail,
                                                         forward_text=robot_emails.sender_unknown_teacher%(cur_mail['From'],config['task_name']),
                                                         failed_emails_path = config['failed_emails_path'] )
    if exit_message != 'OK':
        # error while sending the e-mail
        print timestamp, ':', exit_message


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
            print timestamp, ':', 'Unpacking archive', attachment['file_name']
            extracted_files = extract_files_zip_archive(os.path.join(submit_path,attachment['file_name']), submit_path, test_files)
            is_archive = True

        if RAR_INSTALLED and len(attachment['file_name']) >= 4 and attachment['file_name'][-4:].lower() == '.rar':
            # found a RAR archive, need to unpack
            print timestamp, ':', 'Unpacking archive', attachment['file_name']
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


def read_student_score_file(file_name, number_tests):
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
            test_scores = []
            for i_task in xrange(number_tests):
                if row[i_task+4] == 'None':
                    test_scores.append(None)
                else:
                    test_scores.append(float(row[i_task+4]))
            cur_student_score['test_scores'] = test_scores
            student_score_data.append(cur_student_score)
    return student_score_data


def write_student_score_file(file_name, number_tests, student_score_data):
    with open(file_name, 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for i_student in xrange(len(student_score_data)):
            cur_student_score = student_score_data[i_student]
            cur_list = [cur_student_score['email'], cur_student_score['time_stamp'], str(cur_student_score['total_score']), str(cur_student_score['late-penalty'])]
            for i_test in xrange(number_tests):
                cur_list.append(str(cur_student_score['test_scores'][i_test]))
            writer.writerow(cur_list)


def find_student_email(student_score_data, student):
    student_id = None
    for i_email in xrange(len(student_score_data)):
        email = student_score_data[i_email]['email']
        for i in xrange(len(student['e-mails'])):
            if standartize_email(student['e-mails'][i]) == standartize_email(email):
                student_id = i_email
    return student_id


def update_student_scores(config, student, new_score_data):
    student_score_data = read_student_score_file(config['student_score_file'], config['number_tests'])
    student_id = find_student_email(student_score_data, student)
    if not student_id is None:
        student_score_data[student_id] = new_score_data
    else:
        student_score_data.append(new_score_data)
    write_student_score_file(config['student_score_file'], config['number_tests'], student_score_data)


def get_previous_scores(config, student):
    student_score_data = read_student_score_file(config['student_score_file'], config['number_tests'])
    student_id = find_student_email(student_score_data, student)
    if student_id is not None:
        return student_score_data[student_id]['test_scores'], student_score_data[student_id]['total_score']
    else:
        return [None]*config['number_tests'], None


def get_delay_days(submission_time, deadline):
    time_sub = datetime.datetime.strptime(submission_time, gmail_communication.time_format)
    time_deadline = datetime.datetime.strptime(deadline, gmail_communication.time_format)
    delay_seconds = (time_sub - time_deadline).total_seconds()
    if delay_seconds <= 0:
        return 0
    else:
        delay_days = int(math.ceil( delay_seconds / (3600 * 24.0) ))
        return delay_days


def get_delay_penalty(delay_days, config):
    late_penalty = delay_days * config['delay_day_penalty']
    late_penalty = min(late_penalty, config['delay_cap'])
    return late_penalty


def check_solutions(config, submit_path, student, submission_time):
    submit_message = ''
    solution_score = 0
    old_test_scores, old_full_score = get_previous_scores(config, student)
    test_scores = [None]*config['number_tests']
    # start testing
    for test_case in xrange(config['number_tests']):
        test_file = config['test_pattern']%(test_case+1)
        test_data_file = config['test_data_pattern']%(test_case+1)
        test_groundtruth_file = config['test_groundtruth_pattern']%(test_case+1)

        if len(submit_message) > 0:
            submit_message += '\n'
        submit_message += 'Checking '+test_file+':\n'
        if os.path.exists(os.path.join(submit_path,test_file)):
            command_line_checker = config['checker_cmd']%(test_data_file, test_groundtruth_file, os.path.join(submit_path,test_file))
            p = subprocess.Popen(command_line_checker,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
            output, errors = p.communicate()
            # we assume that the score for this test file is given in the first line
            first_line_ends = output.find('\n')
            first_line_elements = output[0:first_line_ends].split(' ')
            score = float(first_line_elements[0])
            submit_message += output[first_line_ends+1:]

            if not old_test_scores[test_case] is None:
                # there was some solution in the past
                if score > old_test_scores[test_case]:
                    submit_message += 'Your new score is '+str(score)+' (instead of '+str(old_test_scores[test_case])+')\n'
                elif score == old_test_scores[test_case]:
                    submit_message += 'Your score '+str(score)+' is the same as your old score'+'\n'
                else:
                    submit_message += 'Your new score is '+str(score)+', but I am keeping your old score '+str(old_test_scores[test_case])+'\n'
                    score = old_test_scores[test_case]
            else:
                submit_message += 'Your score is '+str(score)+'\n'

            test_scores[test_case] = score
            solution_score += score
        else:
            submit_message += 'File ' + test_file + ' not found in the submission\n'

    # grade the solution
    delay_days = get_delay_days(submission_time, config['deadline'])
    if delay_days >= 1:
        late_penalty = get_delay_penalty(delay_days, config)
        submit_message += '\n' + 'You submitted this solution '+str(delay_days)+' days after the deadline. You are getting '+str(late_penalty)+' penalty for that.'+'\n'
    else:
        late_penalty = 0

    if not old_full_score is None and solution_score-late_penalty < old_full_score:
        # score is worse than the previous attempt
        submit_message += '\n' + 'Your score '+str(solution_score)+' is worse than you previous score. I am keeping your old score '+str(old_full_score)+'.'+'\n'
        full_score = old_full_score
    elif solution_score < config['acceptance_threshold']:
        submit_message += '\n' + 'Your score '+str(solution_score)+' is too low (below threshold '+str(config['acceptance_threshold'])+').'
        submit_message += ' I can not accept your solution and assign you '+str(config['score_non_accepted'])+' points for it.'
        full_score = config['score_non_accepted']
    else:
        full_score = solution_score-late_penalty
        submit_message += '\n' + 'I accept your solution and give you '+str(full_score)+' points for it.'+'\n'

    # tell students how much they can still get
    current_time = datetime.datetime.now().strftime( gmail_communication.time_format )
    current_delay_days = get_delay_days(current_time, config['deadline'])
    current_delay_penalty = get_delay_penalty(current_delay_days, config)
    max_possible_score = config['max_score']- current_delay_penalty
    if max_possible_score > full_score:
        submit_message += '\n' + 'You can resubmit an improved solution to get '+str(max_possible_score)+' points.'+'\n'

    cur_student_score = {}
    cur_student_score['email'] = student['e-mails'][0]
    cur_student_score['time_stamp'] = submission_time
    cur_student_score['total_score'] = full_score
    cur_student_score['late-penalty'] = late_penalty
    cur_student_score['test_scores'] = test_scores

    return submit_message, cur_student_score


def react_email(timestamp, cur_mail, config, student):
    print timestamp, ':', 'E-mail from ', student['first_name'], student['last_name']

    student_path = os.path.join(config['solutions_path'], student['last_name']+'_'+student['first_name'] );
    create_path(student_path)

    submit_index = 0
    submit_path = None
    while not submit_path or os.path.isdir( submit_path ):
        submit_index+=1
        submit_path = os.path.join(student_path, 'submit_%04d'%(submit_index))
    create_path(submit_path)

    emails_cc, cc_message = extract_cc_info(cur_mail)

    # save attachements
    if len(cur_mail['Attachments'])==0:
        exit_message = gmail_communication.reply_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         robot_emails.no_attachments%(student['first_name'], cc_message, config['task_name']),
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path'] )
        if exit_message != 'OK':
            # error while sending the e-mail
            print timestamp, ':', exit_message
    else:
        submit_message = ''
        test_files = [config['test_pattern']%(i+1) for i in range(config['number_tests'])] # names of all test files
        extraction_message, found_some_test_files = save_attachements(timestamp, cur_mail, submit_path, test_files)
        submit_message += extraction_message + '\n'

        if found_some_test_files:
            solution_message, cur_student_score = check_solutions(config, submit_path, student, cur_mail['Time'])
            submit_message += solution_message
            update_student_scores(config, student, cur_student_score)
        else:
            submit_message += 'I could not find any test files in your solution. Please, ensure that files ' + ', '.join(test_files) + ' are attached in ZIP archive (.zip file).' + '\n'

        submit_message += cc_message

        exit_message = gmail_communication.reply_email_gmail(config['course_e_mail'], config['course_e_mail_password'],
                                                         cur_mail,
                                                         robot_emails.solution_graded%(student['first_name'],submit_message,config['task_name']),
                                                         emails_cc = emails_cc,
                                                         failed_emails_path = config['failed_emails_path']
                                                             )

        if exit_message != 'OK':
            # error while sending the e-mail
            print timestamp, ':', exit_message


def server_email_check(config_file):
    timestamp = datetime.datetime.now().strftime( gmail_communication.time_format )

    config = read_config_file(config_file)
    student_list = read_student_list(config['student_list_file'])

    exit_message, emails = gmail_communication.receive_emails_gmail( config['course_e_mail'], config['course_e_mail_password'], config['gmail_label'] )
    if exit_message != 'OK':
        # error while checking the g-mail folder
        print timestamp, ':', exit_message
        return config['email_check_pause_minutes']

    if len(emails) == 0:
        # no e-mails received
        return config['email_check_pause_minutes']

    print timestamp, ':', 'Received', len(emails), 'e-mails. Parsing...'
    for cur_mail in emails:
        print timestamp, ':', 'Parsing e-mail from', cur_mail['From'], 'received at', cur_mail['Time']
        # get sender name
        student = search_student_by_email(student_list, cur_mail['From'])
        if not student:
            react_email_unknown_sender(timestamp, cur_mail, config)
        else:
            react_email(timestamp, cur_mail, config, student)

    return config['email_check_pause_minutes']


if __name__ == '__main__':
    if len(sys.argv) == 2:
        config_file = sys.argv[1].strip()

        email_check_pause_minutes = server_email_check(config_file)
        while True:
            time.sleep(email_check_pause_minutes*60.0)
            email_check_pause_minutes = server_email_check(config_file)
    else:
        print 'Expecting 1 command line argument: config fiel name'
