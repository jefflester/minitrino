#!/usr/bin/env bash

#-----------------------------------------------------------------------------------------------
# https://github.com/andrewpuch/elasticsearch_examples
#-----------------------------------------------------------------------------------------------

set -euxo pipefail

echo "Waiting for Elasticsearch to come up..."
/opt/minipresto/wait-for-it.sh elasticsearch:9200 --strict --timeout=60 -- echo "Elasticsearch service is up."

echo "Creating user index..."
curl -XPUT http://localhost:9200/user?pretty=true;

echo "Creating user mapping..."
curl -XPUT http://localhost:9200/user/_mapping/profile?include_type_name=true -H 'Content-Type: application/json' -d '
{
    "profile" : {
        "properties" : {
            "full_name" : { "type" : "text", "store" : true },
            "bio" : { "type" : "text", "store" : true },
            "age" : { "type" : "integer" },
            "location" : { "type" : "text" },
            "enjoys_coffee" : { "type" : "boolean" },
            "created_on" : { "type" : "date" }
        }
    }
}
';

echo "Creating user profile records..."
curl -XPOST http://localhost:9200/user/profile/1?pretty=true -H 'Content-Type: application/json' -d '
{
    "full_name" : "Andrew Puch",
    "bio" : "My name is Andrew. I have a short bio.",
    "age" : 26,
    "location" : "41.1246110,-73.4232880",
    "enjoys_coffee" : true,
    "created_on" : "2015-05-02T14:45:10.000-04:00"
}
';

curl -XPOST http://localhost:9200/user/profile/2?pretty=true -H 'Content-Type: application/json' -d '
{
    "full_name" : "Elon Musk",
    "bio" : "Elon Musk is a moderately successful person.",
    "age" : 43,
    "location" : "37.7749290,-122.4194160",
    "enjoys_coffee" : false,
    "created_on" : "2015-05-02T15:45:10.000-04:00"
}
';

curl -XPOST http://localhost:9200/user/profile/3?pretty=true -H 'Content-Type: application/json' -d '
{
    "full_name" : "Some Hacker",
    "bio" : "I am a haxor user who you should end up deleting.",
    "age" : 1000,
    "location" : "37.7749290,-122.4194160",
    "enjoys_coffee" : true,
    "created_on" : "2015-05-02T16:45:10.000-04:00"
}
';

curl -XPOST http://localhost:9200/user/profile/4?pretty=true -H 'Content-Type: application/json' -d '
{
    "full_name" : "Julian Spring",
    "bio" : "Starburst Presto superuser.",
    "age" : 7,
    "location" : "37.7749290,-122.4194160",
    "enjoys_coffee" : true,
    "created_on" : "2016-03-02T16:45:10.000-04:00"
}
';
