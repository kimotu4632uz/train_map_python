#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path
import json

def main(input, output):
  geojson = json.loads(Path(input).read_text())

  id_list = { (f['properties']['運営会社'], f['properties']['路線名'], f['properties']['駅名']) for f in geojson['features'] }
  features = []

  for (comp, line, station) in id_list:
    matched = [ f for f in geojson['features'] if f['properties']['運営会社'] == comp and f['properties']['路線名'] == line and f['properties']['駅名'] == station ]

    coords = []
    for feature in matched:
      coords.extend(feature['geometry']['coordinates'])

    xs = [ c[0] for c in coords ]
    ys = [ c[1] for c in coords ]
    point = ( (max(xs) + min(xs))/2, (max(ys) + min(ys))/2 )

    features.append({
      'type': 'Feature',
      'properties': matched[0]['properties'],
      'geometry': {
        'type': 'Point',
        'coordinates': [ point[0], point[1] ]
      }
    })

  result = {
    'type': 'FeatureCollection',
    'features': features
  }

  Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == "__main__":
  parser = ArgumentParser(description='convert station geojson features from linestring into point.')
  parser.add_argument('--input', '-i', required=True, help='input geojson file.')
  parser.add_argument('--output', '-o', required=True, help='output geojson file.')
  args = parser.parse_args()

  main(args.input, args.output)
