
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
    'Awesome Optimization! Your objective value %.2f is great and you get the full score.'%(value)

VALUE_TESTS = {}
# value for half mark, for the full mark, optimal value (can replaced with a place-holder)
VALUE_TESTS['knapsack_test1.txt'.lower()] = [92000,99798,99798]
VALUE_TESTS['knapsack_test2.txt'.lower()] = [100062,100236,100236]
VALUE_TESTS['knapsack_test3.txt'.lower()] = [3966813,3967028,3967180]
VALUE_TESTS['knapsack_test4.txt'.lower()] = [109869,109899,109899]
VALUE_TESTS['knapsack_test5.txt'.lower()] = [1099870,1099881,1099893]


# the default weight for all the tests is 1.0
TEST_WEIGHT = {}


MODE = 'max' # 'min' or 'max'


def are_equal_floats(tested, correct):
    return abs(tested - correct) <= COMPARISON_ACCURACY


def assign_score(value, test_name):
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
    for i_line in range(len(input_data)):
        entries = input_data[i_line].split()
        entries = filter(None, entries) # remove empty entries
        line_numbers = [ float(x) if x.lower != "inf" else float("inf") for x in entries ]
        numbers = np.append(numbers, line_numbers)
    return numbers


def read_data(data_file):
    numbers = read_numbers(data_file)
    cur_entry = 0

    # number of nodes
    num_items = int(numbers[cur_entry])
    cur_entry += 1
    
    # maximum capacity of the knapsack
    capacity = float(numbers[cur_entry])
    cur_entry += 1
    
    # get data on the items
    value = np.zeros(num_items, dtype = 'float')
    size = np.zeros(num_items, dtype = 'float')
    for i_item in range(num_items):
        value[i_item] = float(numbers[cur_entry])
        cur_entry += 1
        size[i_item] = float(numbers[cur_entry])
        cur_entry += 1
        
    return value, size, capacity


def check_feasibility( submitted_solution, value, size, capacity ):
    n = len(value)
    submitted_value = submitted_solution[0]
    computed_size = 0
    computed_value = 0
    message = ''
    for i_item in range(n):
        cur_item = submitted_solution[i_item + 1]
        if are_equal_floats(cur_item, 1):
            computed_value += value[i_item]
            computed_size += size[i_item]
        elif not are_equal_floats(cur_item, 0):
            message += 'Value %f corresponding to item %d is not valid.'%(cur_item, i_item)
            message += ' Expecting 0 or 1.\n'
            return None, message

    if not are_equal_floats(computed_value, submitted_value):
        message += 'The value of the solution is computed incorrectly: %d instead of %d.'%(submitted_value, computed_value)
        message += ' Using correct value %d.\n'%(computed_value)
    else:
        message += 'The produced configuration is feasible and the objective value is correct.\n'

    if computed_size > capacity:
        message += 'The submitted solution is not feasible: size %d exceeds capacity %d.\n'%(computed_size, capacity)
        return None, message
    return computed_value, message



if __name__ == '__main__':
    if len(sys.argv) == 4:
        test_file = sys.argv[1].strip()
        correct_file = sys.argv[2].strip()
        tested_file = sys.argv[3].strip()

        try:
            tested_numbers = read_numbers(tested_file)
        except:
            print(0.0)
            print('Failed to read file', os.path.basename(tested_file))
            sys.exit(0)

        correct_numbers = read_numbers(correct_file)
        value, size, capacity = read_data(test_file)

        if len(tested_numbers) != len(correct_numbers):
            print(0.0)
            print('Infeasible answer')
            print('Wrong number of entries in file %s'%(os.path.basename(tested_file)), '(%d instead of %d).'%(len(tested_numbers), len(correct_numbers)))
        else:
            is_correct = True
            submitted_value, feasibility_message = check_feasibility( tested_numbers, value, size, capacity )
            if submitted_value is None:
                print(0.0)
                print(feasibility_message, end='')
            else:
                test_name = os.path.basename(test_file)
                score, value_to_improve = assign_score(submitted_value, test_name)
                print(score, value_to_improve)
                if score is not None:
                    if test_name.lower() in TEST_WEIGHT:
                        print(score * TEST_WEIGHT[test_name.lower()])
                    else:
                        print(score)
                    print(feasibility_message, end='')
                    print(MESSAGES_SCORE[score](submitted_value, value_to_improve))
                else:
                    print(0.0)
                    print('Could not grade your solution for unknown reason. Please, contact the instructors to resolve this issue.')
    else:
        print('Expecting 3 command line arguments: test_file, correct_answer, tested_answer')
