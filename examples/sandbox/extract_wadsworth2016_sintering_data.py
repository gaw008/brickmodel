"""Convert the author's twelve six-column groups without smoothing or fitting."""
import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    with args.source.open() as stream:
        rows = list(csv.reader(stream,delimiter='\t'))
    fields = ['time_s','temperature_k','normalized_porosity','porosity_error_printed','length_m','length_error_m']
    width = len(fields); runs = []
    for group in range(len(rows[1])//width):
        start = group*width
        records = [{'source_line':index+3,**dict(zip(fields,map(float,row[start:start+width]),strict=True))}
                   for index,row in enumerate(rows[2:]) if row[start]]
        runs.append({'run_id':f'column-group-{group+1:02d}',
                     'source_columns_one_based':[start+1,start+width],
                     'nominal_temperature_header':rows[0][start],'records':records})
    result = {'source_filename':args.source.name,
              'classification':'author-published processed observations, not original camera recordings',
              'total_records':sum(len(run['records']) for run in runs),'runs':runs}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'groups':len(runs),'observations':result['total_records']}))


if __name__=='__main__':
    main()
