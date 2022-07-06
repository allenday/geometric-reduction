# geometric-reduction

```
python3 reduction.py -o ./tests/out.json --min_segment_length 3 --max_ambiguous_points 3 --max_bad_points 3 --desired_label A --score 0.8 --min_segment_score 0.8 --maximum_percent_contamination 0.35 -i ./tests/test00.json
```

Demonstrate annealing of two "A" segments
```
python3 ./reduction.py -o ./tests/out.json --min_segment_length 1 --max_ambiguous_points 60 --max_bad_points 5 --score 0.8 --min_segment_score 0.8 --maximum_percent_contamination 0.5 --desired_label A -i ./tests/B-sub.json
```
