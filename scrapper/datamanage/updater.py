from core import rule, repo, package, people
from sourcemanage import clone_repos as crep, source_finder as sf

import extractor
import db_manager as dbm

import os
import yaml

class DbUpdater:
    def __init__(self):
        self.root = os.path.join(os.path.expanduser("~"), "ros", "repos")
        self.repos      = []    # list of lists, atm
        self.packages   = {}    # string -> Package
        self.sources    = {}    # string -> SourceFile
        self.people     = None
        self.licenses   = None
        self.issues     = None
        self.labels     = None
        self.git_users  = None
        self.metrics    = None
        self.rules      = None
        self.tags       = None
        self.rule_tags  = None
        self.issues_labels  = None
        self.source_dirty   = False
        self.meta_dirty     = False
        self.metrics_dirty  = False
        self.rules_dirty    = False


    def updateSource(self, dist, dist_filter = None, network = True):
        self.source_dirty = True
        repos = repo.get_repos_from_dist(dist, dist_filter)
        if network:
            print "[Network] Cloning repositories to:", self.root, "(this may take a while)."
            crep.clone_repos(repos, self.root)
            print "[Network] Querying repository information (this may take a while)."
            repo_keys = [["owner", "type"], "created_at", "updated_at",
                    "pushed_at", "size", "forks_count", "watchers_count",
                    "subscribers_count"]
            repo_names = set()
            for r in repos.values():
                for n in r.repo_names:
                    repo_names.add(n)
            self.repos = extractor.getRepoInfo(repo_names, repo_keys)
        else:
            self.repos = []
            i = 1
            for r in repos.values():
                self.repos.append([i, r.name, None, None, None, None,
                        None, None, None, None])
                i += 1
        self.packages = package.get_packages_from_repos(self.root, repos)
        self.sources = sf.find_source_files(self.root, self.packages)

        i = 1
        for p in self.packages.values():
            p.id = i
            i += 1
        i = 1
        for ss in self.sources.values():
            for s in ss:
                s.id = i
                i += 1


    def updateMetadata(self, network = True):
        self.meta_dirty = True
        pkgs = self.packages.values()
        mntnrs = reduce(set.union, [p.maintainers.people for p in pkgs])
        authors = reduce(set.union, [p.authors.people for p in pkgs])
        self.people = mntnrs.union(authors)
        self.licenses = reduce(set.union, [p.licenses for p in pkgs])
        self.licenses = [p for p in enumerate(self.licenses, start = 1)]
        if network:
            issues_keys = [["user", "login"], ["assignee", "login"],
                    "created_at", "closed_at", ["labels", "name"]]
            repo_ids = [(r[0], r[1]) for r in self.repos]
            print "[Network] Fetching Git issues (this may take a while)."
            issues_info = extractor.getIssuesLinkRepos(repo_ids, issues_keys)
            issue_cols = ["id", "created_by", "assigned_to", "created_at",
                    "closed_at", "labels", "repository_id"]
            (issue_cols, issues_info, label_ids,
                issues_labels) = extractor.getIssuesLabels(issue_cols,
                        issues_info)
            self.issues = issues_info
            self.labels = label_ids
            self.issues_labels = issues_labels
            print "[Network] Fetching e-mails for Git users (this may take a while)."
            git_names = set([i[1] for i in issues_info])
            self.git_users = extractor.getGitEmails(git_names)

        i = 1
        for p in self.people:
            p.id = i
            i += 1


    def updateMetrics(self, metrics_file):
        self.metrics_dirty = True
        with open(metrics_file, "r") as mf:
            self.metrics = yaml.load(mf)
            self.metrics = [(ind + 1, m["name"], m["description"])
                    for ind, m in enumerate(self.metrics)]


    def updateRules(self, rule_file):
        self.rules_dirty = True
        rules = rule.load_rules_from_file(rule_file)
        (self.rules, self.tags, self.rule_tags) = rule.extract_rules_and_tags(rules)


    def commit(self, truncate = True):
        db = dbm.DbManager()
        db.connect("dbuser.txt")
        self._truncateRelationships(db)
        if self.source_dirty:
            self._commitSource(db)
        if self.meta_dirty:
            self._commitMetadata(db)
        if self.metrics_dirty:
            # Metrics
            self._commitMetrics(db)
        if self.rules_dirty:
            # Rules
            self._commitRules(db)
        self._commitRelationships(db)
        db.disconnect()
        self._resetState()


    def _commitSource(self, db):
        pkg_info = [p.asTuple() for p in self.packages.values()]
        db.updateTable("Packages", ["id", "name", "metapackage",
                "description", "wiki", "git", "branch", "path"],
                ["MEDIUMINT(9)", "VARCHAR(100)", "TINYINT(1)", "VARCHAR(2000)",
                "VARCHAR(100)", "VARCHAR(100)", "VARCHAR(50)", "VARCHAR(200)"],
                pkg_info, pk="id")

        db.updateTable("Repositories", ["id", "name", "owner_type", "created_at",
                "updated_at", "pushed_at", "size", "forks_count",
                "watchers_count", "subscribers_count"],
                ["MEDIUMINT(9)", "VARCHAR(60)", "VARCHAR(30)", "CHAR(10)",
                "CHAR(10)", "CHAR(10)", "MEDIUMINT(9)", "SMALLINT(6)",
                "SMALLINT(6)", "SMALLINT(6)"], self.repos, pk="id")

        pkg_ids = [(p.id, p.name) for p in self.packages.values()]
        src_info = extractor.getPkgFiles(pkg_ids, self.sources)
        db.updateTable("Files", ["id", "package_id", "name", "path"],
                ["MEDIUMINT(9)", "MEDIUMINT(9)", "VARCHAR(50)", "VARCHAR(200)"],
                src_info, pk="id", fk=["package_id"], fk_ref=["Packages(id)"])

        dep_type_ids = [(1, "buildtool_depend"), (2, "build_depend"),
                (3, "run_depend")]
        db.updateTable("Package_Dependency_Types", ["id", "dependency_type"],
                ["SMALLINT(6)", "VARCHAR(16)"], dep_type_ids, pk="id")

        dep_cols = ["package_id", "dependency_id", "type_id"]
        pkg_deps = extractor.mapPkgDeps(pkg_ids, dep_type_ids, self.packages)
        db.updateTable("Package_Dependencies", dep_cols,
                ["MEDIUMINT(9)", "MEDIUMINT(9)", "SMALLINT(6)"], pkg_deps,
                pk="package_id, dependency_id, type_id", fk=dep_cols,
                fk_ref=["Packages(id)", "Packages(id)", "Package_Dependency_Types(id)"])

        repo_ids = [(r[0], r[1]) for r in self.repos]
        pkg_repos = extractor.mapPkgRepos(pkg_ids, repo_ids, self.packages)
        pr_cols = ["package_id", "repository_id"]
        db.updateTable("Repository_Packages", pr_cols,
                ["MEDIUMINT(9)", "MEDIUMINT(9)"], pkg_repos,
			    pk = "package_id, repository_id", fk = pr_cols,
			    fk_ref = ["Packages(id)", "Repositories(id)"])


    def _commitMetadata(self, db):
        ppl_info = [p.asTuple() for p in self.people]
        db.updateTable("People", ["id", "name", "email"],
                ["SMALLINT(6)", "VARCHAR(150)", "VARCHAR(50)"],
                ppl_info, pk="id")

        db.updateTable("Licenses", ["id", "name"],
                ["SMALLINT(6)", "VARCHAR(150)"], self.licenses, pk="id")

        db.updateTable("Issues", ["id", "created_by", "assigned_to",
                "created_at", "closed_at", "repository_id"],
                ["MEDIUMINT(9)", "VARCHAR(50)", "VARCHAR(50)",
                "CHAR(10)", "CHAR(10)", "MEDIUMINT(9)"], self.issues,
                pk="id", fk="repository_id", fk_ref="Repositories(id)")

        db.updateTable("Labels", ["id", "name"],
                ["SMALLINT(6)", "VARCHAR(50)"], self.labels, pk="id")

        il_cols = ["issue_id", "label_id"]
        db.updateTable("Issue_Labels", il_cols,
                ["MEDIUMINT(9)", "SMALLINT(6)"], self.issues_labels,
			    pk="issue_id, label_id", fk=il_cols,
			    fk_ref=["Issues(id)", "Labels(id)"])

        db.updateTable("Git_Users", ["id", "username", "email"],
                ["SMALLINT(6)", "VARCHAR(50)", "VARCHAR(50)"],
                self.git_users, pk="id")

        # Link the git users to the people from package manifests
        git_emails = [(u[0], u[2]) for u in self.git_users]
        ppl_emails = [(u[0], u[2]) for u in ppl_info]
        git_ppl = extractor.mapGitPpl(git_emails, ppl_emails)
        git_ppl_cols = ["id", "git_id", "person_id"]
        db.updateTable("Git_People", git_ppl_cols,
                ["SMALLINT(6)", "SMALLINT(6)", "SMALLINT(6)"], git_ppl, 
                pk="id", fk=git_ppl_cols[1:],
                fk_ref = ["Git_Users(id)", "People(id)"])


    def _commitMetrics(self, db):
        db.updateTable("Metrics", ["id", "name", "description"],
                ["SMALLINT(6)", "VARCHAR(50)", "VARCHAR(2000)"],
                self.metrics, pk="id")


    def _commitRules(self, db):
        db.updateTable("Tags", ["id", "name"], ["SMALLINT(6)", "VARCHAR(30)"],
                self.tags, pk="id")
        db.updateTable("Rules", ["id", "name", "scope", "description"],
                ["MEDIUMINT(9)", "VARCHAR(30)", "VARCHAR(10)", "VARCHAR(120)"],
                self.rules, pk="id")


    def _commitRelationships(self, db):
        if self.source_dirty and self.meta_dirty:
            pkg_ids = [(p.id, p.name) for p in self.packages.values()]

            pkg_licenses = extractor.mapPkgLicenses(pkg_ids,
                    self.licenses, self.packages)
            lic_cols = ["package_id", "lic_id"]
            db.updateTable("Package_Licenses", lic_cols,
                    ["MEDIUMINT(9)", "SMALLINT(6)"], pkg_licenses,
			         pk="package_id, lic_id", fk=lic_cols,
			         fk_ref=["Packages(id)", "Licenses(id)"])

            ppl_ids = [(p.id, p.name) for p in self.people]
            am_cols = ["package_id", "person_id"]
            am_col_t = ["MEDIUMINT(9)", "SMALLINT(6)"]
            am_fk_refs = ["Packages(id)", "People(id)"]
            pkg_authors, pkg_mntnrs = extractor.mapPkgAMs(pkg_ids,
                    ppl_ids, self.packages)
            db.updateTable("Package_Authors", am_cols, am_col_t, pkg_authors,
                    pk = "package_id, person_id", fk = am_cols, fk_ref = am_fk_refs)
            db.updateTable("Package_Maintainers", am_cols, am_col_t, pkg_mntnrs,
                    pk = "package_id, person_id", fk = am_cols, fk_ref = am_fk_refs)
        if self.source_dirty and self.metrics_dirty:
            db.updateTable("File_Metrics", ["file_id", "metric_id", "value"],
                    ["MEDIUMINT(9)", "SMALLINT(6)", "FLOAT"], None,
		            pk="file_id, metric_id", fk=["file_id", "metric_id"],
		            fk_ref=["Files(id)", "Metrics(id)"])
            db.updateTable("Package_Metrics", ["package_id", "metric_id", "value"],
                    ["MEDIUMINT(9)", "SMALLINT(6)", "FLOAT"], None,
		            pk="package_id, metric_id", fk=["package_id", "metric_id"],
		            fk_ref=["Packages(id)", "Metrics(id)"])
            db.updateTable("File_Class_Metrics",
                    ["file_id", "class_name", "line", "metric_id", "value"],
                    ["MEDIUMINT(9)", "VARCHAR(50)", "MEDIUMINT(9)",
                    "SMALLINT(6)", "FLOAT"], None,
		            pk="file_id, class_name, line, metric_id",
                    fk=["file_id", "metric_id"],
                    fk_ref=["Files(id)", "Metrics(id)"])
            db.updateTable("File_Function_Metrics",
                    ["file_id", "function_name", "line", "metric_id", "value"],
                    ["MEDIUMINT(9)", "VARCHAR(100)", "MEDIUMINT(9)",
                    "SMALLINT(6)", "FLOAT"], None,
		            pk="file_id, function_name, line, metric_id",
                    fk=["file_id", "metric_id"],
                    fk_ref=["Files(id)", "Metrics(id)"])
        if self.source_dirty and self.rules_dirty:
            db.updateTable("Non_Compliance",
                    ["id", "rule_id", "package_id", "file_id",
                        "line", "function", "comment"],
                    ["MEDIUMINT(9)", "MEDIUMINT(9)", "MEDIUMINT(9)",
                        "MEDIUMINT(9)", "MEDIUMINT(9)",
                        "VARCHAR(100)", "VARCHAR(250)"],
                    None, pk="id", fk=["rule_id", "package_id", "file_id"],
                    fk_ref=["Rules(id)", "Packages(id)", "Files(id)"])
        if self.rules_dirty:
            db.updateTable("Rule_Tags", ["rule_id", "tag_id"],
                    ["MEDIUMINT(9)", "SMALLINT(6)"],
                    self.rule_tags, pk="rule_id, tag_id",
                    fk=["rule_id", "tag_id"],
                    fk_ref=["Rules(id)", "Tags(id)"])


    def _truncateRelationships(self, db):
        tables = set()
        if self.source_dirty:
            tables.update(["Repository_Packages", "Package_Maintainers", "Package_Authors",
                    "Package_Licenses", "Package_Dependencies", "Package_Metrics",
                    "Non_Compliance", "File_Metrics",
                    "File_Class_Metrics", "File_Function_Metrics"])
        if self.meta_dirty:
            tables.update(["Git_People", "Issue_Labels", "Package_Authors",
                    "Package_Maintainers", "Package_Licenses"])
        if self.metrics_dirty:
            tables.update(["File_Metrics", "Package_Metrics",
                    "File_Class_Metrics", "File_Function_Metrics"])
        if self.rules_dirty:
            tables.update(["Non_Compliance", "Rule_Tags"])
        for table in tables:
            db.truncate(table)
        if self.source_dirty:
            db.truncate("Package_Dependency_Types")


    def _resetState(self):
        self.repos      = []    # list of lists, atm
        self.packages   = {}    # string -> Package
        self.sources    = {}    # string -> SourceFile
        self.people     = None
        self.licenses   = None
        self.issues     = None
        self.labels     = None
        self.git_users  = None
        self.metrics    = None
        self.rules      = None
        self.tags       = None
        self.rule_tags  = None
        self.issues_labels  = None
        self.source_dirty   = False
        self.meta_dirty     = False
        self.metrics_dirty  = False
        self.rules_dirty    = False
