# Ideas

## Remove `cmd_executor.execute()` Instances - IN PROGRESS

In an effort to make use of the Docker SDK and reduce dependence on the shell,
I'd like to remove as many instances of *host shell* `cmd_executor.execute()` as
possible. Container usage of this method is still perfectly fine. A couple will
be unavoidable (like `docker exec -it ...` and `docker compose up`), but this
should be fine since Docker is a core dependency of Minitrino.

## Add Coverage Badge to Readme

Ask ChatGPT for help. Sounds like I need to upload the coverage report after my
CLI test workflow completes.

## Make `Library` Class

All library functionality is stashed in the context object or the `lib-install`
command. This should be grouped into a `Library` class and packaged under
`core`. This will better position the CLI to work out-of-the-box with a REST
API.

## Docker Compose Wrapper

This would be a big project. That said, it would improve Minitrino's ability to
control minute Compose things we don't like, e.g. how Compose project labels are
applied to whatever module is the first module to invoke an image pull. In
Minitrino context, images are global resources, so having a compose project
label doesn't make any sense.

We could add subtle enhancements to YAML support, e.g. worker or cluster
provisioning logic (granted much of this can be handled by `metadata.json`).

Implementation-wise, the idea would be:

- Have a `docker` CLI dependency for access to `docker compose config`
  - This shows us all the Docker objects that need to be deployed (in YAML).
- Translate the captured YAML into Docker objects through the Docker SDK.
- Write a process that copies `docker compose up` logic.

The bulk of the effort here is that second step, as we'd need to account for:

- Container definitions
- Volumes definitions (bind mounts and named volumes)
- Network definitions
- Anything else?

Note that we already have Minitrino wrappers for containers, volumes, networks,
and images. We could use them to our advantage here.

Overall, we just need to decide if this would be worth it. Ultimately, it would:

- Give us complete control over Compose objects an functionality.
- Decouple us from leveraging shell execution as much as we do, and instead
  leverage the Docker SDK.

## Telemetry

We could track deployments (with modules/OS) in a database or something. This
would allow us to determine how often the tool is used.

## Adding and Removing modules

**Note:** Doing this would be so much easier with our own Compose wrapper.

Add a module:

- Detect extra module
- Run the compose command to provision new module containers
- Remove all workers if present; store count in memory
- Restart the coordinator (to kick off the entrypoint and any bootstraps again)
- Provision workers if count stored in memory (will fetch fresh data from the
  coordinator)

Remove a module:

- *Note: This one is way more complicated and arguably provides less value*
- Remove all workers if present
- Remove all containers linked to the module (except the coordinator)
- Maybe (?) run bootstrap *uninstallers* per module
- Restart the coordinator (to kick off the entrypoint again)
- Remove the module from the coordinator

## Standardize Components Across Library

By components, I mean things like:

- Users
- Groups
- Roles
- Passwords

## Wiki Updates: Bootstrap Blip

There are two methods of bootstrap execution:

1. Mount bootstrap scripts directly to the coordinator container. Requires
   `before_start()` and `after_start()` functions to be defined in the bootstrap
   script. Can be mounted to a module directory or the parent directory. Module
   mounts allow for multiple scripts per module to be executed.
2. Legacy method: Use `MINITRINO_BOOTSTRAP` environment variable to specify a
   bootstrap script to run after the container starts. This can be used to run
   scripts on the coordinator or any other container. All bootstraps defined
   this way execute in parallel. These scripts also assume that whatever service
   they're operating on is started, and may rely on health checks to determine
   when the service is ready.
  
Note that bootstrap scripts must be idempotent.
