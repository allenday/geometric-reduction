# -*- coding: utf-8 -*-

import sys
import os
import os.path
import argparse
import json
from pathlib import Path
from enum import Enum

class SType(Enum):
    UNKNOWN = 0
    GOOD = 1
    BAD = 2
    AMBIGUOUS = 3

class Segment:

    def __init__(self, min, max, label, score):
        self.min = min
        self.max = max
        self.label = label
        self.score = score
        self.type = SType.UNKNOWN

    def __lt__(self, other):
        if self.min == other.min:
            return self.max < other.max
        return self.min < other.min

    def __repr__(self):
        return "min: {} max: {} label: {} score: {} type: {}".format(self.min, self.max, self.label, self.score, self.type)

    def length(self):
        return self.max - self.min + 1


def get_longest_valid_chain(segments, chain_start, chain_stop, maximum_percent_contamination, min_segment_score):
    #print ('get_longest_valid_chain', chain_start, chain_stop)

    if chain_start == -1 or chain_stop == -1:
        return (-1, 0)

    length = chain_stop - chain_start + 1
    good_lengths_sat = []
    bad_lengths_sat  = []
    scores_sat = []


    for i in range(chain_start, chain_start + length):
        l = segments[i].length()
        if segments[i].type == SType.GOOD:
            good_lengths_sat.append(l)
            bad_lengths_sat.append(0)            
            scores_sat.append(segments[i].score * l)
        else:
            good_lengths_sat.append(0)
            scores_sat.append(0)
            bad_lengths_sat.append(l)

    for i in range(chain_start + 1, chain_start + length):
        good_lengths_sat[i] += good_lengths_sat[i - 1]
        bad_lengths_sat[i] += bad_lengths_sat[i - 1]
        scores_sat[i] += scores_sat[i - 1]


    #print ('good_lenghts', good_lengths_sat)
    #print ('bad_lenghts', bad_lengths_sat)

    for i in range(chain_stop, chain_start - 1, -1):
        if segments[i].type != SType.GOOD:
            continue
        percent_contamination = float(bad_lengths_sat[i - chain_start]) / float(bad_lengths_sat[i - chain_start] + good_lengths_sat[i - chain_start])
        score = scores_sat[i - chain_start] / float(good_lengths_sat[i - chain_start])
        #print (i, percent_contamination, score)

        if percent_contamination <= maximum_percent_contamination and score >= min_segment_score:
            return (i, score)


def do_job(input_file_path, output_file_path, desired_label, score, max_ambiguous_points, max_bad_points, maximum_percent_contamination, min_segment_score):

    print (input_file_path, output_file_path)

    try:
        f = open(input_file_path)
        data = json.load(f)
        #print (data)
    except Exception as e:        
        print ('Can not read input json from ', input_file_path)
        print(e)
        return 

    total_segments = len(data)
    print ("total_segments: ", total_segments)

    segments = []

    for js in data:
        #print (js)
        try:
            s = Segment(int(js['min']), int(js['max']), js['label'], float(js['score']))

            if s.score >= score:
                if s.label == desired_label:
                    s.type = SType.GOOD
                else:
                    s.type = SType.BAD
            else:
                s.type = SType.AMBIGUOUS

        except Exception as e:
            print ("invalid segment description", js)
            print ("missing key: ", e)
            return      
        segments.append(s)

    segments.sort()

#    for s in segments:
#        print (s)

    enriched_segments = []
    for i in range(1, total_segments):
        enriched_segments.append(segments[i - 1])
        if segments[i - 1].max != segments[i].min - 1:
            gapseg = Segment(segments[i - 1].max + 1, segments[i].min - 1, 'NA', float(0))
            gapseg.type = SType.AMBIGUOUS
            enriched_segments.append(gapseg)
    enriched_segments.append(segments[total_segments - 1])
    for s in enriched_segments:
        print (s)
    segments = enriched_segments
    total_segments = len(segments)

    for i in range(1, total_segments):
        if segments[i - 1].max >= segments[i].min:
            print ("Segments {}=[{},{}] and {}=[{},{}] intersects. This is not suppported. Fix input data.".format(i - 1, segments[i - 1].min, segments[i - 1].max, i, segments[i].min, segments[i].max))
            return

#        if segments[i - 1].max != segments[i].min - 1:
#            print ("There is a gap between segment {}=[{},{}] and {}=[{},{}] : [{}, {}]. This is not suppported. Fix input data.".format(i - 1, segments[i - 1].min, segments[i - 1].max, i, segments[i].min, segments[i].max, segments[i - 1].max + 1, segments[i].min - 1))
#            return

    chain_start = -1
    chain_stop = -1
    total_ambiguous = 0
    total_bad = 0
    ind = 0

    result = []

    while ind < total_segments:

        if chain_start == -1:
            if segments[ind].type == SType.GOOD:
                chain_start = ind
                chain_stop = ind
                total_ambiguous = 0
                total_bad = 0                                
        else:
            stop_forward = False
            if segments[ind].type == SType.AMBIGUOUS:
                total_ambiguous += segments[ind].length()
                if total_ambiguous > max_ambiguous_points:
                    stop_forward = True
            elif segments[ind].type == SType.BAD:
                total_bad += segments[ind].length()
                if total_bad > max_bad_points:
                    stop_forward = True
            else:
                chain_stop = ind

            if stop_forward:
                chain_end, score = get_longest_valid_chain(segments, chain_start, chain_stop, maximum_percent_contamination, min_segment_score)
                result.append({"min":segments[chain_start].min, "max":segments[chain_end].min, "label":segments[chain_start].label, "score":score})
                ind = chain_end
                chain_start = -1
        ind += 1

    chain_end, score = get_longest_valid_chain(segments, chain_start, chain_stop, maximum_percent_contamination, min_segment_score)
    if chain_end != -1:        
        result.append({"min":segments[chain_start].min, "max":segments[chain_end].min, "label":segments[chain_start].label, "score":score})

    print ('result:')
    print (result)

    try:
        with open(output_file_path, 'w') as outfile:
            json.dump(result, outfile)    

    except Exception as e:
        print ("Can not save results to", output_file_path)
        print ("Error: ", e)

    
def check_positive_int(value):

    int_value = int(value)
    if int_value <= 0:
        raise argparse.ArgumentTypeError("{} is not a positive integer".format(value))
    return int_value

def check_positive_float(value):

    float_value = float(value)
    if float_value < 0:
        raise argparse.ArgumentTypeError("{} is not a postive float".format(value))
    return float_value

def check_float_0_1(value):

    float_value = float(value)
    if float_value < 0 or float_value > 1:
        raise argparse.ArgumentTypeError("{} is not a float in [0, 1] range".format(value))
    return float_value

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file',  help='Input file path, file must exists.', required=True)
    parser.add_argument('-o', '--output_file', help='Output file path', required=True)
    parser.add_argument('--desired_label', required=True)
    parser.add_argument('--min_segment_length', type=check_positive_int, required=True)
    parser.add_argument('--max_ambiguous_points', type=check_positive_int, required=True)
    parser.add_argument('--max_bad_points', type=check_positive_int, required=True)
    parser.add_argument('--score', type=check_positive_float, required=True)
    parser.add_argument('--min_segment_score', type=check_positive_float, required=True)
    parser.add_argument('--maximum_percent_contamination', type=check_float_0_1, required=True)

    args = vars(parser.parse_args())

    input_file = Path(args['input_file'])
    output_file = Path(args['output_file'])

    if not input_file.is_file():
        print('Fatal error: Input file {0} does not exists'.format(args['input_file']))
        sys.exit(-1)        

    do_job(str(input_file), str(output_file), args['desired_label'], float(args['score']), int(args['max_ambiguous_points']), int(args['max_bad_points']), float(args['maximum_percent_contamination']), float(args['min_segment_score']))
