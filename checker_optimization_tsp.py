
import sys
import numpy as np
import os
import math
import chardet
import io

COMPARISON_ACCURACY = 1e-2
MAX_SCORE = 1.0
HALF_SCORE = 0.5
SUBMISSION_SCORE = 0.0

MESSAGES_SCORE = {}
MESSAGES_SCORE[SUBMISSION_SCORE] = lambda value, value_to_get : \
    'Your submission output is good, but the solution objective value %.2f is insufficient for full credit. For a higher grade, you will need to improve the objective value to %.2f or better.'%(value, value_to_get)
MESSAGES_SCORE[HALF_SCORE] = lambda value, value_to_get : \
    'Good Optimization. Your algorithm does some basic optimization but your solution objective value %.2f can be improved significantly. For a higher grade, you will need to improve the objective value to %.2f or better.'%(value, value_to_get)
MESSAGES_SCORE[MAX_SCORE] = lambda value, value_to_get : \
    'Awesome Optimization! Your objective value %.2f is great and you get a full score.'%(value)

VALUE_TESTS = {}
# value for half mark, for the full mark, optimal value (can replaced with a place-holder)
VALUE_TESTS['task3_test1.txt'.lower()] = [482,430,428.871756]
VALUE_TESTS['task3_test2.txt'.lower()] = [23433,20800,20750.762504]
VALUE_TESTS['task3_test3.txt'.lower()] = [35985,30000,29440.412221]
VALUE_TESTS['task3_test4.txt'.lower()] = [40000,37600,36934]
VALUE_TESTS['task3_test5.txt'.lower()] = [378069,323000,316527]
VALUE_TESTS['task3_test6.txt'.lower()] = [78478868,67700000,66050619.79]

# the default weight for all the tests is 1.0
TEST_WEIGHT = {}
TEST_WEIGHT['task3_test6.txt'.lower()] = 2.0

MODE = 'min' # 'min' or 'max'


def are_equal_floats(tested, correct):
    return abs(tested - correct) <= COMPARISON_ACCURACY


def asign_score(value, test_name):
    score = None
    value_to_improve = None

    if test_name.lower() in VALUE_TESTS:
        test_data = VALUE_TESTS[test_name.lower()]
        score = SUBMISSION_SCORE
        value_to_improve = test_data[0]
        if MODE == 'max':
            if value >= test_data[0]:
                score = HALF_SCORE
                value_to_improve = test_data[1]
            if value >= test_data[1]:
                score = MAX_SCORE
                value_to_improve = None
        else:
            if value <= test_data[0]:
                score = HALF_SCORE
                value_to_improve = test_data[1]
            if value <= test_data[1]:
                score = MAX_SCORE
                value_to_improve = None

    return score, value_to_improve


def decode_lines(data_file):
    # detect encoding
    with open(data_file, 'rb') as file:
        raw = file.read(1024) # at most 1024 bytes are returned
        charenc = chardet.detect(raw)['encoding']

    input_data = []
    with io.open(data_file,'r', encoding=charenc) as file:
        for line in file:
            line = line.encode("ascii", "ignore")
            input_data.append(line)

    return input_data


def read_numbers(data_file):
    input_data = decode_lines(data_file)

    numbers = np.array([])
    for i_line in xrange(len(input_data)):
        entries = input_data[i_line].split()
        entries = filter(None, entries) # remove empty entries
        line_numbers = [ float(x) if x.lower != "inf" else float("inf") for x in entries ]
        numbers = np.append(numbers, line_numbers)
    return numbers


def read_data(data_file):
    numbers = read_numbers(data_file)
    cur_entry = 0

    # number of points
    num_points = int(numbers[cur_entry])
    cur_entry += 1

    # get data on the points
    points = np.zeros((num_points, 2))
    for i_point in xrange(num_points):
        points[i_point, 0] = float(numbers[cur_entry])
        cur_entry += 1
        points[i_point, 1] = float(numbers[cur_entry])
        cur_entry += 1

    return points


def dist(A, B):
    return math.sqrt( (A[0] - B[0]) * (A[0] - B[0]) + (A[1] - B[1]) * (A[1] - B[1]) )


def check_tsp_solution( solution, points ):
    num_points = points.shape[0]
    visited_nodes = np.zeros(num_points, dtype=bool)
    path_length = dist( points[solution[0]], points[solution[-1]] )
    visited_nodes[solution[-1]] = True
    for i_point in xrange(num_points-1):
        visited_nodes[solution[i_point]] = True
        path_length += dist( points[solution[i_point]], points[solution[i_point+1]] )

    is_valid_solution = not (False in visited_nodes)
    return is_valid_solution, path_length


def check_feasibility( submitted_solution, points ):
    n = points.shape[0]
    submitted_value = submitted_solution[0]
    message = ''

    for i_point in range(n):
        cur_item = submitted_solution[i_point + 1]
        if not are_equal_floats(cur_item, round(cur_item)) or round(cur_item) < 0 or round(cur_item) > n-1:
            message += 'Value %f corresponding to item %d is not valid.'%(cur_item, i_item)
            message += ' Expecting integer between 0 and %d.\n'%(n-1)
            return None, message

    is_valid_solution, computed_value = check_tsp_solution(  submitted_solution[1:], points )
    if not is_valid_solution:
        message += 'The submitted solution is not a valid TSP path.'
        return None, message

    if not are_equal_floats(computed_value, submitted_value):
        message += 'The value of the solution is computed incorrectly: %d instead of %d.'%(submitted_value, computed_value)
        message += ' Using correct value %d.\n'%(computed_value)
    else:
        message += 'The produced configuration is feasible and the objective value is correct.\n'

    return computed_value, message



if __name__ == '__main__':
    if len(sys.argv) == 4:
        test_file = sys.argv[1].strip()
        correct_file = sys.argv[2].strip()
        tested_file = sys.argv[3].strip()

        try:
            tested_numbers = read_numbers(tested_file)
        except:
            print 0.0
            print 'Failed to read file', os.path.basename(tested_file)
            sys.exit(0)

        correct_numbers = read_numbers(correct_file)
        points = read_data(test_file)

        if len(tested_numbers) != len(correct_numbers):
            print 0.0
            print 'Infeasible answer'
            print 'Wrong number of entries in file %s'%(os.path.basename(tested_file)), '(%d instead of %d).'%(len(tested_numbers), len(correct_numbers))
        else:
            is_correct = True
            submitted_value, feasibility_message = check_feasibility( tested_numbers, points )
            if submitted_value is None:
                print 0.0
                print feasibility_message,
            else:
                test_name = os.path.basename(test_file)
                score, value_to_improve = asign_score(submitted_value, test_name)
                if score is not None:
                    if test_name.lower() in TEST_WEIGHT:
                        print score * TEST_WEIGHT[test_name.lower()]
                    else:
                        print score
                    print feasibility_message,
                    print MESSAGES_SCORE[score](submitted_value, value_to_improve)
                else:
                    print 0.0
                    print 'Could not grade your solution for unknown reason. Please, contact the instructors to resolve this issue.'
    else:
        print 'Expecting 3 command line arguments: test_file, correct_answer, tested_answer'