# python3.6 -m pip install GitPython

import os
import re
import git
import time
import subprocess
from git import RemoteProgress

TEST_DIR = '/tmp/testing'

GIT_URLS = [
    # git@github.com:torvalds/linux.git
    'git@github.com:pockethub/PocketHub.git',
    # 'git@github.com:cstamas/nexus-core-ng.git',
    'git@github.com:apache/maven.git',
    'git@github.com:apache/wicket.git',
    'git@github.com:netty/netty.git',
    'git@github.com:tensorflow/tensorflow.git',
    'git@github.com:angular/angular.js.git',
    'git@github.com:twbs/bootstrap.git'
]


class CustomProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            percent = cur_count / max_count
            print("{0:50}\t{1:.2%}".format(message, percent), end='\r')
            if op_code & RemoteProgress.END == RemoteProgress.END:
                print('')


def git_url_to_path(base_dir, git_url):
    repo_name = re.findall('/(.+?)\.git', git_url)[0]
    repo_path = os.path.join(base_dir, repo_name)
    return repo_path


def setup_testing_repos():
    os.makedirs(TEST_DIR, exist_ok=True)
    for git_url in GIT_URLS:
        repo_path = git_url_to_path(TEST_DIR, git_url)

        if not os.path.isdir(repo_path):
            print('Clone {0} into {1}'.format(git_url, repo_path))
            git.Repo.clone_from(git_url, repo_path, progress=CustomProgress())
        else:
            print('Nothing to-do for {0}'.format(git_url))


def setup_maven_benchmark_pom(tmp_dir_name):
    with open(os.path.join(tmp_dir_name, "pom.xml"), 'w') as mvn_pom:
        mvn_pom.write('''<?xml version="1.0" encoding="UTF-8"?>
            <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
                <modelVersion>4.0.0</modelVersion>
                <parent>
                    <groupId>org.sonatype.oss</groupId>
                    <artifactId>oss-parent</artifactId>
                    <version>9</version>
                </parent>
            
                <artifactId>naive-performance-test</artifactId>
                <version>0.0.3-SNAPSHOT</version>
            
                <properties>
                    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
                    <project.reporting.outputEncoding>UTF-8</project.reporting.outputEncoding>
                    <git-commit-id-version>3.0.0-SNAPSHOT</git-commit-id-version>
                    <git-use-native>false</git-use-native>
                </properties>
            
                <build>
                    <plugins>
                        <plugin>
                            <groupId>pl.project13.maven</groupId>
                            <artifactId>git-commit-id-plugin</artifactId>
                            <version>${git-commit-id-version}</version>
                            <executions>
                                <execution>
                                    <id>get-the-git-infos</id>
                                    <goals>
                                        <goal>revision</goal>
                                    </goals>
                                    <phase>initialize</phase>
                                </execution>
                            </executions>
                            <configuration>
                                <prefix>git</prefix>
                                <verbose>true</verbose>
                                <useNativeGit>${git-use-native}</useNativeGit>
                                <skipPoms>false</skipPoms>
                                <!-- <nativeGitTimeoutInMs>3000</nativeGitTimeoutInMs> -->
                                <dotGitDirectory>${project.basedir}/.git</dotGitDirectory>
                                <generateGitPropertiesFile>true</generateGitPropertiesFile>
                                <evaluateOnCommit>HEAD</evaluateOnCommit>
                                <generateGitPropertiesFilename>${project.build.outputDirectory}/git.properties</generateGitPropertiesFilename>
                                <!--
                                <includeOnlyProperties>
                                    <includeOnlyProperty>^git.commit.id$</includeOnlyProperty>
                                </includeOnlyProperties>
                                -->
                                <excludeProperties>
                                    <excludeProperty>^git.local.branch.*$</excludeProperty>
                                </excludeProperties>
                            </configuration>
                        </plugin>
                        <!--
                        <plugin>
                            <artifactId>maven-antrun-plugin</artifactId>
                            <version>1.8</version>
                            <executions>
                                <execution>
                                    <id>echo-properties</id>
                                    <phase>initialize</phase>
                                    <goals>
                                        <goal>run</goal>
                                    </goals>
                                    <configuration>
                                        <target>
                                            <echo>git-evaluation-dir: ${git-evaluation-dir}</echo>
                                            <echo>git-use-native: ${git-use-native}</echo>
                                        </target>
                                    </configuration>
                                </execution>
                            </executions>
                        </plugin>
                        -->
                    </plugins>
                </build>
            </project>''')


def run_process(args, cwd):
    # print("start process: " + str(' '.join(args)))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        raise ValueError('Process failed with exit-code {0}.\nOutput: {1}'.format(proc.returncode, stdout))

    return stdout


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


setup_testing_repos()

for git_url in GIT_URLS:
    repo_path = git_url_to_path(TEST_DIR, git_url)
    actual_git_repo = os.path.join(repo_path, '.git')

    commit_count = run_process(['git', 'rev-list', '--all', '--count'], cwd=repo_path)
    commit_count = re.search(r'\d+', str(commit_count)).group()

    print(f"=== Run test for {repo_path} (commit count: {commit_count})")
    setup_maven_benchmark_pom(repo_path)

    for use_native_git in [True, False]:
        for git_commit_id_plugin_version in ['2.2.6', '3.0.0-SNAPSHOT']:
            max_attempts = 10
            execution_times = []
            for attempt in range(1, max_attempts + 1):
                print(f"Launching {attempt} / {max_attempts} for {git_commit_id_plugin_version},{use_native_git}",
                      end='\r', flush=True)
                start = time.time()
                run_process(
                    ['mvn',
                     'pl.project13.maven:git-commit-id-plugin:' + str(git_commit_id_plugin_version) + ':revision',
                     '-Dgit-use-native=' + str(use_native_git).lower()],
                    cwd=repo_path)

                total_time = time.time() - start
                execution_times.append(total_time)
            avg_execution_time = mean(execution_times)
            print(f"\"{git_commit_id_plugin_version}\",\"{use_native_git}\",\"{avg_execution_time:.2f}\"{100*' '}")
