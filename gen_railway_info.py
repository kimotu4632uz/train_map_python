#!/usr/bin/env python
from bs4 import BeautifulSoup
from cssutils import parseStyle
import requests

from argparse import ArgumentParser
from pathlib import Path
import json


class TableResolver:
    def __init__(self, table, include_header=True):
        if table.tbody is not None:
            tbody = table.tbody
        else:
            tbody = table

        cols_iter = filter(lambda x: x.name == 'tr', tbody.children)

        if include_header:
            self._header = next(cols_iter)
        else:
            self._header = None
        self._cols = cols_iter
        self.rowspan_save = dict()
    
    def __iter__(self):
        return self
    
    def __next__(self):
        next_col = next(self._cols, None)
        if next_col is None:
            raise StopIteration()

        next_iter = filter(lambda x: x.name == 'td', next_col.children)
        return TableResolver_col(next_iter, self)


class TableResolver_col:
    def __init__(self, inner_iter, parent_instalce):
        self._inner_iter = inner_iter
        self._parent = parent_instalce
        self._colspan_count = 0
        self._idx = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._colspan_count != 0:
            self._colspan_count -= 1
            self._idx += 1
            return None
        
        next_item = None
        if self._idx in self._parent.rowspan_save and self._parent.rowspan_save[self._idx]['count'] != 0:
            self._parent.rowspan_save[self._idx]['count'] -= 1
            next_item = self._parent.rowspan_save[self._idx]['item']
        else:
            next_item = next(self._inner_iter, None)

        if next_item is None:
            raise StopIteration()

        if 'colspan' in next_item.attrs:
            self._colspan_count = int(next_item['colspan']) - 1
        
        if 'rowspan' in next_item.attrs:
            count = int(next_item['rowspan']) - 1
            del next_item.attrs['rowspan']
            self._parent.rowspan_save[self._idx] = { 'count': count, 'item': next_item }
        
        self._idx += 1
        return next_item


def style2rgb(style):
    bg = parseStyle(style).getProperty('background').propertyValue[0]
    return '{:02x}{:02x}{:02x}'.format(bg.red, bg.green, bg.blue)


def fetch_line_color(info_json):
    resp = requests.get('https://ja.wikipedia.org/wiki/%E6%97%A5%E6%9C%AC%E3%81%AE%E9%89%84%E9%81%93%E3%83%A9%E3%82%A4%E3%83%B3%E3%82%AB%E3%83%A9%E3%83%BC%E4%B8%80%E8%A6%A7#%E6%9D%B1%E6%97%A5%E6%9C%AC%E6%97%85%E5%AE%A2%E9%89%84%E9%81%93%EF%BC%88JR%E6%9D%B1%E6%97%A5%E6%9C%AC%EF%BC%89')
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    for tag in soup(string='\n'):
        tag.extract()

    resolve_list = [
        {
            'comp_name': '東日本旅客鉄道',
            'comp_code': '2',
            'rules': [
                {
                    'table': lambda: soup.find(lambda tag: tag.name == 'table' and tag.caption is not None and tag.caption.text == '東京近郊地区における路線案内色と車体色\n'),
                    'key': [0],
                    'val': 2
                },
                {
                    'table': lambda: soup.find(lambda tag: tag.name == 'table' and tag.caption is not None and tag.caption.text == 'JR東日本各路線のラインカラー\n'),
                    'key': [0, 1],
                    'val': 2
                }
            ]
        },
        {
            'comp_name': '東海旅客鉄道',
            'comp_code': '2',
            'rules': [
                {
                    'table': lambda: soup.select_one('#東海旅客鉄道（JR東海）').parent.next_sibling.next_sibling,
                    'key': [0],
                    'val': 2
                }
            ]
        }
    ]

    line_color_list = list()

    for comp in resolve_list:
        if info_json is not None:
            lines = next((x['lines'] for x in info_json if x['comp']['name'] == comp['comp_name'] and x['comp']['type']['code'] == comp['comp_code']))
        lines_not_found = list()

        for rule in comp['rules']:
            table = rule['table']()

            for col in TableResolver(table):
                items = list(col)
                key = ' '.join([ items[key].text.replace('\n', '') for key in rule['key'] if items[key] is not None ])
                val = style2rgb(items[rule['val']]['style'])

                line = next((x for x in lines if x['name'] == key), None) if info_json is not None else None
                if line is not None:
                    line['color'] = val
                else:
                    lines_not_found.append({'line_name': key, 'line_color': val})
        
        line_color_list.append({'comp_name': comp['comp_name'], 'lines': lines_not_found})

    return line_color_list


def gen_info(geojson):
    ctype_dict = {
        '1': '新幹線',
        '2': 'JR在来線',
        '3': '公営鉄道',
        '4': '民営鉄道',
        '5': '第三セクター',
    }

    ltype_dict = {
        '11': '普通鉄道JR',
        '12': '普通鉄道',
        '13': '鋼索鉄道',
        '14': '懸垂式鉄道',
        '15': '跨座式鉄道',
        '16': '案内軌条式鉄道',
        '17': '無軌条鉄道',
        '21': '軌道',
        '22': '懸垂式モノレール',
        '23': '跨座式モノレール',
        '24': '案内軌条式',
        '25': '浮上式',
    }

    comp_line_list = []
    comp_list = { (f['properties']['運営会社'], f['properties']['事業者種別']) for f in geojson['features'] }
    comp_line_detail = { (f['properties']['運営会社'], f['properties']['事業者種別'], f['properties']['路線名'], f['properties']['鉄道区分']) for f in geojson['features'] }

    for cname, ctype in comp_list:
        line_list = [ {
            'name': detail[2],
            'type': {
                'name': ltype_dict[detail[3]],
                'code': detail[3],
            },
        } for detail in comp_line_detail if detail[0] == cname and detail[1] == ctype ]

        if ctype == '1':
            cname += '(新幹線)'

        comp_line_list.append({
            'comp': {
                'name': cname,
                'type': {
                    'name': ctype_dict[ctype],
                    'code': ctype
                },
            },
            'lines': line_list
        })

    sorted_list = []
    for item in comp_line_list:
        item['lines'] = sorted(item['lines'], key=lambda x: x['type']['code'])
        sorted_list.append(item)

    return sorted(sorted_list, key=lambda x: x['comp']['type']['code'])


if __name__ == '__main__':
    parser = ArgumentParser(description='generate railway info from geojson and wikipedia.')
    parser.add_argument('--input', '-i', required=True, help='input geojson file.')
    parser.add_argument('--output-info-json', required=True, help='path of generated json file.')
    parser.add_argument('--output-line-color', required=True, help='path of line color file if some line color not fit to info json.')
    args = parser.parse_args()

    geojson = json.loads(Path(args.input).read_text())
    info = gen_info(geojson)
    line_color_left = fetch_line_color(info)

    Path(args.output_info_json).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')

    if len(line_color_left) > 0:
        Path(args.output_line_color).write_text(json.dumps(line_color_left, ensure_ascii=False, indent=2), encoding='utf-8')
