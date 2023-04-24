# Password File Authentication Module

This module configures Trino to authenticate users with a password file.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module password-file
    docker exec -it trino bash 

    trino-cli --server https://trino:8443 \
       --truststore-path /etc/starburst/ssl/truststore.jks --truststore-password changeit \
       --user bob --password
       
    trino> show schemas from tpch;

## Default Usernames and Passwords

- alice / trinoRocks15
- bob / trinoRocks15

## Adding a New User to the Password File

Example with username `admin` and password `trinoRocks15`

    docker exec trino htpasswd -bB -C 10 /etc/starburst/password.db admin trinoRocks15
