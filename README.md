# lolplatform
League of Legends platform for loading LoL's data and creating data analysis insights for proffesional or amateur teams.


```
docker-compose up --build -d
docker exec lolplatform bash

```

Example of use:

1.
```
python 3
>>> import lolplatform.dataset.get_riot_data as grd

>>> loldataobject = grd.lolData(player='name_example')
>>> print('Name: ', loldataboject.name)

```

2. Connection to the Postgress SQL
```
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dbname=os.getenv("DB_NAME")
)

cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

cur.close()
conn.close()

```

## Streamlit interface process

```
streamlit run streamlit/main.py --server.address=0.0.0.0 --server.port=8501
```

Open url: `localhost:8501`

