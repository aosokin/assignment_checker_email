import sys


def main():
    if len(sys.argv) == 3:
        test_file = sys.argv[1].strip()
        with open(test_file, 'r') as f:
            all_lines = f.readlines()

        subset_file = sys.argv[2].strip()
        with open(subset_file, 'r') as f:
            split = f.readlines()
        split = [int(s) for s in split]
        
        for i in split:
            if len(all_lines) > i:
                print(all_lines[i], end="")
    else:
        print('Expecting 2 command line arguments: result file and split file')

if __name__ == '__main__':
    main()
