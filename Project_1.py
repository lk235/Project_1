# 项目一：准备数据

import csv
import codecs
# import pprint
import re
import xml.etree.cElementTree as ET
import sys

reload(sys)
sys.setdefaultencoding('utf8')
# import cerberus
# import schema

OSM_PATH = "C:/Users/Administrator/Desktop/Project_1"
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# 匹配G104、S41等国道、省道路名
G104_none_line_char_re = re.compile(ur'\u56fd\u9053(?!\u7ebf)')
G104_none_G_char_re = re.compile(r'^(?!G)104')
S41_re = re.compile(r'S41')
S233_re = re.compile(ur'223\u7701\u9053')
S325_re = re.compile(r'S325')
S1_re = re.compile(r'S1')
X9_re = re.compile(r'X[0-9]{3}')

# 匹配中文字符
chinese_re = re.compile(ur'[\u4e00-\u9fff]')
# 匹配名称中出现数字的路名
road_have_number_re = re.compile(r'\d')
# 匹配含有“路、道、线”等文字的路名
Is_road_re = re.compile(ur'[\u8def|\u7ebf|\u9053]')

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

# SCHEMA = schema.schema

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

# S41省道名字已经弃用，统一改为S233省道；其他国道、省道也统一格式
mapping = {'S41': 'S223省道',
           '223省道': 'S223省道',
           'S325': 'S325省道',
           'S1': 'S1市域铁路',
           "NationalRoad104": "G104国道线",
           "104NationalRoad": "G104国道线",
           '国道': '国道线',
           '104': "G104"

           }


# 道路名清洗函数，清洗目标限于国道，省道，县道
def update_name(name):
    S41 = S41_re.search(name)
    S233 = S233_re.search(name)
    S325 = S325_re.search(name)
    S1 = S1_re.search(name)
    X9 = X9_re.search(name)

    if name == 'NationalRoad104':
        name = mapping['NationalRoad104']
    elif name == '104NationalRoad':
        name = mapping['104NationalRoad']
    elif S41:
        old_name = str(S41.group())
        replace = mapping[old_name]
        name = name.replace(old_name, replace)
    elif S233:
        old_name = str(S233.group())
        replace = mapping[old_name]
        name = name.replace(old_name, replace)
    elif S325:
        old_name = str(S325.group())
        replace = mapping[old_name]
        name = name.replace(old_name, replace)
    elif S1:
        old_name = str(S1.group())
        replace = mapping[old_name]
        name = name.replace(old_name, replace)
    elif X9:
        old_name = str(X9.group())
        replace = old_name + '县道'
        name = name.replace(old_name, replace)
    else:
        G104_none_line_char = G104_none_line_char_re.search(name)
        G104_none_G_char = G104_none_G_char_re.search(name)
        if G104_none_line_char:
            old_name = str(G104_none_line_char.group())
            replace = mapping[old_name]
            name = name.replace(old_name, replace)
        if G104_none_G_char:
            old_name = str(G104_none_G_char.group())
            replace = mapping[old_name]
            name = name.replace(old_name, replace)

    return name


# 建立子标签tag字典并赋值
def add_to_dict(el_id, key, value, default_tag_type, tags):
    tag_dict = {}
    tag_dict['type'] = default_tag_type
    tag_dict['key'] = key
    tag_dict['id'] = el_id
    tag_dict['value'] = value
    tags.append(tag_dict)


# 清洗并规范xml数据，转为python字典    
def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    way_nodes = []
    tags = []

    # 处理node节点
    if element.tag == 'node':
        node_attribs = element.attrib
        el_id = element.attrib['id']
        for k in node_attribs.keys():
            if k not in node_attr_fields:
                del node_attribs[k]

        for tag in element.iter("tag"):

            key = tag.attrib['k']
            value = tag.attrib['v'].replace(' ', '')

            if not problemchars.search(value):
                # 排除name和name.zh中不含中文的字段
                if key == 'name' or key == 'name.zh':
                    if chinese_re.search(tag.attrib['v']):
                        add_to_dict(el_id, key, value, default_tag_type, tags)
                # 清理source字段，统一为大写
                elif key == 'source':
                    value = value.upper()
                    add_to_dict(el_id, key, value, default_tag_type, tags)
                else:
                    add_to_dict(el_id, key, value, default_tag_type, tags)
        # print {'node': node_attribs, 'node_tags': tags}
        return {'node': node_attribs, 'node_tags': tags}

    # 处理way节点
    elif element.tag == 'way':
        way_attribs = element.attrib
        el_id = element.attrib['id']
        for k in way_attribs.keys():
            if k not in way_attr_fields:
                del way_attribs[k]

        position = 0
        for tag in element.iter():

            if tag.tag == 'tag':
                key = tag.attrib['k']
                # 对所有属性值进行去空格处理，统一格式
                value = tag.attrib['v'].replace(' ', '')

                if not problemchars.search(value):
                    # 排除name和name.zh中不含中文的字段，并更新国道、省道、县道路名
                    if key == 'name' or key == 'name:zh':
                        value = update_name(value)
                        if chinese_re.search(value):
                            tag_dict = {}
                            if Is_road_re.search(tag.attrib['v']):
                                tag_dict['type'] = 'Road'
                            else:
                                tag_dict['type'] = default_tag_type
                            tag_dict['id'] = el_id
                            tag_dict['key'] = key
                            tag_dict['value'] = value
                            tags.append(tag_dict)
                    # 清理source字段，统一为大写
                    elif key == 'source':
                        value = value.upper()
                        add_to_dict(el_id, key, value, default_tag_type, tags)
                    else:
                        add_to_dict(el_id, key, value, default_tag_type, tags)

            if tag.tag == 'nd':
                way_dict = {}
                way_dict['id'] = el_id
                way_dict['node_id'] = tag.attrib['ref']
                way_dict['position'] = position
                position = position + 1
                way_nodes.append(way_dict)
        # print  {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}  
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


def get_element(osm_file, tags=('node', 'way')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def process_map(file_in):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
            codecs.open(WAYS_PATH, 'w') as ways_file, \
            codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
            codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


process_map('C:/Users/Administrator/Desktop/Project_1/wenzhou.osm')
print 'END'