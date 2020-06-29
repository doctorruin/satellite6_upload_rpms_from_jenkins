# !/usr/bin/python
import argparse
import json
import os

import requests


def get_sat6(url, user, passw, headers, data=None):
    """
    GET param against SAT6 API
    :param url: SAT6 endpoint
    :param user: username
    :param passw: password
    :param headers: get headers
    :param data: data parameter
    :return: json response
    """

    if data is None:
        data = {}
    try:
        results = requests.get(
            url,
            auth=(user, passw),
            headers=headers,
            data=data,
            verify=True
        ).json()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    if results.get('error'):
        print("Error: %s" % results['error']['message'])
        exit(0)

    return results


def execute_publish_promote(server, user, passw, content_views, def_env=False, specific_envs=None):

    headers = {
        "Accept": "application/json,version=2",
        "Content-Type": "application/json"
    }

    sat6_api = 'https://' + server + '/katello/api/'

    content_view_api = sat6_api + 'content_views'

    content_view_ids = []
    envs = None
    for content_view in content_views:
        data = json.dumps({"search": content_view})
        results = get_sat6(content_view_api, user, passw, headers, data)
        cv_id = results.get(results[0]["id"])
        envs = results.get(results[0]["environments"])
        content_view_ids.append(cv_id)

    for e in envs:
        print(e)

    print(content_view_ids)


def main():
    """
    Get Args and run API
    """

    parser = argparse.ArgumentParser(description='Publish and Promote content views'
                                                 'Specific API documentation can be found at:'
                                                 'https://theforeman.org/plugins/katello/3.5/api/apidoc/v2.html'
                                                 'COntent_Views utilizes the Katello API Specifically')

    parser.add_argument('-s', '--server', dest='server', required=True,
                        help='server name of SAT 6')
    parser.add_argument('-u', '--user', dest='user', required=True,
                        help='USERNAME for API')
    parser.add_argument('-p', '--password', dest='passw', required=True,
                        help='PASSWORD for USERNAME')
    parser.add_argument('-c', '--cont-view', dest='cont_view', required=True, action='append',
                        help='Content Views to publish. Can be set multiple times. Must be in order of precedence,'
                             ' space delimited.'
                             'ex. -c iarc-splunk -c iarc-composite-splunk')
    parser.add_argument('-a', '--all', dest='default_environments', required=False, default=False, action='store_true',
                        help='Promotes to lifecycle environments associated with the Content View.')
    parser.add_argument('-l', dest='non_default_envs', required=False, action='append',
                        help='Specify lifecycle environments by name. Must be in order of precedence, space delimited'
                             'ex. -e dev -e stage')

    args = parser.parse_args()

    execute_publish_promote(args.server, args.user, args.passw, args.cont_view, args.default_environments, args.non_default_envs)


if __name__ == "__main__":
    main()
