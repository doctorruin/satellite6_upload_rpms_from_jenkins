# !/usr/bin/python
import argparse
import json
import time
from datetime import date

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


def post_sat6(url, user, passw, headers, data):
    """
     Performs a POST and passes the data to the URL location
    :param url: SAT6 endpoint
    :param user: username
    :param passw: password
    :param headers: POST headers
    :param data: any data params needed
    :return: json of request
    """
    # uncomment for debugging purposes
    # print("POST Headers: %s" % headers)
    try:
        results = requests.post(
            url,
            data=data,
            auth=(user, passw),
            verify=True,
            headers=headers,
        ).json()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    if results.get('error'):
        print ("Error: %s" % results['error']['message'])
        exit(0)

    return results


def get_cv_params(content_view_api, user, passw, headers, content_view):
    """
    Get the content view parameters, specifically the ID and environments to promote to
    :param content_view_api: url for the content view endpoint
    :param user: API username
    :param passw: API password
    :param headers: API headers
    :param content_view: content view name
    :return: python list including id and environments object
    """

    print("Getting content view information for " + content_view)
    results = []
    data = json.dumps({"search": content_view})
    sat6_results = get_sat6(content_view_api, user, passw, headers, data)
    api_results = sat6_results.get('results')
    results.append(api_results[0]['id'])
    results.append(api_results[0]['environments'])

    print("get_cv_params results returned: " + str(results))

    return results


def publish_content_view(content_view_api, user, passw, headers, data, cv_id):
    """
    Publish the content view
    :param content_view_api: url for the content view endpoint
    :param user: API username
    :param passw: API password
    :param headers: API headers
    :param data: data object to query the API
    :param cv_id: the content view ID
    :return: the content_view version being published
    """

    publish_api = content_view_api + '/' + str(cv_id) + '/publish'

    results = post_sat6(publish_api, user, passw, headers, data)
    version_id = results['content_view_version_id']
    print("publish_content_view version id returned: " + str(version_id))

    print("Checking status before promoting to lifecycle environments")
    check_publish_status(content_view_api, user, passw, headers)

    return version_id


def check_publish_status(content_view_api, user, passw, headers):
    """
    Check the status of the content view being published
    :param content_view_api: url for the content view endpoint
    :param user: API username
    :param passw: API password
    :param headers: API headers
    :return: status of the publish
    """

    done = False
    while not done:
        results = get_sat6(content_view_api, user, passw, headers)
        status = results['last_event']['status']
        print("Publish status is: " + status)
        if status == "success":
            done = True
        else:
            print("Publish is still pending...")
            time.sleep(1)

    print("Ready to promote...")
    return


def promote_envs(promote_api, user, passw, headers, envs, today):
    """
    Promote the published content view to the environments
    :param promote_api:
    :param user: API username
    :param passw: API password
    :param headers: API headers
    :param envs: environments
    :param today: today's date
    :return:
    """

    print("Beginning promotion to lifecycle environments...")
    for env in envs:
        env_name = env['name']
        env_id = env['id']
        if not env_name == "Library":
            data = json.dumps({"environment_id": env_id,
                               "description": today + "Jenkins promote to " + env_name})
            print("promoting to: " + env_name)
            post_sat6(promote_api, user, passw, headers, data)
            print("promotion successful!")

    return


def execute_publish_promote(server, user, passw, content_views, default_envs, non_default_envs):
    """
    Method that executes publish and promotion of content views
    :param server: Satellite 6 server hostname to create URL endpoints
    :param user: API username
    :param passw: API password
    :param content_views: list of content views
    :param default_envs: boolean to use all associated environments to promote a content view to
    :param non_default_envs: list of specific environments to promote to
    """

    headers = {
        "Accept": "application/json,version=2",
        "Content-Type": "application/json"
    }

    sat6_api = 'https://' + server + '/katello/api/'
    content_view_api = sat6_api + 'content_views'

    today = str(date.today())

    content_view_information = []
    for content_view in content_views:
        print("Getting Content View ID and Environments.")
        cv_return = get_cv_params(content_view_api, user, passw, headers, content_view)
        print("Content view " + content_view + " id: " + cv_return[0])
        content_view_information.append(cv_return)

    for cv in content_view_information:
        print("Beginning publish for " + str(cv[0][0]))
        cv_id = cv[0][0]
        envs = cv[0][1]

        description = today + " Jenkins Publish"
        publish_data = json.dumps({"description": description})
        version_id = publish_content_view(content_view_api, user, passw, headers, publish_data, cv_id)

        promote_api = sat6_api + 'content_view_versions/' + str(version_id)
        if default_envs:
            promote_envs(promote_api, user, passw, headers, envs, today)
        else:
            promote_envs(promote_api, user, passw, headers, non_default_envs, today)

    print("Completed publish and promote!")
    exit(0)


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
    parser.add_argument('-a', '--all', dest='default_envs', required=False, default=False, action='store_true',
                        help='Promotes to lifecycle environments associated with the Content View.')
    parser.add_argument('-l', dest='non_default_envs', required=False, action='append',
                        help='Specify lifecycle environments by name. Must be in order of precedence, space delimited'
                             'ex. -e dev -e stage')

    args = parser.parse_args()

    execute_publish_promote(args.server, args.user, args.passw, args.cont_view, args.default_envs,
                            args.non_default_envs)


if __name__ == "__main__":
    main()
