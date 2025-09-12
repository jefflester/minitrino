# Troubleshooting

- If you experience issues executing a Minitrino command, re-run it with the
  `-v` option for verbose output. This will often reveal the issue's root cause.
- If you experience an issue with a particular Docker container, consider
  running these commands:
  - `docker logs ${CONTAINER_NAME}`: Print the logs for a given container to the
    terminal
  - `docker ps`: Show all running Docker containers and associated statistics
  - `docker inspect ${CONTAINER_NAME}` to see detailed about a container
- If you experience issues with a library module, check that that module is
  structured correctly according to the
  [module tutorial](https://github.com/jefflester/minitrino/wiki/Build-a-Module),
  and ensure the library and the CLI versions match (check with
  `minitrino version`).
- Sometimes, a lingering named volume can cause problems (i.e. a stale Hive
  metastore database volume from a previous module deployment). To rule this
  out, run:
  - `minitrino down`
  - `minitrino -v remove --volumes` to remove **all** existing Minitrino
    volumes. Alternatively, run
    `minitrino -v remove --volumes --label <your label>` to specify a specific
    module for which to remove volumes. See the
    [removing resources](https://github.com/jefflester/minitrino/wiki/Workflow-Examples#remove-minitrino-resources)
    section for more information.

If none of these troubleshooting tips help to resolve your issue,
[please file a GitHub issue](https://github.com/jefflester/minitrino/wiki/Reporting-Bugs-and-Contributing)
and provide as much information as possible.
