import pandas as pd
import tabula

import aiofiles
import json
import os

_path = os.getcwd()
_filespath = os.path.join(_path, 'files')

# def find_file(filename: str, files: list):
#     for f in files:
#         if f.filename == filename:
#             return f

async def pdf_to_json(filename: str):
    pdfpath = os.path.join(_filespath, filename)
    dfs = tabula.read_pdf(
        pdfpath,
        pages="all",
        stream=True
    )

    print(f"Data Type :{type(dfs)}")
    print(f"Data Length: {len(dfs)}")

    for index, table in enumerate(dfs):
        print(f"\nData Index: {index}")
        print(type(table))
        print(table.head())

    jsonpath = os.path.join(_filespath, "tmp.json")
    __json = tabula.convert_into(
        pdfpath,
        jsonpath,
        output_format="json",
        pages="all",
        stream=True
    )

    with open(jsonpath, 'r') as file:
        _json = json.load(file)

    print(_json)

    return _json
