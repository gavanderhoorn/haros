
#Copyright (c) 2016 Andre Santos
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

###############################################################################
# Imports
###############################################################################

import json
import logging
import os


###############################################################################
# Utility
###############################################################################

class LoggingObject(object):
    log = logging.getLogger(__name__)


################################################################################
# Export Manager
################################################################################

class JsonExporter(LoggingObject):
    def export_projects(self, datadir, projects, overwrite = True):
        self.log.info("Exporting project data.")
        out = os.path.join(datadir, "projects.json")
        if not overwrite and os.path.isfile(out):
            with open(out, "r") as f:
                data = json.load(f)
            for p in projects:
                is_new = True
                for i in xrange(len(data)):
                    if data[i]["id"] == p.id:
                        is_new = False
                        data[i] = p.to_JSON_object()
                        break
                if is_new:
                    data.append(p.to_JSON_object())
        else:
            data = [p.to_JSON_object() for p in projects]
        with open(out, "w") as f:
            self.log.debug("Writing to %s", out)
            json.dump(data, f)

    def export_packages(self, datadir, packages):
        self.log.info("Exporting package data.")
        self._export_collection(datadir, packages, "packages.json")

    def export_rules(self, datadir, rules):
        self.log.info("Exporting analysis rules.")
        self._export_collection(datadir, rules, "rules.json")

    def export_metrics(self, datadir, metrics):
        self.log.info("Exporting analysis metrics.")
        self._export_collection(datadir, metrics, "metrics.json")

    def export_violations(self, datadir, pkg_reports):
        self.log.info("Exporting reported rule violations.")
        if isinstance(pkg_reports, dict):
            pkg_reports = pkg_reports.viewvalues()
        for report in pkg_reports:
            out = os.path.join(datadir, report.package.name + ".json")
            data = [v.to_JSON_object() for v in report.violations]
            for fa in report.file_analysis:
                data.extend(v.to_JSON_object() for v in fa.violations)
            with open(out, "w") as f:
                self.log.debug("Writing to %s", out)
                json.dump(data, f)

    def export_measurements(self, datadir, pkg_reports):
        self.log.info("Exporting metrics measurements.")
        if isinstance(pkg_reports, dict):
            pkg_reports = pkg_reports.viewvalues()
        for report in pkg_reports:
            out = os.path.join(datadir, report.package.name + ".json")
            data = [m.to_JSON_object() for m in report.metrics]
            for fa in report.file_analysis:
                data.extend(m.to_JSON_object() for m in fa.metrics)
            with open(out, "w") as f:
                self.log.debug("Writing to %s", out)
                json.dump(data, f)

    def export_configurations(self, datadir, configs):
        self.log.info("Exporting launch configurations.")
        self._export_collection(datadir, configs, "configurations.json")

    def export_summary(self, datadir, report, past):
        self.log.info("Exporting analysis summary.")
        out = os.path.join(datadir, "summary.json")
        data = report.to_JSON_object()
        data["history"] = {
            "timestamps": [r.timestamp for r in past],
            "lines_of_code": [r.statistics.lines_of_code for r in past],
            "comments": [r.statistics.comment_lines for r in past],
            "issues": [r.statistics.issue_count for r in past],
            "standards": [r.statistics.standard_issue_count for r in past],
            "metrics": [r.statistics.metrics_issue_count for r in past],
            "complexity": [r.statistics.avg_complexity for r in past],
            "function_length": [r.statistics.avg_function_length for r in past]
        }
        stats = report.statistics
        data["history"]["timestamps"].append(report.timestamp)
        data["history"]["lines_of_code"].append(stats.lines_of_code)
        data["history"]["comments"].append(stats.comment_lines)
        data["history"]["issues"].append(stats.issue_count)
        data["history"]["standards"].append(stats.standard_issue_count)
        data["history"]["metrics"].append(stats.metrics_issue_count)
        data["history"]["complexity"].append(stats.avg_complexity)
        data["history"]["function_length"].append(stats.avg_function_length)
        with open(out, "w") as f:
            self.log.debug("Writing to %s", out)
            json.dump(data, f)

    def _export_collection(self, datadir, items, filename):
        out = os.path.join(datadir, filename)
        if isinstance(items, dict):
            items = items.viewvalues()
        with open(out, "w") as f:
            self.log.debug("Writing to %s", out)
            json.dump([item.to_JSON_object() for item in items], f)
