
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
VALUE_TESTS['gc_test1.txt'.lower()] = [8,6,6]
VALUE_TESTS['gc_test2.txt'.lower()] = [20,17,17]
VALUE_TESTS['gc_test3.txt'.lower()] = [21,16,None]
VALUE_TESTS['gc_test4.txt'.lower()] = [95,78,None]
VALUE_TESTS['gc_test5.txt'.lower()] = [18,16,None]
VALUE_TESTS['gc_test6.txt'.lower()] = [124,100,None]

# the default weight for all the tests is 1.0
TEST_WEIGHT = {}
TEST_WEIGHT['gc_test6.txt'.lower()] = 2.0

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

    num_read = 0
    numbers = np.zeros(1000, dtype=int)
    for i_line in range(len(input_data)):
        entries = input_data[i_line].split()
        entries = filter(None, entries) # remove empty entries
        line_numbers = [ int(float(x) + 0.5) if x.lower != "inf" else float("inf") for x in entries ]
        line_numbers = np.array(line_numbers, dtype=numbers.dtype)
        
        if num_read + line_numbers.size > numbers.size:
            # double the size of the buffer each time it is not enough
            extra = numbers * 0
            if numbers.size + extra.size < line_numbers.size + num_read:
                extra = np.zeros(line_numbers.size + num_read - numbers.size, dtype=numbers.dtype)
            numbers = np.append(numbers, extra)

        numbers[num_read : num_read + line_numbers.size] = line_numbers
        num_read += line_numbers.size

    return numbers[:num_read]


def read_data(data_file):
    numbers = read_numbers(data_file)
    cur_entry = 0

    # number of solution_data
    num_nodes = int(numbers[cur_entry])
    cur_entry += 1
    num_edges = int(numbers[cur_entry])
    cur_entry += 1

    # get data on the solution_data
    edges = np.zeros((num_edges, 2), dtype=int)
    for i_edge in range(num_edges):
        edges[i_edge, 0] = int(numbers[cur_entry] + 0.5)
        cur_entry += 1
        edges[i_edge, 1] = int(numbers[cur_entry] + 0.5)
        cur_entry += 1

    return num_nodes, num_edges, edges


def check_gc_solution( coloring, edges ):
    used_colors = {}
    num_colors = 0

    for color in coloring:
        if color not in used_colors:
            used_colors[color] = 1
            num_colors += 1

    message = ''
    is_valid_solution = True
    for i_node, j_node in edges:
        if coloring[i_node] == coloring[j_node]:
            is_valid_solution = False
            message += 'Vertices of the edge (%d, %d) are colored into %d\n'%(i_node, j_node, coloring[i_node])
    
    return is_valid_solution, num_colors, message


def check_feasibility( submitted_solution, num_nodes, num_edges, edges ):
    num_colors_submitted = submitted_solution[0]
    message = ''

    coloring = submitted_solution[1:]
    n = coloring.shape[0]
    if n != num_nodes:
        message += 'The submitted coloring has wrong number of nodes: %d instead of %d.'%(n, num_nodes)
        return None, message

    for i_node in range(n):
        cur_item = coloring[i_node]
        if not are_equal_floats(cur_item, round(cur_item)) or round(cur_item) < 0 or round(cur_item) > num_colors_submitted:
            message += 'Value %f corresponding to node %d is not valid.'%(cur_item, i_node)
            message += ' Expecting integer between 0 and the number of colors - 1 = %d.\n'%(num_colors_submitted - 1)
            return None, message

    is_valid_solution, computed_value, test_message = check_gc_solution( coloring, edges )
    if not is_valid_solution:
        message += 'The submitted solution is not a valid GC configuration:\n' + test_message
        return None, message

    if not are_equal_floats(computed_value, num_colors_submitted):
        message += 'The value of the solution is computed incorrectly: %d instead of %d.'%(num_colors_submitted, computed_value)
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
            print(0.0)
            print('Failed to read file', os.path.basename(tested_file))
            sys.exit(0)

        correct_numbers = read_numbers(correct_file)
        num_nodes, num_edges, edges = read_data(test_file)

        if len(tested_numbers) != len(correct_numbers):
            print(0.0)
            print('Infeasible answer')
            print('Wrong number of entries in file %s'%(os.path.basename(tested_file)), '(%d instead of %d).'%(len(tested_numbers), len(correct_numbers)))
        else:
            is_correct = True
            submitted_value, feasibility_message = check_feasibility( tested_numbers, num_nodes, num_edges, edges )
            if submitted_value is None:
                print(0.0)
                print(feasibility_message, end='')
            else:
                test_name = os.path.basename(test_file)
                score, value_to_improve = asign_score(submitted_value, test_name)
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
