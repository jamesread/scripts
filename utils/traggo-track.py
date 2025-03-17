#!/usr/bin/env python3

import requests
import json
import datetime

import configargparse

parser = configargparse.ArgParser(default_config_files=['~/.config/traggo-track.yaml'])
parser.add('--api_key', default = "", required = True)
parser.add('--api_url', default = "", required = True)
parser.add('tags', nargs = "*")
args = parser.parse_args()

def build_tags(raw):
    ret = []

    print(raw)

    for tag in raw:
        print("tag", tag)

        k, v = tag.split(":")
        ret.append({"key": k, "value": v})

    return ret

headers = {
    "Content-Type": "application/json",
    "Authorization": f"traggo {args.api_key}"
}

# Example GraphQL query
query = """
mutation StartTimer($start: Time!, $tags: [InputTimeSpanTag!], $note: String!) {
    createTimeSpan(start: $start, tags: $tags, note: $note) {
        id    start    end    tags {      key      value      __typename    }    oldStart    note    __typename  
    }
}
"""

now = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")

# Variables for the query (if needed)
variables = {
    "start": now,
    "note": "created by foo.py",
    "tags": build_tags(args.tags),
}

# Prepare the request payload
payload = {
    "query": query,
    "variables": variables,
    "operationName": "StartTimer"
}

def make_traggo_request():
    """Make a GraphQL request and return the response."""
    try:
        response = requests.post(
            args.api_url,
            headers=headers,
            data=json.dumps(payload)
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse and return the JSON response
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(response.text)
        print(f"A req error occurred: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"JSON decode error: {json_err}")
        print(f"Response content: {response.text}")
    
    return None

if __name__ == "__main__":
    # Make the request
    result = make_traggo_request()
    
    # Print the result
    if result:
        print(json.dumps(result, indent=2))

