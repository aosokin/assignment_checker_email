# params: test data file, teacher-provided answer, student answer

source activate assignment_server 2> /dev/null

# baselines:
# baseline1 - 11.86 - 3 points
# baseline2 - 25.46 - 6 points
# baseline3 - 27.45 - 8 points
# baseline4 - 29.48 - 10 points

if RESULT=$(python checker_bleu_select_subset.py "$3" "$1".public.split | sacrebleu "$1".public --tokenize none --width 2 -b 2>&1); then
    OLDIFS=$IFS
    IFS=',';
    BASELINE=0.0
    BASELINE_POINTS=0
    for i in 11.86,3 25.46,6 27.45,8 29.48,10
    do
        set -- $i
        if [ 1 -eq "$(echo "${RESULT} >= $1" | bc)" ]
        then  
            BASELINE=$1
            BASELINE_POINTS=$2
        fi
    done
    IFS=$OLDIFS

    echo ${BASELINE_POINTS} ${RESULT}

    echo "OK"

    echo "Successfully obtained BLEU of ${RESULT} - reached baseline ${BASELINE}"
else
    rc=$?
    STDERR=$RESULT

    echo "0 0.0"
    echo "sacrebleu returned exit code ${rc}"
    echo "Error message: ${STDERR}"
fi

