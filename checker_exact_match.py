
import sys
import numpy as np
import os
import chardet
import io

COMPARISON_ACCURACY = 1e-2

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


if __name__ == '__main__':
    if len(sys.argv) == 4:
        test_file = sys.argv[1].strip()
        correct_file = sys.argv[2].strip()
        tested_file = sys.argv[3].strip()

        correct_numbers = read_numbers(correct_file)
        try:
            tested_numbers = read_numbers(tested_file)
        except:
            print 0.0
            print 'Failed to read file', os.path.basename(tested_file)
            sys.exit(0)


        if len(tested_numbers) != len(correct_numbers):
            print 0.0
            print 'Wrong answer'
            print 'Wrong number of entries in file ', os.path.basename(tested_numbers)
            print 'Expected', len(correct_numbers)
        else:
            is_correct = True
            for i in xrange(len(correct_numbers)):
                if abs(tested_numbers[i] - correct_numbers[i]) > COMPARISON_ACCURACY:
                    print 0.0
                    print 'Wrong answer'
                    print 'Value', tested_numbers[i], 'in position', i , 'is incorrect'
                    is_correct = False
                    break

        if is_correct:
            print 1.0
            print 'OK'
    else:
        print 'Expecting 3 command line arguments: test_file, correct_answer, tested_answer'