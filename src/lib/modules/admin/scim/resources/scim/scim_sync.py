"""Sync users and groups to a SCIM /v2 endpoint using requests."""

import logging
import os
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CLUSTER_NAME = os.environ.get("CLUSTER_NAME")
SCIM_BASE_URL = f"http://minitrino-{CLUSTER_NAME}:8080/scim/v2"
SCIM_TOKEN = os.environ.get("SCIM_TOKEN", "changeme")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "60"))
GROUP_MAPPING = {
    "clusteradmins": ["admin", "cachesvc", "test"],
    "metadata-users": ["metadata-user", "bob", "test"],
    "platform-users": ["platform-user", "alice", "test"],
}

HEADERS = {
    "Authorization": f"Bearer {SCIM_TOKEN}",
    "Content-Type": "application/scim+json",
    "Accept": "application/scim+json",
}


def get_user(username):
    """Get a user from SCIM by username."""
    resp = requests.get(
        f"{SCIM_BASE_URL}/Users",
        headers=HEADERS,
        params={"filter": f'userName eq "{username}"'},
        timeout=10,
    )
    resp.raise_for_status()
    resources = resp.json().get("Resources", [])
    return resources[0] if resources else None


def create_user(username):
    """Create a user in SCIM."""
    data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": username,
    }
    resp = requests.post(
        f"{SCIM_BASE_URL}/Users", headers=HEADERS, json=data, timeout=10
    )
    resp.raise_for_status()
    logging.info(f"Created user: {username}")
    return resp.json()


def ensure_user(username):
    """Ensure a user exists in SCIM."""
    user = get_user(username)
    if user:
        return user
    try:
        return create_user(username)
    except Exception as e:
        logging.error(f"Error creating user {username}: {e}")
        return None


def get_group(groupname):
    """Get a group from SCIM by displayName."""
    resp = requests.get(
        f"{SCIM_BASE_URL}/Groups",
        headers=HEADERS,
        params={"filter": f'displayName eq "{groupname}"'},
        timeout=10,
    )
    resp.raise_for_status()
    resources = resp.json().get("Resources", [])
    return resources[0] if resources else None


def create_group(groupname):
    """Create a group in SCIM."""
    data = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": groupname,
    }
    resp = requests.post(
        f"{SCIM_BASE_URL}/Groups", headers=HEADERS, json=data, timeout=10
    )
    resp.raise_for_status()
    logging.info(f"Created group: {groupname}")
    return resp.json()


def ensure_group(groupname):
    """Ensure a group exists in SCIM."""
    group = get_group(groupname)
    if group:
        return group
    try:
        return create_group(groupname)
    except Exception as e:
        logging.error(f"Error creating group {groupname}: {e}")
        return None


def update_group_members(group, user_objs):
    """Update group membership in SCIM."""
    user_ids = {u["id"] for u in user_objs if u}
    current_members = {m["value"] for m in group.get("members", []) if "value" in m}
    if user_ids == current_members:
        return
    new_members = [{"value": uid} for uid in user_ids]
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "members", "value": new_members}],
    }
    group_id = group["id"]
    try:
        resp = requests.patch(
            f"{SCIM_BASE_URL}/Groups/{group_id}",
            headers=HEADERS,
            json=patch_data,
            timeout=10,
        )
        resp.raise_for_status()
        logging.info(f"Updated members for group {group['displayName']}: {new_members}")
    except Exception as e:
        logging.error(f"Error updating group {group['displayName']}: {e}")


def main():
    """Sync users and groups to a scim/v2 server endpoint."""
    while True:
        try:
            for group, users in GROUP_MAPPING.items():
                group_obj = ensure_group(group)
                user_objs = [ensure_user(u) for u in users]
                if group_obj and all(user_objs):
                    update_group_members(group_obj, user_objs)
            logging.info(f"Sync complete. Sleeping {SYNC_INTERVAL}s...")
        except Exception as e:
            logging.error(f"Unexpected error in sync loop: {e}", exc_info=True)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
