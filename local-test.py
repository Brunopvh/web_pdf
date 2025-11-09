#!/usr/bin/env python3
#

from soup_files import JsonConvert, JsonData, File

outfile = 'teste.json'

base = {
    "ip_server": "192.168.100.47",
    "rt_split_pdf": "uploads/pdf/split",
    "rt_join_pdf": "uploads/pdf/join",
}


dt = JsonConvert.from_dict(base)

dt.to_json_data().to_file(File(outfile))