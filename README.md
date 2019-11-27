## Assignment submission system based on e-mails

Created by Anton Osokin.


### Description

This system is a very basic script (Python 3.7) that runs on a server machine (the only requirement is Internet connection), checks e-mails, downloads solutions, checks and grades the solutions. The system currently does not run the code provided by students, but only checks solutions on the tests submitted in the text files.
I used this system for assignments of the two types: get the unique correct answer and optimize a function as well as you can.

Main properties of the system:

1. An assignment consists of a fixed number of tests. The tests have to be provided to the students. The system only checks solutions to the provided tests.

2. Students submit their solutions to the course e-mail. Solutions to the tests of the assignment are attached as text files, ZIP, or RAR archives.

3. One instance of the system supports one assignment.

4. E-mail is the primary identifier of each student in the system. One student can have multiple e-mails, but only the first one is the primary identifier.

5. All students should be manually registered to the system (see `student_list.csv` file). If the system receives an e-mail from an unregistered e-mail it sends a message to the supervisor e-mail.

6. The score of the students are saved in a text file. I recommend to put this file under version control, not to loose scores. The file can be manually edited to make discounts for very important reasons students come up with.


### Installation

The goal of writing these scripts was to make something very simple with almost no dependencies. As a result, the only requirement is a Python 3.7 distribution (I used Anaconda) with almost no extra packages.

0. Setup the course e-mail on [GMAIL](https://gmail.com), create a special label for the task, create a filter that puts e-mails with a subject marker given to students under this label, allow [less secure apps to access your account](https://support.google.com/accounts/answer/6010255?hl=en) (I do not recommend doing this on your main e-mail), make IMAP available in the GMAIl settings.

1. Install [Anaconda](https://www.continuum.io/downloads) suitable for your system. Optional: if you want to parse RAR archives (students like them) install package `rarfile`.
  ```Shell
  conda create --name assignment_server python=3.7 chardet numpy pytz
  source activate assignment_server
  conda install -c anjos rarfile

  # for BLEU checker you need sacrebleu
  pip install sacrebleu==1.4.2

  # for leaderboard in Google Spreadsheet (from here: https://developers.google.com/sheets/api/quickstart/python)
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
  ```

2. Get the scripts:  
  ```Shell
  git clone https://github.com/aosokin/assignment_checker_email.git
  cd assignment_checker
  ```

3. Create the configuration file `task.cfg`.

4. Run the system:
  ```Shell
  python assignment_checker.py task.cfg
  ```

### Configuration files

The main configuration file contains all information about the assignment. See the `task.cfg` for an example. Lines starting with `#` contain comments.

```
[General]
# e-mail for the course
course_e_mail=course.email@gmail.com
# password to access gmail
course_e_mail_password=course.email.password
# file with the list of all students, created manually, can be shared among multiple tasks, see student_list.csv for an example
student_list_file=student_list.csv
# file to store grades, created automatically, one per each task
student_score_file=taskX_scores.csv
# e-mail where to write in case of unregistered students and some problems
teacher_email=teacher@gmail.com
# delay between the two e-mail checks, not to overload the connection
email_check_pause_minutes=10
[Assignment]
# gmail label to store the e-mails parsed by the system
gmail_label=TaskX 
# name of the task used in communication with students
task_name=Task X 
# path to store student solutions, contains everything students send
solutions_path=./taskX_student_solutions
# number of tests for the assignment
number_tests=5
#pattern for the names of the test solutions, %%d - the index of a test (1-based)
test_pattern=task_test%%d_solution.txt
# command to launch the checker; has to contain %%s three times for the three file names: test data file, teacher-provided answer, student answer; not all the three files have to be actually read
checker_cmd=python ./checker_exact_match.py "%%s" "%%s" "%%s"
# pattern for files containing test data
test_data_pattern=./data/taskX_test%%d.txt
# pattern for files containing teacher-provided answer
test_groundtruth_pattern=./data/taskX_test%%d_solution.txt
# folder to store e-mails, if sending failed (just in case)
failed_emails_path=taskX_unsent_emails
# the assignment deadline: Year-Mon-Date-Hours:Min:Sec
deadline=2016-05-13-23:59:59
# grade penalty for each day of delay after the deadline
delay_day_penalty=0.1
# maximum allowed delay penalty
delay_cap=5.0
# score threshold to accept the assignment
acceptance_threshold=1.0
# score for non-accepted solution
score_non_accepted=-5.0
# maximum score per all the tests, used in communication with students, should be sum of the scores for all the tests
max_score=5.0
```

Format for `student_list_file`(each line corresponds to one student, each student can have multiple e-mails, the first e-mail is the primary identifier): 
```
student_last_name,student_first_name,student.main.email@gmail.com,student.email2@gmail.com,student.email3@gmail.com,...
```

Format for `student_score_file` (each line corresponds to one student, number of tests can vary): 
```
student.email@gmail.com,timestamp,full_score,delay_penalty,test1_score,test2_score,test3_score,test4_score,test5_score,test6_score,...
```

### Assignment checkers

A critical component the the system is a checker to actually check solutions submitted by students.
I've used the system for the assignments of two types: correct answer is exact and unique, a task is an optimization problem and a solution is graded based on the achieved objective (and feasibility, of course).

1. For the exact match tasks, script `checker_exact_match.py` should do fine. The test data file can replaced by a placeholder. the only internal parameter `COMPARISON_ACCURACY` sets the comparison accuracy.

2. For the optimization tasks, you'll need to code a bit. In particular, you'll need to implement the computation of the function value. As examples, see script `checker_optimization_knapsack.py` for a task on the knapsack problem and `checker_optimization_tsp.py` for a task on TSP.


### License

The code is released under the MIT License (refer to the LICENSE file for details), so use in any way you like at your own risk.
