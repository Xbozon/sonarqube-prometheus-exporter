import time
import threading
import logging
from prometheus_client.core import GaugeMetricFamily
import prometheus_client as prom
from sonarqube_exporter import get_all_projects_with_metrics

class CustomSonarExporter:
    def __init__(self, update_interval=60):
        """
        Initializes the exporter.
        :param update_interval: How often (in seconds) to update the cache from the SonarQube API.
        """
        self.cached_projects = []
        self.lock = threading.Lock()
        self.update_interval = update_interval

        thread = threading.Thread(target=self.update_cache, daemon=True)
        thread.start()

    def update_cache(self):
        """Background loop that periodically updates the cache."""
        while True:
            try:
                projects = get_all_projects_with_metrics()
                with self.lock:
                    self.cached_projects = projects
                logging.info("Successfully updated SonarQube metrics cache.")
            except Exception as e:
                logging.exception("Error updating SonarQube metrics cache: %s", e)
            time.sleep(self.update_interval)

    def collect(self):
        """
        Called by Prometheus to collect metrics.
        Uses the cached projects data.
        """
        with self.lock:
            projects = list(self.cached_projects)  # Shallow copy of the cache

        if not projects:
            try:
                projects = get_all_projects_with_metrics()
            except Exception as e:
                logging.exception("Error fetching SonarQube metrics directly: %s", e)
                return

        for project in projects:
            for metric in project.metrics:
                label_list = ['id', 'key', 'name']
                label_values = [project.id, project.key, project.name]
                value_to_set = None

                # Process each metric's values.
                for metric_value in metric.values:
                    if metric_value[0] == 'value':
                        value_to_set = metric_value[1]
                    else:
                        label_list.append(metric_value[0])
                        label_values.append(metric_value[1])

                gauge = GaugeMetricFamily(
                    name="sonar_{}".format(metric.key),
                    documentation=metric.description,
                    labels=label_list
                )
                gauge.add_metric(labels=label_values, value=value_to_set)
                yield gauge

if __name__ == "__main__":
    logging.info("Starting service on port 9120.")
    logging.basicConfig(level=logging.INFO)

    custom_exporter = CustomSonarExporter(update_interval=60)  # Update cache every 60 seconds.
    prom.REGISTRY.register(custom_exporter)
    prom.start_http_server(9120)
    logging.info("SonarQube exporter is running on port 9120.")

    # Keep 
    while True:
        time.sleep(2)
