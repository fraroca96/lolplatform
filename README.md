# lolplatform
League of Legends platform for loading LoL's data and creating data analysis insights for proffesional or amateur teams.

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



## Necessary actions to run the system

- To download data, you need a Riot Games API KEY. You have to register and generate it [here](https://developer.riotgames.com/).
- You need to install docker in your machine.

NOTE: The name of the docker image might change if you rebuild the system (`docker ps` to check image names - you will see postgress port also)
```
docker-compose up --build -d
docker exec -it lolplatform bash

```

**IMPORTANT**: If you don't have a permanent API KEY, you have to regenerate it every day (it lasts for 24 hours) and update it in .env file. Then you need to rebuild the container in order to this update in the environment variable to be done in the machine.

`docker-compose up -d`



In order to include others players data, you can access the info in [LolPros](https://lolpros.gg/search). 

