# Contributing Guide

This repository contains materials related to the Roman Data Monitoring Tool (RDMT) Spire, the component of the RDMT that monitors science and guide window data. This tool is a best-effort project developed by the Roman Telescope Branch of the Space Telescope Science Institute (STScI) to support the Roman mission. The tool is not a formal product of the Roman mission, and it is not intended for use in official Roman mission operations or data processing. 

We greatly appreciate Roman mission community interest. However, the development team’s primary focus is achieving operational stability after launch and through commissioning into operations. As a result, the maintainers may or may not be able to respond to every GitHub Issue or discussion submitted to this repository.
 
Thank you for your understanding and patience during this phase of mission development.

The current list of implemented and planned monitors, along with their prioritization, is tracked in the [monitor development document](https://github.com/spacetelescope/rdmt-spire/blob/main/MONITOR_DEVELOPMENT.md).

If you have an idea for a new monitor or an improvement to an existing one, we encourage you to submit a [**monitor request issue**](https://github.com/spacetelescope/rdmt-spire/issues/new?template=monitor-request.yaml). Monitor requests can be as simple as a description of the desired monitor and its scientific motivation, or they can be more detailed and include specific implementation suggestions. The maintainers will review monitor requests and may ask for additional information or clarification before accepting the request.

If you would like to directly contribute to the repository, please follow the instructions below for how to contribute to this repository using a forking workflow. We cannot guarantee that all pull requests will be accepted, but we welcome contributions that are well-documented and well-tested. If you have questions about whether a contribution is appropriate or how to implement it, please feel free to open an issue in the repository.

#### Monitor Metric Naming Convention

Monitor metric keys stored in data cards and column names in the database tables must use lowercase names. This lowercase naming convention is enforced when adding metrics to the monitor data dictionary.

#### Setting up a Personal Fork
1. Create a personal fork of the `rdmt-spire` repository by visiting its location on GitHub and clicking the `Fork` button.  This will create a copy of the `rdmt-spire` repository under your personal GitHub account (hereby referred to as "personal fork").  Note that this only has to be done once.

2. Make a local copy of your personal fork by cloning the repository (e.g. `git clone https://github.com/username/rdmt-spire.git`, using the repository URL available from the GitHub `Code` menu).  Note that this only has to be done once, unless you explicitly delete your clone of the fork.

3. Ensure that the personal fork is pointing to the `upstream` `rdmt-spire` repository with `git remote add upstream https://github.com/spacetelescope/rdmt-spire.git` (or use the SSH version if you have your SSH keys set up).  Note that, unless you explicitly change the remote location of the repository, this only has to be done once.

#### Development Workflow
1. Create a branch off of the `main` branch on the personal clone to develop software changes on. Branch names should be short but descriptive (e.g. `new-database-table` or `fix-ingest-algorithm`), and not too generic (e.g. `bug-fix`).  Consistent use of hyphens is encouraged.
    1. `git branch <branchname>`
    2. `git checkout <branchname>` - you can use this command to switch back and forth between existing branches.
    3. Perform local software changes using the nominal `git add`/`git commit -m` cycle:
       1. `git status` -  allows you to see which files have changed.
       2. `git add <new or changed files you want to commit>`
       3. `git commit -m 'Explanation of changes you've done with these files'`

2. Remember all changes must have appropriate test and documentation updates (e.g. adding new test coverage in `rdmt_spire/tests`, updating doc-strings and in-line comments, updating relevant markdown files).

3. Push the branch to the GitHub repository for the personal fork with `git push origin <branchname>`.

4. In the `rdmt-spire` repository, create a pull request for the recently pushed branch.  You will want to set the base fork pointing to `rdmt-spire:main` and the `head` fork pointing to the branch on your personal fork (i.e. `username:branchname`).  Note that if the branch is still under development, you can use the GitHub "Draft" feature (under the "Reviewers" section) to tag the pull request as a draft. Not until the "Ready for review" button at the bottom of the pull request is explicitly pushed is the pull request 'mergeable'.

5. Assign the pull request a reviewer, selecting a maintainer of the `rdmt-spire` repository.  They will review your pull request and either accept the request and merge, or ask for additional changes.

6. Iterate with your reviewer(s) on additional changes if necessary, addressing any comments on your pull request.  If changes are required, you may end up iterating over steps 1.3, 2, and 3 several times while working with your reviewer.

7. Once the pull request has been accepted and merged, you can delete your local branch with `git branch -d <branchname>`.

#### Keeping your fork updated
If you wish to, you can keep a personal fork up-to-date with the `rdmt-spire` repository by fetching and rebasing with the `upstream` remote, remember to update your GitHub repo's main after doing this.
1. `git checkout main`
2. `git fetch upstream main`
3. `git rebase upstream/main`
4. `git push origin main`

Alternatively, you can use the `sync fork` button on the main page of your GitHub fork.  Remember once synced you will need to pull your main down to your machine.
1. `git checkout main`
2. `git fetch origin main`
3. `git pull origin main`

#### Collaborating on someone else's fork
Users can contribute to another user's personal fork by adding a `remote` that points to their fork and using the nominal forking workflow, e.g.:

1. `git remote add <username> <remote URL>`
2. `git fetch <username>`
3. `git checkout -b <branchname> <username>/<branchname>`
4. Make some changes (i.e. `add/commit` cycle)
5. `git push <username> <branchname>`

> **Note:** Step 5 only works if you have write access to that user's fork/branch (for example, as a collaborator on their fork, or as a maintainer when "Allow edits by maintainers" is enabled on the pull request). If you do not have write access, contribute via your own fork and open a separate pull request, or provide commits/patches to the pull request author.