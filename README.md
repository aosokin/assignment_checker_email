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

The main configuration file contains all information about the assignment. See the `task.cfg` for an example of an optimization task and `task_bleu_checker.cfg` for an example of using BLEU, public/private data and leaderboard.

Format for `student_list_file`(each line corresponds to one student, each student can have multiple e-mails, the first e-mail is the primary identifier): 
```
student_last_name,student_first_name,Student,student.main.email@gmail.com,student.email2@gmail.com,student.email3@gmail.com,...
```

Format for `student_score_file` (each line corresponds to one student, number of tests can vary): 
```
student.email@gmail.com,timestamp,full_score,delay_penalty,test1_score,test2_score,test3_score,test4_score,test5_score,test6_score,...
```
If using the leaderboard:
```
student.email@gmail.com,timestamp,full_score,delay_penalty,test1_score,test2_score,...,test1_leaderboard_score,test2_leaderboard_score,...
```
If using public/private data on top:
```
student.email@gmail.com,timestamp,full_score,delay_penalty,test1_score,test2_score,...,test1_leaderboard_public_score,test2_leaderboard_public_score,...,test1_leaderboard_private_score,test2_leaderboard_private_score,...
```

### Assignment checkers

A critical component the the system is a checker to actually check solutions submitted by students.
I've used the system for the assignments of two types: correct answer is exact and unique, a task is an optimization problem and a solution is graded based on the achieved objective (and feasibility, of course).

1. For the exact match tasks, script `checker_exact_match.py` should do fine. The test data file can replaced by a placeholder. the only internal parameter `COMPARISON_ACCURACY` sets the comparison accuracy.

2. For the optimization tasks, you'll need to code a bit. In particular, you'll need to implement the computation of the function value. As examples, see script `checker_optimization_knapsack.py` for a task on the knapsack problem and `checker_optimization_tsp.py` for a task on TSP.

3. For measuring BLEU, please check out `checker_bleu.sh`. If you want to use public/private data splits, please see `task_bleu_checker.cfg` for examples of how to set this up.

### License

The code is released under the MIT License (refer to the LICENSE file for details), so use in any way you like at your own risk.
