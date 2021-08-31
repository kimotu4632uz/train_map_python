#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path
import json

def main(input):
  geojson = json.loads(Path(input).read_text())
  comp_line = list({ (f['properties']['運営会社'], f['properties']['路線名']) for f in geojson['features'] })

  for i, (comp, line) in enumerate(comp_line):
    features = [ f for f in geojson['features'] if f['properties']['運営会社'] == comp and f['properties']['路線名'] == line ]
    geojson_split = {
      "type": "FeatureCollection",
      "features": features
    }
    Path(f'splited/{i}.geojson').write_text(json.dumps(geojson_split, ensure_ascii=False), encoding='utf-8')


if __name__ == "__main__":
  parser = ArgumentParser(description='split geojson feature into splited/ dir by company and line name.')
  parser.add_argument('--input', '-i', required=True, help='input geojson file.')
  args = parser.parse_args()

  main(args.input)
