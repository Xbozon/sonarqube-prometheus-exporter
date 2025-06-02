import requests
import logging
from config import Config

# Web API Documentation: http://your-sonarqube-url/web_api

CONF = Config()

class SonarExporter:

    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.base_url = CONF.sonar_url
        self.request_timeout = CONF.request_timeout

    def _request(self, endpoint):
        try:
            req = requests.get("{}/{}".format(self.base_url, endpoint),
                               auth=(self.user, self.password),
                               timeout=self.request_timeout)
            req.raise_for_status()
            return req.json()
        except Exception as e:
            logging.exception("Timeout during request to endpoint '%s': %s", endpoint, e)
            raise

    def get_all_projects(self):
        return self._request(endpoint='api/components/search_projects?filter=tags=sonarqube-exporter')

    def get_measures_component(self, component_key, metric_key):
        return self._request(endpoint="api/measures/component?component={}&metricKeys={}".format(component_key, metric_key))

class Project:

    def __init__(self, identifier, key):
        self.id = identifier
        self.key = key
        self._metrics = None
        self._name = None
        self._organization = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, value):
        self._metrics = value

    @property
    def organization(self):
        return self._organization

    @organization.setter
    def organization(self, value):
        self._organization = value

    def organize_measures(self, metrics: list):
        metric_obj_list = []
        for measure in self.metrics['component']['measures']:
            if 'metric' in measure:
                m = Metric()
                # Set basic properties from our defined metrics
                for metric_obj in metrics:
                    if metric_obj.key == measure['metric']:
                        m.key = metric_obj.key
                        m.description = metric_obj.description
                        m.domain = metric_obj.domain
                # Convert measure data into tuple format
                tuple_list = []
                for met_tuple in self.transform_object_in_list_tuple(measure):
                    if met_tuple[0] == 'metric':
                        m.key = met_tuple[1]
                    else:
                        tuple_list.append(met_tuple)
                m.values = tuple_list
                metric_obj_list.append(m)
        self.metrics = metric_obj_list

    def transform_object_in_list_tuple(self, metric_object):
        object_list_tuples = []
        for item in metric_object:
            if isinstance(metric_object[item], list):
                for obj in metric_object[item]:
                    object_list_tuples.extend(self.transform_object_in_list_tuple(metric_object=obj))
            else:
                obj_tuple = (str(item), str(metric_object[item]))
                object_list_tuples.append(obj_tuple)
        return object_list_tuples


class Metric:

    def __init__(self):
        self._key = None
        self._values = []
        self._description = None
        self._domain = None

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values.extend(value)

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, value):
        self._domain = value


def get_all_projects_with_metrics():
    projects = []
    client = SonarExporter(CONF.sonar_user, CONF.sonar_password)
    all_projects = client.get_all_projects()

    metrics_keys = "code_smells,bugs,vulnerabilities,coverage,ncloc"

    metrics = []
    for key, description in [("code_smells", "Code Smells"),
                             ("bugs", "Bugs"),
                             ("vulnerabilities", "Vulnerabilities"),
                             ("coverage", "Coverage"),
                             ("ncloc", "Lines of Code")]:
        m = Metric()
        m.key = key
        m.description = description
        metrics.append(m)

    for project in all_projects['components']:
        p = Project(identifier=project['key'], key=project['key'])
        p.name = project['name']
        p.metrics = client.get_measures_component(component_key=p.key, metric_key=metrics_keys)
        p.organize_measures(metrics)
        projects.append(p)

    return projects
