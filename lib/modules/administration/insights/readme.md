# Insights Module

This module sets up the [Starburst
Insights](https://docs.starburst.io/latest/insights.html), which includes a
cluster overview UI as well as a SQl editor.

## Usage

    minitrino --env STARBURST_VER=<ver> provision --module insights

You can view Insights in the browser by visiting:

    localhost:8080/ui/insights/

You can view the Insights SQL editor in the browser by visiting:

    localhost:8080/ui/insights/ide
