#!/usr/bin/env bash

set -euxo pipefail

echo "Waiting for Elasticsearch to come up..."
wait-for-it elasticsearch:9200 --strict --timeout=60 -- echo "Elasticsearch service is up."

echo "Checking if 'user' index exists..."
if curl -s http://elasticsearch:9200/_cat/indices | grep -q 'user'; then
  echo "'user' index already exists. Skipping index creation and mapping."
else
  echo "Creating 'user' index..."
  curl -XPUT -H 'Content-Type: application/json' http://elasticsearch:9200/user?pretty=true -d'
  {
    "settings" : {
      "index" : {
        "number_of_replicas" : 0
      }
    }
  }'

  echo "Creating 'user' mapping..."
  curl -XPUT 'http://elasticsearch:9200/user/_mapping' -H 'Content-Type: application/json' -d '
  {
      "properties" : {
          "full_name" : { "type" : "text", "store" : true },
          "bio" : { "type" : "text", "store" : true },
          "age" : { "type" : "integer" },
          "location" : { "type" : "text" },
          "enjoys_coffee" : { "type" : "boolean" },
          "created_on" : { "type" : "date" }
      }
  }'
fi

echo "Generating and inserting sample data..."
sudo pip install faker requests

cat << EOF > /tmp/generate_es_users.py
import json
import requests
from faker import Faker

fake = Faker()

for i in range(1, 500):
    user = {
        "full_name": fake.name(),
        "bio": f"My name is {fake.first_name()}. {fake.sentence()}",
        "age": fake.random_int(min=20, max=60),
        "location": f"{fake.latitude()},{fake.longitude()}",
        "enjoys_coffee": fake.boolean(),
        "created_on": fake.date_time_this_decade().isoformat()
    }

    response = requests.post(
        f"http://elasticsearch:9200/user/_doc/{i}",
        headers={"Content-Type": "application/json"},
        data=json.dumps(user)
    )
    if response.status_code == 409:
        print(f"User {i} already exists. Skipping.")
    else:
        print(f"Created user {i}, response: {response.status_code}")
EOF

# Make the Python script executable
chmod +x /tmp/generate_es_users.py

# Execute the Python script
python3 /tmp/generate_es_users.py
