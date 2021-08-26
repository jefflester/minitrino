# Elasticsearch Connector Module

This module contains an ES container with some preloaded data. It contains: a
schema (ES mapping), a table (ES doc mapping), and data (ES docs).

## Loading your own data

Since port 9200 is exposed on localhost you can add your own data like this:

    # Create user index
    curl -XPUT http://localhost:9200/user?pretty=true;

    # Create user mapping
    curl -XPUT http://localhost:9200/user/_mapping/profile?include_type_name=true -H 'Content-Type: application/json' -d '
    {
        "profile" : {
            "properties" : {
                "full_name" : { "type" : "text", "store" : true },
                "bio" : { "type" : "text", "store" : true },
                "age" : { "type" : "integer" },
                "location" : { "type" : "geo_point" },
                "enjoys_coffee" : { "type" : "boolean" },
                "created_on" : {
                    "type" : "date", 
                    "format" : "date_time" 
                }
            }
        }
    }
    ';

    # Create user profile records
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

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module elasticsearch
    docker exec -it trino bash 
    trino-cli
    trino> show schemas from elasticsearch;
