# Teradata Connector Module
This module provisions a Teradata connector. However, a Teradata database still needs to be brought up separately from Minipresto.

## Configuration

The following environment variables need to be set, by adding them to the Minipresto user configuration file, or by setting the environment variables prior to starting Minipresto:

TERADATA_CONNECT_URL - JDBC Connection string to Teradata database (connection-url), ex. jdbc:teradata://HOST
TERADATA_CONNECT_USER - Login user (connection-user)
TERADATA_CONNECT_PASSWORD - Login password (connection-password)

Environmental variables are also used to set the path to the Teradata JDBC drivers, which must be downloaded separately for your TD database vrsion. 

TERADATA_TERAJDBC_PATH - Path to terajdbc4.jar
TERADATA_TDGSSCONFIG_PATH - Path to tdgssconfig.jar

At a minimum you would need TERADATA_TERAJDBC_PATH, but older versions may also require TERADATA_TDGSSCONFIG_PATH. The latter is commented out in lib/modules/catalog/teradata/teradata.yml. If you do need this additional JAR file, please make sure to uncomment the corresponding line prior to starting Minipresto.

This module also requires a valid Starburst Data license. Please review the main README for instructions on how to set up the license file.
