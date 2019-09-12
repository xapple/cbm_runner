---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.1'
      jupytext_version: 1.1.7
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

```python
import sys, pandas 
# Catch database related errors
from pyodbc import Error
from pandas.io.sql import DatabaseError

# Project modules
# Load the cbm_runner package from 'repos/' (instead of 'deploy/') #
sys.path.insert(0, "/repos/cbmcfs3_runner/") 
from cbmcfs3_runner.core.continent import continent

# Choose  a country
country = 'LU'
country = 'BG'
db = continent.countries[country].aidb.database

list_all_column_names = True
```

# Introduction





## List all tables

```python
db.tables
```

## List all column names

```python
if list_all_column_names:
    for table in db.tables:
        print("")
        print(table)
        try: 
            print(db[table].columns)
        except (Error, DatabaseError) as error:
            print(error)
```

# Display



## tblsimulation

```python

db['tblsimulation']
```

## Disturbance Matrix
The following tables contain information relevant to the disturbance matrix.
### tbldm

```python
db['tbldm']
```

### tbldmassociationdefault

```python
db['tbldmassociationdefault']
```

### tbldmassociationspudefault

```python
db['tbldmassociationspudefault']
```

### tbldmvalueslookup

```python
db['tbldmvalueslookup']
```

### tblsinkname

```python
db['tblsinkname']
```

### tblsourcename

```python
db['tblsourcename']
```

## tbluserimportconfig

```python
db['tbluserimportconfig']
```